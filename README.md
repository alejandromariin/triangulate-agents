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

## Requirements

| | Why |
|---|---|
| Python 3.12 | pinned in `.python-version` |
| [uv](https://docs.astral.sh/uv/) | dependency and environment management |
| git | the repositories are cloned and checked out through it |
| [ripgrep](https://github.com/BurntSushi/ripgrep) (`rg`) | backs the lexical search tool |
| ~2 GB of disk | the twelve cloned repositories |

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

## Layout

```
scripts/   golden set construction and repository setup
tools/     read-only access to a checkout: workspace, files, search
data/      golden_set_v1.json (committed) and repos/ (regenerable, ignored)
docs/      decision log
```

## Documentation

- [`docs/DECISIONS.md`](docs/DECISIONS.md) — design decisions and their rationale.
- [`data/SCHEMA.md`](data/SCHEMA.md) — golden set schema and measured dataset properties.

## License

MIT — see [LICENSE](LICENSE).
