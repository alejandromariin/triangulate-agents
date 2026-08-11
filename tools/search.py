"""Lexical search inside a repository checkout, backed by ripgrep."""

import shutil
import subprocess
from pathlib import Path

MAX_RESULTS = 50
MAX_COLUMNS = 200
TIMEOUT_SECONDS = 60


# Matches of a regular expression, as `path:line:text`. The pattern comes from the
# agent, so an invalid one is reported back rather than raised.
def ripgrep_search(
    root: Path,
    pattern: str,
    glob: str = "*.py",
    max_results: int = MAX_RESULTS,
) -> str:
    # An external binary: without it every search would silently return nothing.
    if shutil.which("rg") is None:
        raise RuntimeError("ripgrep is not installed or not on PATH")

    result = subprocess.run(
        [
            "rg",
            "--line-number",
            "--no-heading",
            "--color=never",
            f"--max-columns={MAX_COLUMNS}",
            "--glob",
            glob,
            pattern,
            ".",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )

    # ripgrep exits 1 on no matches, which is an ordinary answer here.
    if result.returncode not in (0, 1):
        return f"search failed: {result.stderr.strip()}"

    matches = result.stdout.splitlines()
    if not matches:
        return f"no matches for {pattern!r} in {glob}"

    header = f"{len(matches)} matches for {pattern!r} in {glob}"
    if len(matches) > max_results:
        header = f"{header} (showing the first {max_results}; narrow the pattern to see the rest)"
        matches = matches[:max_results]
    return "\n".join([header, *matches])
