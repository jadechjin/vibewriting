"""Git safety net for orchestrator - snapshot commits and rollback."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

# Orchestrator 管辖路径（仅这些路径参与 snapshot/rollback）
MANAGED_PATHS = ["paper/", "output/"]


def get_managed_paths() -> list[str]:
    """Return list of paths managed by the orchestrator."""
    return list(MANAGED_PATHS)


def has_uncommitted_changes(repo_root: Path) -> bool:
    """Check if there are uncommitted changes in managed paths.

    Runs: git status --porcelain -- paper/ output/
    Returns True if any output (= changes exist).
    """
    cmd = [
        "git", "-C", str(repo_root),
        "status", "--porcelain", "--"
    ] + MANAGED_PATHS
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return bool(result.stdout.strip())


def create_snapshot_commit(repo_root: Path, message: str) -> str:
    """Create a snapshot commit of managed paths.

    Steps:
    1. git add paper/ output/
    2. git commit -m "auto: snapshot before {message}"
    3. Return commit hash

    Returns empty string if nothing to commit.
    Raises subprocess.CalledProcessError on git failure.
    """
    # Stage managed paths
    add_cmd = ["git", "-C", str(repo_root), "add", "--"] + MANAGED_PATHS
    subprocess.run(add_cmd, capture_output=True, text=True, check=True)

    # Check if there's anything staged
    diff_cmd = ["git", "-C", str(repo_root), "diff", "--cached", "--quiet"]
    diff_result = subprocess.run(diff_cmd, capture_output=True, text=True, check=False)

    if diff_result.returncode == 0:
        # Nothing staged, nothing to commit
        logger.info("No changes to snapshot in managed paths")
        return ""

    # Commit
    commit_msg = f"auto: snapshot before {message}"
    commit_cmd = [
        "git", "-C", str(repo_root),
        "commit", "-m", commit_msg
    ]
    subprocess.run(commit_cmd, capture_output=True, text=True, check=True)

    # Get commit hash
    hash_cmd = ["git", "-C", str(repo_root), "rev-parse", "HEAD"]
    hash_result = subprocess.run(hash_cmd, capture_output=True, text=True, check=True)
    commit_hash = hash_result.stdout.strip()

    logger.info("Created snapshot commit %s: %s", commit_hash[:8], commit_msg)
    return commit_hash


def rollback_to_snapshot(repo_root: Path, commit_hash: str) -> None:
    """Rollback managed paths to a previous snapshot commit.

    Uses: git checkout <commit_hash> -- paper/ output/
    This only affects managed paths, not the entire repo.

    Raises subprocess.CalledProcessError on failure.
    """
    cmd = [
        "git", "-C", str(repo_root),
        "checkout", commit_hash, "--"
    ] + MANAGED_PATHS
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    logger.info("Rolled back managed paths to snapshot %s", commit_hash[:8])


def stash_before_patch(repo_root: Path, message: str) -> str:
    """Stash changes in paper/ before applying a patch.

    Runs: git stash push -m "auto: before patch {message}" -- paper/
    Returns the stash ref (e.g. "stash@{0}") on success,
    or empty string if working tree is clean (nothing to stash).

    Raises subprocess.CalledProcessError on git failure.
    """
    # Check if paper/ has uncommitted changes first
    status_cmd = [
        "git", "-C", str(repo_root),
        "status", "--porcelain", "--", "paper/",
    ]
    status_result = subprocess.run(
        status_cmd, capture_output=True, text=True, check=False,
    )
    if not status_result.stdout.strip():
        logger.info("No changes in paper/ to stash")
        return ""

    stash_msg = f"auto: before patch {message}"
    stash_cmd = [
        "git", "-C", str(repo_root),
        "stash", "push", "-m", stash_msg, "--", "paper/",
    ]
    subprocess.run(stash_cmd, capture_output=True, text=True, check=True)

    # Retrieve the latest stash ref
    list_cmd = ["git", "-C", str(repo_root), "stash", "list"]
    list_result = subprocess.run(
        list_cmd, capture_output=True, text=True, check=True,
    )
    first_line = list_result.stdout.strip().splitlines()[0]
    stash_ref = first_line.split(":")[0]  # e.g. "stash@{0}"

    logger.info("Stashed paper/ changes as %s: %s", stash_ref, stash_msg)
    return stash_ref


def rollback_stash(repo_root: Path) -> None:
    """Pop the latest stash to restore previous working tree state.

    Runs: git stash pop
    Raises subprocess.CalledProcessError on failure.
    """
    cmd = ["git", "-C", str(repo_root), "stash", "pop"]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    logger.info("Popped latest stash to restore working tree")


def drop_stash(repo_root: Path) -> None:
    """Drop the latest stash after a successful patch.

    Runs: git stash drop
    Raises subprocess.CalledProcessError on failure.
    """
    cmd = ["git", "-C", str(repo_root), "stash", "drop"]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    logger.info("Dropped latest stash (patch succeeded)")


def list_stashes(repo_root: Path) -> list[str]:
    """List all stashes in the repository.

    Runs: git stash list
    Returns each stash entry as a list element, or empty list if none.
    """
    cmd = ["git", "-C", str(repo_root), "stash", "list"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    output = result.stdout.strip()
    if not output:
        return []
    return output.splitlines()
