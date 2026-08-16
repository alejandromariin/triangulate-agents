"""Baseline topology: one agent holding every tool.

The reference point for the multi-agent topologies: whatever they gain has to be
measured against what a single well-equipped agent already achieves.
"""

from pathlib import Path

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
    run_crew,
)
from tools.crew import build_tools
from tools.workspace import checkout


def build_agent(root: Path) -> Agent:
    return Agent(
        role="Bug locator",
        goal=(
            "Identify which source files of a repository must be modified to fix a "
            "reported bug, using only the report and the repository itself."
        ),
        backstory=(
            "You are a maintainer who knows how to find your way around an unfamiliar "
            "codebase. You start from the distinctive terms of a report — symbols, error "
            "messages, stack frames — search for them, and read the surrounding code "
            "before committing to an answer. You never guess a path you have not seen."
        ),
        tools=build_tools(root),
        llm=language_model(),
        max_iter=MAX_ITER,
        allow_delegation=False,
        verbose=False,
    )


def build_task(agent: Agent, instance: dict) -> Task:
    return Task(
        description=(
            "A bug has been reported against this repository. Find the source files that "
            f"have to be changed to fix it.\n\n{INVESTIGATION_RULES}\n\n"
            f"{bug_report(instance)}"
        ),
        expected_output=(
            f"At most {MAX_CANDIDATES} paths, most suspicious first, each one seen in the "
            f"repository during the investigation. {PATH_FORMAT}"
        ),
        agent=agent,
        output_pydantic=Localization,
    )


def run(instance: dict) -> LocalizationResult:
    root = checkout(instance)
    agent = build_agent(root)
    crew = Crew(
        agents=[agent],
        tasks=[build_task(agent, instance)],
        process=Process.sequential,
        verbose=False,
        # Left unset, CrewAI prompts on the terminal after every run and blocks
        # for 20 seconds waiting for an answer.
        tracing=False,
    )
    return run_crew(crew, instance["instance_id"])
