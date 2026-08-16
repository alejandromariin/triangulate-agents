"""What every topology shares.

The budget, the answer format and the wording of the rules live here rather than
in each topology: a difference between two rows of the comparison has to come
from the architecture, not from one of them having been asked more clearly.
"""

import time
from dataclasses import dataclass, field

from crewai import Crew
from pydantic import BaseModel, Field

MODEL = "openai/gpt-5.6-luna"
MAX_ITER = 15
MAX_CANDIDATES = 5


# The shape every topology answers with, so the harness can treat them alike.
@dataclass
class LocalizationResult:
    instance_id: str
    files: list[str]
    reasoning: str
    seconds: float
    usage: dict = field(default_factory=dict)


# Scoring compares paths verbatim, so the format it demands is stated in the
# prompt. Anything a metric penalises has to be asked for explicitly, or the
# measurement drifts into "did the agent guess the expected format".
PATH_FORMAT = (
    "Every path must be complete and relative to the repository root, exactly as "
    "the tools print it: 'django/forms/formsets.py'. Not 'formsets.py', not "
    "'forms/formsets.py', not './django/forms/formsets.py', not an absolute path."
)

INVESTIGATION_RULES = (
    "Investigate with the tools before answering: never propose a path you have "
    "not seen in the repository. Product code only — never tests."
)


# The moulded answer, so scoring never has to parse prose.
class Localization(BaseModel):
    files: list[str] = Field(
        description=f"Repository-relative paths, most suspicious first. {PATH_FORMAT}"
    )
    reasoning: str = Field(description="Why these files, in a few sentences")


def bug_report(instance: dict) -> str:
    return f"--- bug report ---\n{instance['problem_statement']}"


def run_crew(crew: Crew, instance_id: str) -> LocalizationResult:
    started = time.perf_counter()
    output = crew.kickoff()
    elapsed = time.perf_counter() - started

    answer = output.pydantic
    return LocalizationResult(
        instance_id=instance_id,
        files=answer.files[:MAX_CANDIDATES],
        reasoning=answer.reasoning,
        seconds=elapsed,
        usage=dict(crew.usage_metrics) if crew.usage_metrics else {},
    )
