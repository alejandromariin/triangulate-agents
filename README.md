# Triangulate

> When does a multi-agent architecture beat a single agent — and what does that gain cost?

A CrewAI multi-agent system for **bug localization** that compares four
topologies — single-agent, sequential, hierarchical and parallel — through an
eval harness built on
[SWE-bench Lite](https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite).

Each instance is a real GitHub issue plus read-only access to the repository at
the commit preceding its fix. The system returns a ranked list of files to
change, scored against the files the real fix actually touched.

## Quickstart

```bash
uv sync
uv run python -m scripts.build_golden_set --dry-run   # inspect without writing
uv run python -m scripts.build_golden_set             # -> data/golden_set_v1.json
uv run pytest
```

## Documentation

- [`docs/DECISIONS.md`](docs/DECISIONS.md) — design decisions and their rationale.
- [`data/SCHEMA.md`](data/SCHEMA.md) — golden set schema.

## License

MIT — see [LICENSE](LICENSE).
