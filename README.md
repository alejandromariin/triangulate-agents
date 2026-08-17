# Triangulate

> When does a multi-agent architecture beat a single agent — and what does that gain cost?

A CrewAI multi-agent system for **bug localization** that compares four
topologies — single-agent, sequential, hierarchical and parallel — through an
eval harness built on
[SWE-bench Lite](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite).

Each instance is a real GitHub issue plus read-only access to the repository at
the commit preceding its fix. The system returns a ranked list of files to
change, scored against the files the real fix actually touched.

Nothing from the analyzed repositories is ever executed. They are cloned, checked
out at the relevant commit, and read.

## The topologies

Three signals locate a bug: the words of the report (lexical — search, directory
listing, file reading), what changed recently (historical — log and blame), and
who imports whom (structural — the import graph). A specialist agent holds the
tools of one signal each; the topologies differ only in how the specialists are
arranged.

| Topology | Arrangement | The question it answers |
|---|---|---|
| `single` | one agent holding every tool | is a single well-equipped agent enough? |
| `sequential` | lexical → historical → structural, each stage refining the last | does accumulated context beat independence? |
| `hierarchical` | a triage manager delegates to the specialists it finds relevant | does routing save cost without losing accuracy? |
| `parallel` | all three at once from the raw report, a synthesizer reconciles | does independence find what a chain funnels away? |

Every topology answers with at most 5 candidate files, and every agent is capped
at 15 tool-using iterations — accuracy is measured under that budget, and the
caps are identical across topologies so that no row can buy accuracy with room
the others were not given.

## What is measured

**These are not SWE-bench numbers.** SWE-bench reports `% resolved`: a system
generates a patch, the patch is applied, and the repository's own tests decide
whether the bug is fixed. This project stops one step earlier — at localization,
which file must change — so its numbers are not comparable to any SWE-bench
leaderboard, and a higher figure here does not mean a better SWE-bench system.

The metrics are therefore defined here rather than inherited:

| | |
|---|---|
| Accuracy@1 / @3 / @5 | is the gold file among the first k candidates? |
| MRR | how highly was it ranked? `1/rank`, averaged over instances |
| tokens, cost, wall-clock | what the answer cost to produce |
| malformed candidates | answers that name a file without locating it — a format failure, not a reasoning one |

Precision, recall and F1 are not reported: every instance in SWE-bench Lite has
exactly one gold file, which makes precision degenerate — a correct answer inside
a five-candidate list would score 0.2.

Accuracy is always read next to cost, and always broken down by whether the
report already named the gold file (`statement_names_gold_file`) — the two
populations are of very different difficulty, and an aggregate hides it.

The comparison is between topologies, all of them evaluated on the same instances
under the same budget, with the same model.

The system is stochastic and the model does not accept a fixed temperature, so
the same topology can rank the same bug differently on two runs. Numbers are
produced by a single run per topology, so they carry sampling noise, and
differences of one or two instances are not read as differences.

## Requirements

| | Why |
|---|---|
| Python 3.12 | pinned in `.python-version` |
| [uv](https://docs.astral.sh/uv/) | dependency and environment management |
| git | the repositories are cloned and checked out through it |
| [ripgrep](https://github.com/BurntSushi/ripgrep) (`rg`) | backs the lexical search tool |
| ~2 GB of disk | the twelve cloned repositories |
| an OpenAI API key | only to run the agents; building the dataset needs none |

On Windows, prefix debugging commands with `PYTHONIOENCODING=utf-8`: agent logs
contain characters the default console encoding cannot represent, and without it
the log is replaced by encoding errors.

Installing ripgrep:

```bash
winget install BurntSushi.ripgrep.MSVC   # Windows
brew install ripgrep                     # macOS
apt install ripgrep                      # Debian / Ubuntu
```

## Quickstart

```bash
uv sync

# Build the golden set: 38 instances across 12 repositories, split dev / heldout
uv run python -m scripts.build_golden_set --dry-run   # inspect without writing
uv run python -m scripts.build_golden_set             # -> data/golden_set_v1.json

# Clone those repositories and verify every base commit and gold file
uv run python -m scripts.setup_repos --only flask     # one repository, to try it
uv run python -m scripts.setup_repos                  # -> data/repos/, ~2 GB
```

Both scripts are idempotent: rerunning them re-derives the same golden set and
skips repositories that are already cloned.

To run the agents, copy `.env.example` to `.env` and fill in the key:

```
OPENAI_API_KEY=sk-...
```

```python
from dotenv import load_dotenv; load_dotenv()

from flows import single
from tools.workspace import load_instances

result = single.run(load_instances()["django__django-15902"])
print(result.files, result.usage)
```

Every topology exposes the same `run(instance) -> LocalizationResult`: a ranked
list of files plus the reasoning, elapsed time and token usage.

Evaluating a topology over a whole split:

```bash
uv run python -m evals.runner --topology single --split dev --limit 5   # five instances, to try it
uv run python -m evals.runner --topology parallel --split dev --max-usd 1
```

Once several topologies have been run over the same split, comparing them:

```bash
uv run python -m evals.report --split dev   # -> reports/comparison_dev.md
```

The comparison is restricted to the instances every topology answered, and any
instance left out is listed rather than silently dropped.

Results go to `reports/runs/<topology>_<split>/`, one file per instance written
as it finishes, plus a `summary.json`. Each record keeps the ranked answer, its
reasoning and what every agent produced along the way — for the hierarchical
topology, which specialists the manager involved and what it asked them.
Rerunning resumes: instances already answered are not paid for twice. Delete the
directory to answer them again — which is required after any change to prompts
or budgets, or the summary would average answers produced under different
conditions.

## Layout

```
scripts/   golden set construction and repository setup
tools/     read-only access to a checkout: files, search, history, imports
flows/     one module per topology, all exposing run(instance)
evals/     scorers and the runner that executes a topology over a split
data/      golden_set_v1.json (committed) and repos/ (regenerable, ignored)
reports/   per-instance results and summaries of each run
docs/      decision log
```

## Documentation

- [`docs/DECISIONS.md`](docs/DECISIONS.md) — design decisions and their rationale.
- [`data/SCHEMA.md`](data/SCHEMA.md) — golden set schema and measured dataset properties.

## License

MIT — see [LICENSE](LICENSE).
