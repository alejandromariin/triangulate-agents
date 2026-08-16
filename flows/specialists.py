"""The three specialists the multi-agent topologies are built from.

Shared verbatim rather than redefined per topology: what separates those rows of
the comparison has to be how the specialists are arranged, not who they are.
"""

from dataclasses import dataclass
from pathlib import Path

from crewai import Agent

from flows.common import MAX_ITER, language_model
from tools.crew import build_tools


@dataclass(frozen=True)
class Specialist:
    tools: tuple[str, ...]
    role: str
    goal: str
    backstory: str
    instruction: str


# read_file is in every set: it is not a signal of its own but how any of them is
# confirmed. A stage that cannot open a file can only speculate about it.
LEXICAL = Specialist(
    tools=("search", "list_directory", "read_file"),
    role="Lexical investigator",
    goal="Turn the words of a bug report into a list of candidate files.",
    backstory=(
        "You work from the vocabulary of a report: symbols, error messages, stack "
        "frames, configuration keys. You search for the terms that could only come "
        "from this codebase, then open what you find to see whether it is really "
        "involved. You know that the loudest match is often not the faulty one."
    ),
    instruction=(
        "Search the repository for the distinctive terms of the report and open the "
        "matches to judge them. Produce the candidate files, most suspicious first, "
        "and for each one a sentence on what connects it to the report and what you "
        "are unsure about."
    ),
)

HISTORICAL = Specialist(
    tools=("git_log", "git_blame", "read_file"),
    role="History investigator",
    goal="Judge candidate files by what changed in them recently.",
    backstory=(
        "You read repositories through their history. A bug reported today is usually "
        "younger than the code around it, so a file changed weeks ago is a better "
        "suspect than one untouched for years, and a commit whose subject echoes the "
        "report is better still. You check the change itself before believing it."
    ),
    instruction=(
        "You are given the candidates found so far. Look at the recent history of each "
        "one, and of the directory around it in case a nearby file is the real suspect. "
        "Reorder them by what the history supports, and say for each what the history "
        "showed. You may add a file the history points at, and drop one only if you can "
        "say why."
    ),
)

STRUCTURAL = Specialist(
    tools=("imports", "imported_by", "read_file"),
    role="Dependency investigator",
    goal="Judge candidate files by their position in the import graph.",
    backstory=(
        "You think in terms of who calls whom. A file where a failure is observed is "
        "often only a caller of the file where it originates, so you follow imports "
        "outwards to the code that actually does the work, and callers inwards when a "
        "module looks correct on its own."
    ),
    instruction=(
        "You are given the candidates and what the previous stages concluded. Follow "
        "the imports around them to tell the place where the fault lives from the place "
        "where it shows. Then commit to the final ranked answer."
    ),
)

SPECIALISTS = (LEXICAL, HISTORICAL, STRUCTURAL)


def build_agent(specialist: Specialist, root: Path) -> Agent:
    return Agent(
        role=specialist.role,
        goal=specialist.goal,
        backstory=specialist.backstory,
        tools=[tool for tool in build_tools(root) if tool.name in specialist.tools],
        llm=language_model(),
        max_iter=MAX_ITER,
        allow_delegation=False,
        verbose=False,
    )
