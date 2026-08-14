"""Read-only file access inside a repository checkout."""

from pathlib import Path

MAX_LINES = 200
MAX_ENTRIES = 200

# Directories that never hold the bug and would only burn context.
IGNORED = {
    ".git",
    ".github",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    ".vscode",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
}


# Resolve a repo-relative path, refusing anything that escapes the checkout.
def resolve(root: Path, path: str) -> Path:
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"path outside the repository: {path}")
    return target


# A numbered slice of a file. Line numbers let the agent point at what it found;
# the slice keeps a large file from flooding the context window.
def read_file(root: Path, path: str, start: int = 1, limit: int = MAX_LINES) -> str:
    target = resolve(root, path)
    if not target.is_file():
        return f"no such file: {path}"

    # Some files in these repositories are deliberately mis-encoded; a decoding
    # error must not take down a whole run.
    lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
    chunk = lines[start - 1 : start - 1 + limit]
    numbered = "\n".join(f"{start + offset:>6}  {line}" for offset, line in enumerate(chunk))

    shown_to = start + len(chunk) - 1
    header = f"{path} lines {start}-{shown_to} of {len(lines)}"
    return f"{header}\n{numbered}"


# One level of a directory, folders first and marked with a trailing slash so the
# agent can tell where it can descend. Not recursive: a whole repository at once
# would be thousands of useless lines.
def list_directory(root: Path, path: str = ".") -> str:
    target = resolve(root, path)
    if not target.is_dir():
        return f"no such directory: {path}"

    entries = [entry for entry in target.iterdir() if entry.name not in IGNORED]
    entries.sort(key=lambda entry: (entry.is_file(), entry.name))
    names = [f"{entry.name}/" if entry.is_dir() else entry.name for entry in entries]

    header = f"{path} ({len(names)} entries)"
    if len(names) > MAX_ENTRIES:
        header = f"{path} (showing {MAX_ENTRIES} of {len(names)} entries)"
        names = names[:MAX_ENTRIES]
    return "\n".join([header, *names])
