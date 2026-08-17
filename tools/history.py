"""Read-only git history of a checkout.

Every command is anchored at HEAD, which the workspace has parked on the
instance's base commit. git only ever walks backwards from there, so the commit
that fixes the bug — present in the clone — stays out of reach.
"""

import subprocess
from pathlib import Path

from tools.files import resolve

MAX_COMMITS = 15
MAX_BLAME_LINES = 60
TIMEOUT_SECONDS = 60


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        return f"git failed: {result.stderr.strip()}"
    return result.stdout.strip()


# Recent commits, newest first. With a path, only commits touching it.
def git_log(root: Path, path: str = ".", limit: int = MAX_COMMITS) -> str:
    resolve(root, path)
    limit = min(limit, MAX_COMMITS)
    output = _git(
        root,
        "log",
        "HEAD",
        f"--max-count={limit}",
        "--date=short",
        "--format=%h %ad %an: %s",
        "--",
        path,
    )
    if not output:
        return f"no commits touching {path}"
    if output.startswith("git failed:"):
        return output
    return f"last {limit} commits touching {path}\n{output}"


# Who last changed each line of a range, and when.
def git_blame(root: Path, path: str, start: int = 1, end: int | None = None) -> str:
    resolve(root, path)
    end = min(end or start + MAX_BLAME_LINES - 1, start + MAX_BLAME_LINES - 1)
    output = _git(
        root,
        "blame",
        "HEAD",
        "-L",
        f"{start},{end}",
        "--date=short",
        "--",
        path,
    )
    return output or f"no blame output for {path}"
