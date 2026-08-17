"""Parallel topology: the three specialists at once, then a synthesizer.

Nobody inherits anybody's candidates: each specialist starts from the report and
works alone, so a file missed by one can still be found by another. The cost is
that no specialist benefits from what another discovered, and a fourth agent is
needed to reconcile three answers that may disagree.
"""

import asyncio
import time

from crewai import Agent, Crew, Process, Task

from flows.common import (
    INVESTIGATION_RULES,
    MAX_CANDIDATES,
    MAX_ITER,
    PATH_FORMAT,
    Localization,
    LocalizationResult,
    bug_report,
    language_model,
)
from flows.specialists import SPECIALISTS, Specialist, build_agent
from tools.workspace import checkout

USAGE_FIELDS = ("prompt_tokens", "completion_tokens", "total_tokens", "successful_requests")


# The synthesizer holds no tools: the investigating is done, and letting it search
# again would make it a fourth investigator whose answer could ignore the others.
def build_synthesizer() -> Agent:
    return Agent(
        role="Synthesizer",
        goal="Turn three independent investigations into one ranked answer.",
        backstory=(
            "You arbitrate between specialists who worked without seeing each other. "
            "A file all three arrived at by different routes is stronger than one "
            "argued loudly by a single investigator, and a file only one of them found "
            "may still be right if its reasoning is concrete. You weigh evidence "
            "against confidence."
        ),
        llm=language_model(),
        max_iter=MAX_ITER,
        allow_delegation=False,
        verbose=False,
    )


def build_specialist_crew(specialist: Specialist, instance: dict, root) -> Crew:
    agent = build_agent(specialist, root)
    task = Task(
        description=(
            f"A bug has been reported against this repository.\n\n"
            f"{specialist.instruction}\n\n{INVESTIGATION_RULES}\n\n{bug_report(instance)}"
        ),
        expected_output=(
            "The candidate files in order, each with what you concluded about it and "
            f"how confident you are. {PATH_FORMAT}"
        ),
        agent=agent,
    )
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False, tracing=False)


# The specialists never see each other's work, so their findings only meet here,
# as text in the prompt.
def build_synthesis_crew(instance: dict, findings: list[dict]) -> Crew:
    agent = build_synthesizer()
    reported = "\n\n".join(f"--- {f['role']} ---\n{f['output']}" for f in findings)
    task = Task(
        description=(
            "Three investigators examined this bug report independently, each with a "
            "different kind of evidence. Reconcile their findings into one ranked "
            "answer: rank a file by how well the evidence supports it, not by how many "
            "investigators mentioned it. Propose no path that none of them reported.\n\n"
            f"{bug_report(instance)}\n\n{reported}"
        ),
        expected_output=(
            f"At most {MAX_CANDIDATES} paths, most suspicious first. {PATH_FORMAT}"
        ),
        agent=agent,
        output_pydantic=Localization,
    )
    return Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False, tracing=False)


def usage_of(crews: list[Crew]) -> dict:
    totals = dict.fromkeys(USAGE_FIELDS, 0)
    for crew in crews:
        metrics = dict(crew.usage_metrics) if crew.usage_metrics else {}
        for field in USAGE_FIELDS:
            totals[field] += metrics.get(field, 0)
    return totals


async def investigate(crews: list[Crew]) -> list[str]:
    outputs = await asyncio.gather(*(crew.kickoff_async() for crew in crews))
    return [str(output) for output in outputs]


def run(instance: dict) -> LocalizationResult:
    root = checkout(instance)
    specialist_crews = [build_specialist_crew(s, instance, root) for s in SPECIALISTS]

    started = time.perf_counter()
    outputs = asyncio.run(investigate(specialist_crews))
    findings = [
        {"role": specialist.role, "output": output}
        for specialist, output in zip(SPECIALISTS, outputs)
    ]

    synthesis = build_synthesis_crew(instance, findings)
    answer = synthesis.kickoff().pydantic
    # Wall clock, not the sum of the specialists: three of them working at once
    # take as long as the slowest, which is what running them in parallel buys.
    elapsed = time.perf_counter() - started

    return LocalizationResult(
        instance_id=instance["instance_id"],
        files=answer.files[:MAX_CANDIDATES],
        reasoning=answer.reasoning,
        seconds=elapsed,
        usage=usage_of([*specialist_crews, synthesis]),
        stages=findings,
    )
