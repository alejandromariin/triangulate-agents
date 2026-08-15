"""CrewAI adapters over the read-only tools.

The `description` of each tool is prompt: it is all the model has to decide
which one to reach for, so it states what the tool returns and when it helps.
"""

from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from tools.deps import imported_by, imports
from tools.files import list_directory, read_file
from tools.history import git_blame, git_log
from tools.search import ripgrep_search


class ListDirectoryArgs(BaseModel):
    path: str = Field(default=".", description="Repository-relative directory, e.g. 'django/forms'")


class ListDirectoryTool(BaseTool):
    name: str = "list_directory"
    description: str = (
        "List the contents of one directory of the repository. Directories end with '/'. "
        "Not recursive: call it again to descend. Use it to learn how the project is "
        "organised before guessing file paths."
    )
    args_schema: type[BaseModel] = ListDirectoryArgs
    root: Path

    def _run(self, path: str = ".") -> str:
        return list_directory(self.root, path)


class ReadFileArgs(BaseModel):
    path: str = Field(description="Repository-relative file path, e.g. 'django/forms/formsets.py'")
    start: int = Field(default=1, description="First line to return, 1-based")


class ReadFileTool(BaseTool):
    name: str = "read_file"
    description: str = (
        "Read a numbered slice of a source file, up to 200 lines. The header states the "
        "total line count, so a further call with a larger 'start' continues where the "
        "previous one ended. Use it to confirm that a candidate file really contains the bug."
    )
    args_schema: type[BaseModel] = ReadFileArgs
    root: Path

    def _run(self, path: str, start: int = 1) -> str:
        return read_file(self.root, path, start)


class SearchArgs(BaseModel):
    pattern: str = Field(description="Regular expression, e.g. 'class ManagementForm'")
    glob: str = Field(default="*.py", description="File filter, e.g. '*.py'")


class SearchTool(BaseTool):
    name: str = "search"
    description: str = (
        "Search the repository with a regular expression and return matches as "
        "'path:line:text'. This is the fastest way to locate a symbol, an error message "
        "or a phrase quoted in the bug report. Start from a distinctive term of the report; "
        "if there are too many matches, make the pattern more specific."
    )
    args_schema: type[BaseModel] = SearchArgs
    root: Path

    def _run(self, pattern: str, glob: str = "*.py") -> str:
        return ripgrep_search(self.root, pattern, glob)


class GitLogArgs(BaseModel):
    path: str = Field(default=".", description="File or directory to look at, or '.' for the whole repository")


class GitLogTool(BaseTool):
    name: str = "git_log"
    description: str = (
        "Recent commits touching a file or directory, newest first, as "
        "'hash date author: subject'. Bugs cluster in code that changed recently, so a "
        "file with several recent commits is a stronger candidate than an untouched one. "
        "The history stops at the revision the bug was reported against."
    )
    args_schema: type[BaseModel] = GitLogArgs
    root: Path

    def _run(self, path: str = ".") -> str:
        return git_log(self.root, path)


class GitBlameArgs(BaseModel):
    path: str = Field(description="Repository-relative file path")
    start: int = Field(default=1, description="First line to annotate, 1-based")
    end: int | None = Field(default=None, description="Last line; at most 60 lines are returned")


class GitBlameTool(BaseTool):
    name: str = "git_blame"
    description: str = (
        "Annotate a range of lines with the commit, author and date that last changed each "
        "one. Use it once you have a suspicious range: a line touched days before the "
        "report is far more suspicious than one untouched for a decade."
    )
    args_schema: type[BaseModel] = GitBlameArgs
    root: Path

    def _run(self, path: str, start: int = 1, end: int | None = None) -> str:
        return git_blame(self.root, path, start, end)


class ImportsArgs(BaseModel):
    path: str = Field(description="Repository-relative file path")


class ImportsTool(BaseTool):
    name: str = "imports"
    description: str = (
        "List the modules a file imports, read from its syntax tree. Use it to follow the "
        "bug outwards: if a file looks involved but the fault is not in it, the culprit is "
        "often one of its dependencies."
    )
    args_schema: type[BaseModel] = ImportsArgs
    root: Path

    def _run(self, path: str) -> str:
        return imports(self.root, path)


class ImportedByTool(BaseTool):
    name: str = "imported_by"
    description: str = (
        "Find the files that import a given one, as 'path:line:text'. The reverse of "
        "'imports': use it when a file behaves correctly on its own and the fault is "
        "likely in one of its callers. Lexical, so it misses relative imports."
    )
    args_schema: type[BaseModel] = ImportsArgs
    root: Path

    def _run(self, path: str) -> str:
        return imported_by(self.root, path)


# Every tool, bound to one instance's checkout. Ordered by how often they are the
# right first move, since that ordering is part of what the model sees.
def build_tools(root: Path) -> list[BaseTool]:
    return [
        SearchTool(root=root),
        ListDirectoryTool(root=root),
        ReadFileTool(root=root),
        GitLogTool(root=root),
        GitBlameTool(root=root),
        ImportsTool(root=root),
        ImportedByTool(root=root),
    ]
