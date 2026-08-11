"""Read-only access to a repository at an instance's base commit."""

import json
import subprocess
from pathlib import Path

GOLDEN_SET = Path("data/golden_set_v1.json")
REPOS_DIR = Path("data/repos")


# The golden set keyed by instance_id.
def load_instances() -> dict[str, dict]:
    data = json.loads(GOLDEN_SET.read_text(encoding="utf-8"))
    return {instance["instance_id"]: instance for instance in data["instances"]}


# Put the repository at the state the bug was reported against, and say where it is.
def checkout(instance: dict) -> Path:
    path = REPOS_DIR / instance["repo"].replace("/", "__")
    subprocess.run(
        # --force: a dirty tree would otherwise leave the agent reading a
        # different revision than the one being evaluated.
        ["git", "-C", str(path), "checkout", "--quiet", "--force", instance["base_commit"]],
        check=True,
    )
    return path
