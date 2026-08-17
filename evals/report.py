"""Compare the topologies that have been run over a split.

Usage:
    uv run python -m evals.report --split dev

Aggregates are recomputed here rather than read from each run's summary: the
comparison is restricted to the instances every topology answered, so a row that
covers fewer instances cannot flatter itself against the others.
"""

import argparse
import json
from pathlib import Path

from evals.scorers import aggregate

RUNS_DIR = Path("reports/runs")
ORDER = ("single", "sequential", "hierarchical", "parallel")

COLUMNS = (
    ("accuracy@1", "Acc@1", "{:.2f}"),
    ("accuracy@3", "Acc@3", "{:.2f}"),
    ("accuracy@5", "Acc@5", "{:.2f}"),
    ("mrr", "MRR", "{:.2f}"),
    ("seconds", "Seconds", "{:.0f}"),
    ("prompt_tokens", "Tokens in", "{:.0f}"),
    ("completion_tokens", "Tokens out", "{:.0f}"),
    ("cost_usd", "Cost $", "{:.3f}"),
)


def load_run(topology: str, split: str) -> dict[str, dict]:
    directory = RUNS_DIR / f"{topology}_{split}"
    records = {}
    for path in sorted(directory.glob("*.json")):
        if path.name == "summary.json":
            continue
        record = json.loads(path.read_text(encoding="utf-8"))
        records[record["instance_id"]] = record
    return records


def markdown_table(header: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join(lines)


def summary_table(runs: dict[str, dict], instances: list[str], population: str) -> str:
    rows = []
    for topology, records in runs.items():
        scored = [records[i] for i in instances]
        if population == "hinted":
            scored = [r for r in scored if r["statement_names_gold_file"]]
        elif population == "unhinted":
            scored = [r for r in scored if not r["statement_names_gold_file"]]
        if not scored:
            continue
        row = aggregate(scored)
        rows.append(
            [topology, str(row["n"])] + [fmt.format(row[key]) for key, _, fmt in COLUMNS]
        )
    if not rows:
        return "No instances of this kind in the compared set."
    return markdown_table(["Topology", "n"] + [label for _, label, _ in COLUMNS], rows)


# Where the topologies actually differ, bug by bug. An aggregate cannot show that
# two topologies with the same accuracy are right about different instances.
def per_instance_table(runs: dict[str, dict], instances: list[str]) -> str:
    rows = []
    for instance_id in instances:
        first = next(iter(runs.values()))[instance_id]
        ranks = [runs[t][instance_id]["rank"] for t in runs]
        rows.append(
            [instance_id, "yes" if first["statement_names_gold_file"] else "no"]
            + [str(rank) if rank else "—" for rank in ranks]
        )
    return markdown_table(["Instance", "Hinted"] + list(runs), rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="dev", choices=["dev", "heldout"])
    args = parser.parse_args()

    runs = {t: load_run(t, args.split) for t in ORDER if (RUNS_DIR / f"{t}_{args.split}").is_dir()}
    if not runs:
        raise SystemExit(f"no runs found for split {args.split}")

    answered = [set(records) for records in runs.values()]
    shared = sorted(set.intersection(*answered))
    if not shared:
        raise SystemExit("the topologies share no instance")

    report = [
        f"# Topology comparison — {args.split}",
        "",
        f"{len(shared)} instances answered by all of {', '.join(runs)}.",
        "",
        "## All instances",
        "",
        summary_table(runs, shared, "all"),
        "",
        "## Instances whose report names the gold file",
        "",
        summary_table(runs, shared, "hinted"),
        "",
        "## Instances whose report does not",
        "",
        summary_table(runs, shared, "unhinted"),
        "",
        "## Rank of the gold file, per instance",
        "",
        per_instance_table(runs, shared),
        "",
    ]

    # Silently comparing different instance sets would be the easiest way to
    # publish a difference that is an artefact of who answered what.
    dropped = sorted(set.union(*answered) - set(shared))
    if dropped:
        report += [
            "## Excluded",
            "",
            "Answered by some topologies but not all, so left out of every table above:",
            "",
        ] + [f"- `{instance_id}`" for instance_id in dropped] + [""]

    text = "\n".join(report)
    path = Path("reports") / f"comparison_{args.split}.md"
    path.write_text(text, encoding="utf-8")
    print(text)
    print(path)


if __name__ == "__main__":
    main()
