"""Build the golden set from SWE-bench Lite.

Downloads the `test` split of `princeton-nlp/SWE-bench_Lite`, derives ground
truth from each gold patch, balances the selection across repositories, splits
it into `dev` and `heldout`, and writes `data/golden_set_v1.json`.

Output format is specified in `data/SCHEMA.md`, selection rules in
`docs/DECISIONS.md`.

Usage:
    uv run python -m scripts.build_golden_set --dry-run
    uv run python -m scripts.build_golden_set
"""

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from datasets import load_dataset
from huggingface_hub import dataset_info
from unidiff import PatchedFile, PatchSet

# Matches the definition name in a hunk's section header: "def foo(", "class Bar(".
DEFINITION_RE = re.compile(r"\b(?:async\s+def|def|class)\s+(\w+)")

SCHEMA_VERSION = "1"
SOURCE_DATASET = "princeton-nlp/SWE-bench_Lite"
SOURCE_SPLIT = "test"
DEFAULT_OUTPUT = Path("data/golden_set_v1.json")

MAX_FILES = 3
QUOTA_PER_REPO = 3
TARGET_SIZE = 38
DEFAULT_SEED = 20260803


# True if the path looks like test code rather than product code.
def is_test_path(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return (
        path.startswith("tests/")
        or "/tests/" in path
        or name.startswith("test_")
        or name.endswith("_test.py")
    )


# The files of a patch that count as a localization target.
def product_code_files(patch_text: str) -> list[PatchedFile]:
    return [
        pfile
        for pfile in PatchSet(patch_text)
        # A deleted file has nothing left to locate.
        if pfile.target_file != "/dev/null"
        and pfile.path.endswith(".py")
        and not is_test_path(pfile.path)
    ]


# Ground truth: the paths the real fix touched. Sorted so the output is stable.
def parse_gold_files(patch_text: str) -> list[str]:
    return sorted(pfile.path for pfile in product_code_files(patch_text))


# Pulls "get_prep_value" out of "def get_prep_value(self, value):".
def definition_name(section_header: str) -> str | None:
    match = DEFINITION_RE.search(section_header)
    return match.group(1) if match else None


# Approximate function-level targets, read from what git writes in hunk headers.
def parse_gold_functions(patch_text: str) -> list[str]:
    names = set()  # a set, so two hunks in the same function collapse into one
    for pfile in product_code_files(patch_text):
        for hunk in pfile:
            name = definition_name(hunk.section_header)
            if name:
                names.add(f"{pfile.path}::{name}")
    return sorted(names)


# Whether the report already gives the answer away, usually via a stack trace.
def statement_names_gold_file(statement: str, gold_files: list[str]) -> bool:
    text = statement.lower()
    for gold in gold_files:
        path = gold.lower()
        # Same file written as an import path: src/flask/cli.py -> src.flask.cli -> flask.cli
        dotted = path.removesuffix(".py").replace("/", ".")
        unrooted = dotted.split(".", 1)[-1]
        if any(form in text for form in (path, path.rsplit("/", 1)[-1], dotted, unrooted)):
            return True
    return False


# Instances keyed by repository, each list sorted so the draw is reproducible.
def group_by_repo(instances: list[dict]) -> dict[str, list[dict]]:
    grouped = defaultdict(list)
    for instance in instances:
        grouped[instance["repo"]].append(instance)
    for repo in grouped:
        grouped[repo].sort(key=lambda i: i["instance_id"])
    return dict(grouped)


# How many instances to draw from each repository to reach TARGET_SIZE.
def assign_quotas(pool: dict[str, list[dict]]) -> dict[str, int]:
    # A base quota each, capped by what the repository actually has.
    quotas = {repo: min(QUOTA_PER_REPO, len(items)) for repo, items in pool.items()}
    largest_first = sorted(pool, key=lambda r: (-len(pool[r]), r))

    # Hand out the leftover slots, biggest repositories first.
    remaining = TARGET_SIZE - sum(quotas.values())
    while remaining > 0:
        assigned = 0
        for repo in largest_first:
            if remaining == 0:
                break
            if quotas[repo] < len(pool[repo]):
                quotas[repo] += 1
                remaining -= 1
                assigned += 1
        # Every repository is exhausted: TARGET_SIZE is unreachable.
        if assigned == 0:
            break
    return quotas


def pick_heldout(drawn: dict[str, list[dict]], rng: random.Random) -> list[dict]:
    """One instance per repository, keeping the share of hinted statements.

    Statements that already name the gold file (typically a pasted stack trace)
    make an instance markedly easier. Left to chance the two splits end up at
    very different difficulties, which would make a drop from dev to heldout
    unreadable: overfitting and a harder sample look identical.
    """
    # How many of the held-out instances should carry a hint to match the whole set.
    everything = [i for items in drawn.values() for i in items]
    hinted_share = sum(i["statement_names_gold_file"] for i in everything) / len(everything)
    target = round(len(drawn) * hinted_share)

    repos = sorted(drawn)
    rng.shuffle(repos)
    # Repositories offering only one kind cannot balance anything, so they go
    # first and the ones with a real choice absorb the difference.
    repos.sort(key=lambda r: len({i["statement_names_gold_file"] for i in drawn[r]}))

    heldout = []
    for repo in repos:
        # Ask for whichever kind is still short, and settle for what the repo has.
        want_hinted = sum(i["statement_names_gold_file"] for i in heldout) < target
        options = [i for i in drawn[repo] if i["statement_names_gold_file"] == want_hinted]
        heldout.append(rng.choice(options or drawn[repo]))
    return heldout


# The 38 instances, drawn per repository and tagged dev / heldout.
def select_golden_set(instances: list[dict], seed: int) -> list[dict]:
    # Seeded, so the same input always yields the same golden set.
    rng = random.Random(seed)
    pool = group_by_repo(instances)
    quotas = assign_quotas(pool)

    drawn = {repo: rng.sample(pool[repo], quotas[repo]) for repo in sorted(pool)}
    heldout = {i["instance_id"] for i in pick_heldout(drawn, rng)}

    selected = [instance for items in drawn.values() for instance in items]
    for instance in selected:
        instance["split"] = "heldout" if instance["instance_id"] in heldout else "dev"

    return sorted(selected, key=lambda i: i["instance_id"])


# One SWE-bench row reduced to the fields the benchmark needs. The gold patch is
# read here and deliberately not carried over: it is the answer.
def build_instance(row: dict, gold_files: list[str]) -> dict:
    return {
        "instance_id": row["instance_id"],
        "repo": row["repo"],
        "base_commit": row["base_commit"],
        "environment_setup_commit": row["environment_setup_commit"],
        "problem_statement": row["problem_statement"],
        "hints_text": row["hints_text"],
        "created_at": row["created_at"],
        "gold_files": gold_files,
        "gold_functions": parse_gold_functions(row["patch"]),
        "n_gold_files": len(gold_files),
        "statement_names_gold_file": statement_names_gold_file(
            row["problem_statement"], gold_files
        ),
    }


# Every eligible instance, plus a tally of why the rest were rejected.
def collect_instances(rows) -> tuple[list[dict], Counter]:
    filters = Counter()
    instances = []
    for row in rows:
        gold_files = parse_gold_files(row["patch"])
        if not gold_files:
            filters["no_valid_files"] += 1
        elif len(gold_files) > MAX_FILES:
            filters["too_many_files"] += 1
        elif not row["problem_statement"].strip():
            filters["empty_problem_statement"] += 1
        else:
            instances.append(build_instance(row, gold_files))
    return instances, filters


# Provenance block: everything needed to rebuild this exact file later.
def build_meta(selected: list[dict], seed: int, filters: Counter) -> dict:
    splits = Counter(instance["split"] for instance in selected)
    per_repo = Counter(instance["repo"] for instance in selected)
    return {
        "schema_version": SCHEMA_VERSION,
        "source_dataset": SOURCE_DATASET,
        "source_split": SOURCE_SPLIT,
        "source_revision": dataset_info(SOURCE_DATASET).sha,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "seed": seed,
        "n_total": len(selected),
        "n_dev": splits["dev"],
        "n_heldout": splits["heldout"],
        "n_repos": len(per_repo),
        "max_files": MAX_FILES,
        "per_repo_quota": dict(sorted(per_repo.items())),
        "filters": {
            "no_valid_files": filters["no_valid_files"],
            "too_many_files": filters["too_many_files"],
            "empty_problem_statement": filters["empty_problem_statement"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Cached after the first run, so this only hits the network once.
    rows = load_dataset(SOURCE_DATASET, split=SOURCE_SPLIT)
    instances, filters = collect_instances(rows)
    selected = select_golden_set(instances, args.seed)
    meta = build_meta(selected, args.seed, filters)

    print(f"eligible {len(instances)}/{len(rows)}  ->  selected {meta['n_total']}")
    print(f"dev {meta['n_dev']}  heldout {meta['n_heldout']}  repos {meta['n_repos']}")
    for repo, quota in meta["per_repo_quota"].items():
        print(f"  {repo:<28} {quota}")
    if any(filters.values()):
        print(f"dropped: {dict(filters)}")

    # Everything above is already done; only the write is skipped.
    if args.dry_run:
        print("dry run, nothing written")
        return

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"meta": meta, "instances": selected}
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
