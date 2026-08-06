# `golden_set_v1.json` schema

The contract consumed by the eval runner and by every topology. It is produced
by `scripts/build_golden_set.py` from the `test` split of
[`princeton-nlp/SWE-bench_Lite`](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite).

The file is committed to git: it is small, and its history is the record of what
was evaluated in every run.

## Top-level structure

```jsonc
{
  "meta": { ... },        // provenance and sampling parameters
  "instances": [ ... ]    // instances, sorted by instance_id
}
```

### `meta`

| Field | Type | Description |
|---|---|---|
| `schema_version` | `str` | Version of *this* schema (`"1"`). Bump it when the fields of `instances` change. |
| `source_dataset` | `str` | `"princeton-nlp/SWE-bench_Lite"`. |
| `source_split` | `str` | `"test"`. |
| `source_revision` | `str \| null` | HuggingFace revision of the dataset, when `datasets` exposes it. Without it reproducibility is only best-effort: the upstream dataset could change. |
| `built_at` | `str` | ISO-8601 UTC build timestamp. |
| `seed` | `int` | Sampling seed. Same seed + same upstream ⇒ same file. |
| `n_total` | `int` | Number of selected instances. |
| `n_dev` | `int` | Number of instances in the `dev` split. |
| `n_heldout` | `int` | Number of instances in the `heldout` split. |
| `n_repos` | `int` | Number of distinct repositories represented. Every one of them appears in both splits. |
| `max_files` | `int` | Safeguard: maximum number of files touched by the gold patch. Never fires on SWE-bench Lite (see below). |
| `per_repo_quota` | `object` | Instances drawn from each repository, keyed by repo. Quotas rather than a cap: a cap sets a ceiling but no floor, so a random draw could omit a small repository entirely. See `docs/DECISIONS.md` (D-006). |
| `filters` | `object` | Count of instances rejected by each criterion. Makes the selection bias auditable. Expected to be all zeros on SWE-bench Lite. |

### `instances[]`

| Field | Type | Origin | Description |
|---|---|---|---|
| `instance_id` | `str` | SWE-bench | Unique identifier, e.g. `django__django-11099`. Primary key across the whole project. |
| `repo` | `str` | SWE-bench | GitHub `owner/name`, e.g. `django/django`. |
| `base_commit` | `str` | SWE-bench | SHA of the commit **preceding** the fix. This is the state the agents see, read-only. |
| `environment_setup_commit` | `str \| null` | SWE-bench | SHA SWE-bench uses to build an execution environment. Unused: nothing from the analyzed repositories is ever executed. |
| `problem_statement` | `str` | SWE-bench | Text of the GitHub issue. **The agent's only textual input.** |
| `hints_text` | `str` | SWE-bench | Issue comments posted after the report. Stored but **never passed to the agent**: they often contain the solution and would contaminate the task. |
| `created_at` | `str` | SWE-bench | Date of the original PR. Relevant when reasoning about model memorization. |
| `gold_files` | `list[str]` | derived | Repo-relative paths touched by the gold patch. **Ground truth of the primary metric.** Sorted alphabetically. |
| `gold_functions` | `list[str]` | derived | `"path.py::name"` of the enclosing functions/classes, best-effort (see below). |
| `n_gold_files` | `int` | derived | `len(gold_files)`. Always `1` on SWE-bench Lite; kept because it is not constant on other datasets. |
| `statement_names_gold_file` | `bool` | derived | Whether the statement already names the gold file, usually via a pasted stack trace. Such instances are much easier, so both splits are stratified on it. Also report results split by this field. See `docs/DECISIONS.md` (D-007). |
| `split` | `"dev" \| "heldout"` | derived | `dev` is the only split used while iterating on prompts and parameters; `heldout` is reserved and produces the reported numbers. Stratified by repository *and* by `statement_names_gold_file`. See `docs/DECISIONS.md` (D-003, D-007). |

SWE-bench fields deliberately **not** copied: `patch`, `test_patch`,
`FAIL_TO_PASS`, `PASS_TO_PASS`, `version`. The gold `patch` literally contains
the answer; keeping it out of the JSON that is loaded into the agent process
makes it structurally impossible to leak into a prompt by accident. It can be
re-derived from upstream if ever needed.

## How `gold_files` is derived

From SWE-bench's `patch` field (which already excludes test changes — those live
separately in `test_patch`), the unified-diff headers are parsed and the
*destination* path (`+++ b/...`) of each file is taken. Discarded:

- files deleted by the patch (destination `/dev/null`): there is nothing to locate;
- non-`.py` files;
- test files that slipped through (`tests/`, `test_*.py`, `*_test.py`).

