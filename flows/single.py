"""Baseline topology: one agent holding every tool.

The reference point for the multi-agent topologies: whatever they gain has to be
measured against what a single well-equipped agent already achieves.
"""

import time
from dataclasses import dataclass, field
from pathlib import Path

from crewai import Agent, Crew, Process, Task
from pydantic import BaseModel, Field

from tools.crew import build_tools
from tools.workspace import checkout

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


# The moulded answer, so scoring never has to parse prose.
class Localization(BaseModel):
    files: list[str] = Field(description="Repository-relative paths, most suspicious first")
    reasoning: str = Field(description="Why these files, in a few sentences")


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
        llm=MODEL,
        max_iter=MAX_ITER,
        allow_delegation=False,
        verbose=False,
    )


def build_task(agent: Agent, instance: dict) -> Task:
    return Task(
        description=(
            "A bug has been reported against this repository. Find the source files that "
            "have to be changed to fix it.\n\n"
            "Investigate with the tools before answering: search for distinctive terms "
            "from the report, then read the candidates to confirm. Product code only — "
            "never tests.\n\n"
            f"--- bug report ---\n{instance['problem_statement']}"
        ),
        expected_output=(
            f"At most {MAX_CANDIDATES} repository-relative paths, most suspicious first, "
            "each one seen in the repository during the investigation."
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

    started = time.perf_counter()
    output = crew.kickoff()
    elapsed = time.perf_counter() - started

    answer = output.pydantic
    return LocalizationResult(
        instance_id=instance["instance_id"],
        files=answer.files[:MAX_CANDIDATES],
        reasoning=answer.reasoning,
        seconds=elapsed,
        usage=dict(crew.usage_metrics) if crew.usage_metrics else {},
    )
