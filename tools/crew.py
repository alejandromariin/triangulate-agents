"""CrewAI adapters over the read-only tools.

The `description` of each tool is prompt: it is all the model has to decide
which one to reach for, so it states what the tool returns and when it helps.
"""

from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from tools.files import list_directory, read_file
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


# The three tools bound to one instance's checkout.
def build_tools(root: Path) -> list[BaseTool]:
    return [SearchTool(root=root), ListDirectoryTool(root=root), ReadFileTool(root=root)]
