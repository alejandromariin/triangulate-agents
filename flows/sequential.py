"""Sequential topology: the three specialists in a fixed chain.

Each one receives what the previous concluded. Ordered so the chain can start
from nothing: only the lexical stage can work from the report alone, the other
two need candidate files to interrogate.
"""

from crewai import Agent, Crew, Process, Task

from flows.common import (
    INVESTIGATION_RULES,
    MAX_CANDIDATES,
    PATH_FORMAT,
    Localization,
    LocalizationResult,
    bug_report,
    run_crew,
)
from flows.specialists import SPECIALISTS, Specialist, build_agent
from tools.workspace import checkout

CHAIN = SPECIALISTS


def build_task(specialist: Specialist, agent: Agent, instance: dict, previous: Task | None) -> Task:
    last = specialist is CHAIN[-1]
    return Task(
        description=(
            f"A bug has been reported against this repository.\n\n"
            f"{specialist.instruction}\n\n{INVESTIGATION_RULES}\n\n{bug_report(instance)}"
        ),
        expected_output=(
            (
                f"At most {MAX_CANDIDATES} paths, most suspicious first, each one seen in "
                "the repository during the investigation."
                if last
                else "The candidate files in order, each with what you concluded about it."
            )
            + f" {PATH_FORMAT}"
        ),
        agent=agent,
        context=[previous] if previous else [],
        # Only the end of the chain is scored, so only it is forced into the schema.
        output_pydantic=Localization if last else None,
    )


def run(instance: dict) -> LocalizationResult:
    root = checkout(instance)
    agents = [build_agent(specialist, root) for specialist in CHAIN]

    tasks = []
    for specialist, agent in zip(CHAIN, agents):
        tasks.append(build_task(specialist, agent, instance, tasks[-1] if tasks else None))

    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=False,
        tracing=False,
    )
    return run_crew(crew, instance["instance_id"])
