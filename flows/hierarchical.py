"""Hierarchical topology: a manager decides which specialists to involve.

The same three specialists as the sequential chain, arranged differently: they
are not run in a fixed order but delegated to. What this row of the comparison
adds over the sequential one is routing, and its cost.
"""

from collections.abc import Generator
from contextlib import contextmanager

from crewai import Agent, Crew, Process, Task
from crewai.events import ToolUsageFinishedEvent, crewai_event_bus

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
from flows.specialists import SPECIALISTS, build_agent
from tools.workspace import checkout


# The manager holds no tools of its own: CrewAI gives it delegation tools, and a
# manager able to investigate would stop being a router and become a fourth
# investigator, which is the baseline again.
def build_manager() -> Agent:
    return Agent(
        role="Triage manager",
        goal=(
            "Locate the files behind a bug report by involving only the investigators "
            "whose signal the report actually calls for."
        ),
        backstory=(
            "You triage incoming bug reports. You read what a report offers — a stack "
            "trace, a regression that used to work, a symptom far from its cause — and "
            "you know which kind of investigation each one rewards. You ask one "
            "investigator at a time, read the answer, and stop as soon as the evidence "
            "settles rather than collecting opinions you do not need."
        ),
        llm=language_model(),
        max_iter=MAX_ITER,
        verbose=False,
    )


# No agent is assigned: in a hierarchical process the manager decides who works
# on it, which is the whole point of the topology.
def build_task(instance: dict) -> Task:
    return Task(
        description=(
            "A bug has been reported against this repository. Decide which "
            "investigators to involve, delegate to them, and produce the files that "
            "have to be changed.\n\n"
            "The investigators available to you are a lexical one, which searches the "
            "text of the code, a historical one, which reads recent commits, and a "
            "structural one, which follows imports. Involving one costs time and "
            f"tokens, so involve one when the report gives it something to work with.\n\n"
            f"{INVESTIGATION_RULES}\n\n{bug_report(instance)}"
        ),
        expected_output=(
            f"At most {MAX_CANDIDATES} paths, most suspicious first, each one seen in the "
            f"repository during the investigation. {PATH_FORMAT}"
        ),
        output_pydantic=Localization,
    )


# A delegation tool announces itself as "Delegate work to coworker" and emits
# events under "delegate_work_to_coworker", so the name is matched in one form.
DELEGATION_TOOLS = ("delegate_work_to_coworker", "ask_question_to_coworker")


def is_delegation(tool_name: str) -> bool:
    return tool_name.lower().replace(" ", "_") in DELEGATION_TOOLS


# Which specialists the manager involved, and what each answered. This is the
# decision the topology exists to make, and it happens inside a tool call rather
# than in a task, so it reaches the record through the event bus or not at all.
@contextmanager
def record_delegations() -> Generator[list[dict]]:
    delegations: list[dict] = []

    with crewai_event_bus.scoped_handlers():

        @crewai_event_bus.on(ToolUsageFinishedEvent)
        def capture(source, event) -> None:
            if not is_delegation(event.tool_name):
                return
            args = event.tool_args if isinstance(event.tool_args, dict) else {}
            delegations.append(
                {
                    "role": args.get("coworker", "unknown"),
                    # Delegating names the field 'task', asking names it 'question'.
                    "asked": args.get("task") or args.get("question", ""),
                    "output": str(event.output),
                }
            )

        yield delegations


def run(instance: dict) -> LocalizationResult:
    root = checkout(instance)
    crew = Crew(
        agents=[build_agent(specialist, root) for specialist in SPECIALISTS],
        tasks=[build_task(instance)],
        process=Process.hierarchical,
        manager_agent=build_manager(),
        verbose=False,
        tracing=False,
    )

    with record_delegations() as delegations:
        result = run_crew(crew, instance["instance_id"])

    result.stages = delegations
    return result
