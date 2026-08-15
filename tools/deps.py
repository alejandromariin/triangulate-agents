"""Import relationships between files of a checkout."""

import ast
from pathlib import Path

from tools.files import resolve
from tools.search import ripgrep_search

# Directories projects use as a source root, which are not part of the module path.
SOURCE_ROOTS = ("src/", "lib/")


# django/forms/formsets.py -> django.forms.formsets
def module_name(path: str) -> str:
    module = path.replace("\\", "/")
    for prefix in SOURCE_ROOTS:
        module = module.removeprefix(prefix)
    return module.removesuffix(".py").removesuffix("/__init__").replace("/", ".")


# What this file imports, read from the syntax tree rather than by text matching.
def imports(root: Path, path: str) -> str:
    target = resolve(root, path)
    if not target.is_file():
        return f"no such file: {path}"

    try:
        tree = ast.parse(target.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as error:
        return f"cannot parse {path}: {error}"

    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            # level > 0 is a relative import: '.' repeated, then the module.
            prefix = "." * node.level
            found.append(f"{prefix}{node.module or ''}")

    unique = sorted(set(found))
    if not unique:
        return f"{path} imports nothing"
    return f"{path} imports {len(unique)} modules\n" + "\n".join(unique)


# Which files mention this one as a module. Lexical, so it also catches mentions
# in strings, and it misses relative imports written as '.formsets'.
def imported_by(root: Path, path: str) -> str:
    module = module_name(path)
    tail = module.rsplit(".", 1)[-1]
    pattern = rf"(from|import)\s+[\w.]*\b{tail}\b"
    return ripgrep_search(root, pattern)
