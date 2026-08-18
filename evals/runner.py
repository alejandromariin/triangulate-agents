"""Run a topology over a split and write the scored results.

Usage:
    uv run python -m evals.runner --split dev --limit 5

Each instance is written as soon as it finishes and is not paid for twice: a
second run of the same topology and split resumes where the previous one
stopped. Delete the run directory to force everything to be answered again.
"""

import argparse
import json
import time
from pathlib import Path

from evals.scorers import aggregate, score
from flows import hierarchical, parallel, sequential, single
from tools.workspace import load_instances

RUNS_DIR = Path("reports/runs")
TOPOLOGIES = {
    "single": single.run,
    "sequential": sequential.run,
    "hierarchical": hierarchical.run,
    "parallel": parallel.run,
}
MAX_USD = 1.00

# An instance costs tens of thousands of tokens in a few seconds, which is fast
# enough to hit a per-minute account limit. Held below it deliberately, since
# waiting between instances is cheaper than losing one to a refused call. The
# margin is wide because a topology running its agents concurrently spends its
# tokens in a burst, and the limit is enforced on the burst, not on the average.
TOKENS_PER_MINUTE = 100_000

# A refused call is worth one patient retry: the limit it hit is measured over a
# minute, so waiting one out is usually all it takes.
RETRY_WAIT_SECONDS = 90


def select(split: str, limit: int | None) -> list[dict]:
    instances = [i for i in load_instances().values() if i["split"] == split]
    # Sorted so that --limit always picks the same instances: two runs of a
    # subset have to be comparable with each other.
    instances.sort(key=lambda i: i["instance_id"])
    return instances[:limit] if limit else instances


def run_instance(topology: str, instance: dict) -> dict:
    result = TOPOLOGIES[topology](instance)
    record = score(result, instance["gold_files"])
    record["instance_id"] = instance["instance_id"]
    record["repo"] = instance["repo"]
    record["statement_names_gold_file"] = instance["statement_names_gold_file"]
    record["gold_files"] = instance["gold_files"]
    record["files"] = result.files
    record["reasoning"] = result.reasoning
    record["stages"] = result.stages
    return record


# The aggregate on its own mixes two very different tasks: instances whose
# statement already contains the answer, and instances where it has to be found.
def summarize(records: list[dict]) -> dict:
    return {
        "all": aggregate(records),
        "hinted": aggregate([r for r in records if r["statement_names_gold_file"]]),
        "unhinted": aggregate([r for r in records if not r["statement_names_gold_file"]]),
    }


# Wait until the tokens just spent fit inside the allowance, counting the time
# the instance itself took.
def pace(record: dict) -> None:
    tokens = record["prompt_tokens"] + record["completion_tokens"]
    delay = tokens / TOKENS_PER_MINUTE * 60 - record["seconds"]
    if delay > 0:
        time.sleep(delay)


def attempt(topology: str, instance: dict) -> dict:
    try:
        return run_instance(topology, instance)
    except Exception as error:
        print(f"    retrying in {RETRY_WAIT_SECONDS}s after {type(error).__name__}", flush=True)
        time.sleep(RETRY_WAIT_SECONDS)
        return run_instance(topology, instance)


def write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topology", default="single", choices=sorted(TOPOLOGIES))
    parser.add_argument("--split", default="dev", choices=["dev", "heldout"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--max-usd", type=float, default=MAX_USD)
    args = parser.parse_args()

    run_dir = RUNS_DIR / f"{args.topology}_{args.split}"
    instances = select(args.split, args.limit)
    records = []
    failures = []
    spent = 0.0

    for position, instance in enumerate(instances, start=1):
        path = run_dir / f"{instance['instance_id']}.json"
        head = f"[{position}/{len(instances)}] {instance['instance_id']}"

        if path.is_file():
            records.append(json.loads(path.read_text(encoding="utf-8")))
            print(f"{head}  (done)")
            continue

        if spent >= args.max_usd:
            print(f"{head}  stopping: ${spent:.2f} of ${args.max_usd:.2f} spent")
            break

        print(head, flush=True)
        try:
            record = attempt(args.topology, instance)
        # A refused or dropped call is expected over dozens of API round trips,
        # and it must not discard the instances already answered. Nothing is
        # written, so a later run retries this instance.
        except Exception as error:
            print(f"    failed: {type(error).__name__}: {error}")
            failures.append(instance["instance_id"])
            continue

        write(path, record)
        spent += record["cost_usd"]
        records.append(record)
        print(f"    rank {record['rank']}  {record['seconds']:.0f}s  ${record['cost_usd']:.4f}")
        pace(record)

    summary = summarize(records)
    write(
        run_dir / "summary.json",
        {"topology": args.topology, "split": args.split, "failed": failures, **summary},
    )
    print(f"\n{run_dir}")
    print(json.dumps(summary["all"], indent=2))


if __name__ == "__main__":
    main()
