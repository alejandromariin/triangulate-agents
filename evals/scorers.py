"""Deterministic scoring of a localization answer.

No model is involved: given an answer and the ground truth, the numbers are
fixed. Everything here is checkable by hand on invented cases.
"""

from statistics import mean

K_VALUES = (1, 3, 5)

INPUT_USD_PER_MILLION = 0.20
OUTPUT_USD_PER_MILLION = 1.20


# Same file written differently is still the same file. Case is left alone: on
# Linux 'Utils.py' and 'utils.py' are two different files.
def normalize(path: str) -> str:
    return path.strip().replace("\\", "/").removeprefix("./").removeprefix("/")


# Repeating a candidate must not improve its rank, so duplicates collapse.
def candidates(files: list[str]) -> list[str]:
    seen = []
    for path in files:
        normalized = normalize(path)
        if normalized and normalized not in seen:
            seen.append(normalized)
    return seen


# Position of the first gold file in the ranking, or None if it never appears.
# Partial paths do not count: 'formsets.py' is not an answer, Django has many.
def gold_rank(files: list[str], gold_files: list[str]) -> int | None:
    gold = {normalize(path) for path in gold_files}
    for position, path in enumerate(candidates(files), start=1):
        if path in gold:
            return position
    return None


# Cost of one answer. Cached input is billed at the full input rate here, which
# makes the figure an upper bound rather than an underestimate.
def cost_usd(usage: dict) -> float:
    prompt = usage.get("prompt_tokens", 0)
    completion = usage.get("completion_tokens", 0)
    return (
        prompt * INPUT_USD_PER_MILLION + completion * OUTPUT_USD_PER_MILLION
    ) / 1_000_000


# The per-instance record the report is built from.
def score(result, gold_files: list[str]) -> dict:
    rank = gold_rank(result.files, gold_files)
    scored = {f"hit@{k}": int(rank is not None and rank <= k) for k in K_VALUES}
    scored["rr"] = 1 / rank if rank else 0.0
    scored["rank"] = rank
    scored["n_candidates"] = len(candidates(result.files))
    scored["seconds"] = result.seconds
    scored["prompt_tokens"] = result.usage.get("prompt_tokens", 0)
    scored["completion_tokens"] = result.usage.get("completion_tokens", 0)
    scored["cost_usd"] = cost_usd(result.usage)
    return scored


# One row of the comparison table: accuracy always next to what it cost.
def aggregate(scored: list[dict]) -> dict:
    if not scored:
        return {}
    row = {f"accuracy@{k}": mean(s[f"hit@{k}"] for s in scored) for k in K_VALUES}
    row["mrr"] = mean(s["rr"] for s in scored)
    row["n"] = len(scored)
    row["seconds"] = mean(s["seconds"] for s in scored)
    row["prompt_tokens"] = mean(s["prompt_tokens"] for s in scored)
    row["completion_tokens"] = mean(s["completion_tokens"] for s in scored)
    row["cost_usd"] = sum(s["cost_usd"] for s in scored)
    return row