None of these exclusions actually fire on SWE-bench Lite — see the measured
properties below. They are retained as safeguards and as an executable statement
of what the task assumes.

## How `statement_names_gold_file` is derived

Lexical match of the gold path against the lowercased statement, in three forms:

| Form | Example |
|---|---|
| full path | `django/contrib/staticfiles/handlers.py` |
| bare file name | `axes_grid.py` |
| dotted module, with and without its root package | `sklearn.utils.multiclass`, `flask.config` |

It is a heuristic: it can miss a mention phrased in prose, and a very generic
file name could in principle match unrelated text. All 16 matches in the current
golden set were inspected by hand and none was a false positive.

## Measured properties of the source dataset

Counted over the full `test` split before implementing the build script
(see `docs/DECISIONS.md`, D-005):

| Property | Value |
|---|---|
| Instances in the split | 300 |
| Instances surviving every filter | 300 |
| Instances with exactly one gold file | 300 |
| Files dropped as tests / non-Python / deleted | 0 |
| Distinct repositories | 12 |
| Largest repository share | `django/django`, 114 instances (38%) |
| Smallest repository | `pallets/flask`, 3 instances |
| Selected instances whose statement names the gold file | 16 of 38 (42%) |

Three consequences follow, and all are load-bearing:

1. **Repository balance is the only selection rule that does anything.** It is
   what stops the golden set from being a Django benchmark. Since the smallest
   repository has exactly 3 instances, a quota of 3 per repository is feasible
   for all 12 (D-006).
2. **Every instance has a single target.** Precision@k is degenerate under a
   single gold file — a correct answer inside a 5-candidate list scores 0.2 — so
   the primary metrics are Accuracy@k and MRR. Equally, the benchmark covers
   single-file bugs only. Multi-file bugs, where a team of specialists would
   plausibly gain the most over a single agent, are absent from this dataset, and
   conclusions must be stated as holding for single-file localization.
3. **Roughly two in five instances hand over the answer.** A pasted stack trace
   names the failing file outright. This is realistic and is not filtered out,
   but it splits the benchmark into two populations of very different difficulty
   — so both splits are stratified on it, and results should be reported for each
   population as well as overall. An aggregate number over a 42/58 mix is hard to
   interpret and easy to move by luck of the draw.

## How `gold_functions` is derived (best-effort)

Git writes the *section heading* into every hunk header, i.e. the enclosing
definition line:

```
@@ -120,7 +120,9 @@ def get_prep_value(self, value):
```

The `def`/`class` name is extracted from there. It is a cheap heuristic that does
not require cloning the repositories. Its known limits:

- nested definitions: git reports the nearest definition, which may be the class
  rather than the method, or the other way around;
- hunks at the top of a file (imports) have no heading, so they yield no function;
- the heading is indicative — git does not guarantee it is the syntactic parent.

All three are observable on `django__django-11099`, whose two hunks yield one
absent heading and one naming the preceding class rather than the modified one.
`gold_functions` is therefore **not reportable ground truth**, and scoring uses
`gold_files` only. An accurate derivation requires resolving hunk line numbers to
enclosing definitions with `ast` against a checkout at `base_commit`. See
`docs/DECISIONS.md` (D-002).

## Example

```json
{
  "meta": {
    "schema_version": "1",
    "source_dataset": "princeton-nlp/SWE-bench_Lite",
    "source_split": "test",
    "source_revision": "6ec7bb89b9342f664a54a6e0a6ea6501d3437cc2",
    "built_at": "2026-08-06T08:17:13.277204+00:00",
    "seed": 20260803,
    "n_total": 38,
    "n_dev": 26,
    "n_heldout": 12,
    "n_repos": 12,
    "max_files": 3,
    "per_repo_quota": { "django/django": 4, "sympy/sympy": 4, "pallets/flask": 3 },
    "filters": { "no_valid_files": 0, "too_many_files": 0, "empty_problem_statement": 0 }
  },
  "instances": [
    {
      "instance_id": "astropy__astropy-14182",
      "repo": "astropy/astropy",
      "base_commit": "a5917978be39d13cd90b517e1de4e7a539ffaa48",
      "environment_setup_commit": "5f74eacbcc7fff707a44d8eb58adaa514cb7dcb5",
      "problem_statement": "Please support header rows in RestructuredText output\n...",
      "hints_text": "",
      "created_at": "2022-12-16T11:13:37Z",
      "gold_files": ["astropy/io/ascii/rst.py"],
      "gold_functions": [
        "astropy/io/ascii/rst.py::RST",
        "astropy/io/ascii/rst.py::get_fixedwidth_params"
      ],
      "n_gold_files": 1,
      "statement_names_gold_file": false,
      "split": "heldout"
    }
  ]
}
```
