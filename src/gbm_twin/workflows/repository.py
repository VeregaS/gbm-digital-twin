from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

_GIT_SHA_PATTERN = re.compile(
    r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$"
)


@dataclass(frozen=True)
class RepositoryState:
    commit_sha: str
    dirty: bool


def _run_git(
    repo_root: Path,
    *arguments: str,
) -> str:
    try:
        result: subprocess.CompletedProcess[str] = (
            subprocess.run(
                [
                    "git",
                    *arguments,
                ],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            )
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Git executable was not found"
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Git command failed in {repo_root}"
        ) from exc

    return result.stdout.strip()


def read_repository_state(
    repo_root: Path,
) -> RepositoryState:
    if not repo_root.is_dir():
        raise NotADirectoryError(
            f"Repository root does not exist: {repo_root}"
        )

    commit_sha = _run_git(
        repo_root,
        "rev-parse",
        "HEAD",
    ).lower()

    if (
        _GIT_SHA_PATTERN.fullmatch(
            commit_sha
        )
        is None
    ):
        raise ValueError(
            "Git HEAD must be a 40- or "
            "64-character hexadecimal SHA"
        )

    status = _run_git(
        repo_root,
        "status",
        "--porcelain",
        "--untracked-files=normal",
    )

    return RepositoryState(
        commit_sha=commit_sha,
        dirty=bool(status),
    )