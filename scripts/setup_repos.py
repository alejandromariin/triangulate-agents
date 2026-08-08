"""Clone the repositories referenced by the golden set.

Each repository is cloned once into `data/repos/`, and every instance's
`base_commit` is then verified to exist in it. Nothing from the cloned
repositories is ever executed; they are read-only material for the agents.

Usage:
    uv run python -m scripts.setup_repos --only flask
    uv run python -m scripts.setup_repos
"""

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path

GOLDEN_SET = Path("data/golden_set_v1.json")
REPOS_DIR = Path("data/repos")


# Local checkout of a repository. The slash cannot survive in a directory name.
def repo_dir(repo: str) -> Path:
    return REPOS_DIR / repo.replace("/", "__")


# Full clone: the history is what git_log and git_blame will read.
def clone(repo: str) -> None:
    subprocess.run(
        ["git", "clone", "--quiet", f"https://github.com/{repo}.git", str(repo_dir(repo))],
        # A failed clone stops the script instead of failing later, obscurely.
        check=True,
    )


# Does this commit exist in the clone?
def has_commit(repo: str, commit: str) -> bool:
    return _exists(repo, f"{commit}^{{commit}}")


# Does this file exist inside that commit? Answered without touching the checkout.
def has_file_at_commit(repo: str, commit: str, path: str) -> bool:
    return _exists(repo, f"{commit}:{path}")


def _exists(repo: str, revision: str) -> bool:
    # `cat-file -e` prints nothing and answers through its exit code.
    result = subprocess.run(
        ["git", "-C", str(repo_dir(repo)), "cat-file", "-e", revision],
        capture_output=True,
    )
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", help="substring filter on the repository name")
    args = parser.parse_args()

    # The repositories come from the golden set itself, never hardcoded here.
    instances = json.loads(GOLDEN_SET.read_text(encoding="utf-8"))["instances"]
    if args.only:
        instances = [i for i in instances if args.only in i["repo"]]

    per_repo = Counter(i["repo"] for i in instances)
    REPOS_DIR.mkdir(parents=True, exist_ok=True)

    for repo, n in sorted(per_repo.items()):
        # Skipping what is already there makes an interrupted run resumable.
        if repo_dir(repo).exists():
            print(f"{repo:<28} already cloned")
            continue
        print(f"{repo:<28} cloning for {n} instance(s)...")
        clone(repo)

    # The point of the script: check every address in the golden set is real.
    missing_commits = []
    missing_files = []
    for instance in instances:
        if not has_commit(instance["repo"], instance["base_commit"]):
            missing_commits.append((instance["instance_id"], instance["base_commit"]))
            # No commit means there is no tree to look for files in.
            continue
        for gold in instance["gold_files"]:
            if not has_file_at_commit(instance["repo"], instance["base_commit"], gold):
                missing_files.append((instance["instance_id"], gold))

    print()
    print(f"base commits found : {len(instances) - len(missing_commits)}/{len(instances)}")
    print(f"gold files present : {len(instances) - len(missing_files)}/{len(instances)}")
    for instance_id, value in missing_commits + missing_files:
        print(f"  MISSING {instance_id} {value}")


if __name__ == "__main__":
    main()
