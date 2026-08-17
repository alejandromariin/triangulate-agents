"""The scoring rules, as cases with a known answer.

Every number the comparison reports comes out of these functions, and a mistake
in them produces figures that are wrong without being suspicious.
"""

from evals.scorers import aggregate, candidates, cost_usd, gold_rank, normalize


def test_rank_is_the_position_of_the_gold_file():
    answer = ["a/b.py", "c/d.py", "e/f.py"]
    assert gold_rank(answer, ["c/d.py"]) == 2


def test_rank_is_none_when_the_gold_file_is_absent():
    assert gold_rank(["a/b.py"], ["c/d.py"]) is None


def test_a_bare_file_name_is_not_an_answer():
    # D-009: naming a file is not locating it. Django has many utils.py.
    assert gold_rank(["formsets.py"], ["django/forms/formsets.py"]) is None


def test_a_partial_path_is_not_an_answer():
    assert gold_rank(["forms/formsets.py"], ["django/forms/formsets.py"]) is None


def test_separators_and_prefixes_do_not_change_a_path():
    assert normalize("./django\\forms\\formsets.py") == "django/forms/formsets.py"
    assert gold_rank(["./a/b.py"], ["a/b.py"]) == 1


def test_case_is_not_normalized():
    # On a case-sensitive filesystem these are two different files.
    assert gold_rank(["A/B.py"], ["a/b.py"]) is None


def test_repeating_a_candidate_does_not_improve_its_rank():
    assert candidates(["a/b.py", "a/b.py", "c/d.py"]) == ["a/b.py", "c/d.py"]
    assert gold_rank(["a/b.py", "a/b.py", "c/d.py"], ["c/d.py"]) == 2


def test_cost_uses_both_token_directions():
    usage = {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000}
    assert cost_usd(usage) == 0.20 + 1.20


def test_aggregate_averages_accuracy_and_sums_cost():
    scored = [
        {"hit@1": 1, "hit@3": 1, "hit@5": 1, "rr": 1.0, "bare_names": 0,
         "seconds": 10, "prompt_tokens": 100, "completion_tokens": 10, "cost_usd": 0.01},
        {"hit@1": 0, "hit@3": 1, "hit@5": 1, "rr": 0.5, "bare_names": 2,
         "seconds": 20, "prompt_tokens": 300, "completion_tokens": 30, "cost_usd": 0.03},
    ]
    row = aggregate(scored)

    assert row["n"] == 2
    assert row["accuracy@1"] == 0.5
    assert row["accuracy@3"] == 1
    assert row["mrr"] == 0.75
    assert row["seconds"] == 15
    assert row["prompt_tokens"] == 200
    # Accuracy is an average over instances; cost is what the run actually spent.
    assert row["cost_usd"] == 0.04
    assert row["bare_names"] == 2


def test_aggregate_of_nothing_is_empty():
    assert aggregate([]) == {}
