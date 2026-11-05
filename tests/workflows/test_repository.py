from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import gbm_twin.workflows.repository as repository_module
from gbm_twin.workflows.repository import (
    read_repository_state,
)

GIT_SHA = (
    "0123456789abcdef"
    "0123456789abcdef"
    "01234567"
)


def test_read_repository_state_for_clean_repo(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        assert cwd == tmp_path
        assert check
        assert capture_output
        assert text

        if command == [
            "git",
            "rev-parse",
            "HEAD",
        ]:
            stdout = f"{GIT_SHA}\n"

        elif command == [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=normal",
        ]:
            stdout = ""

        else:
            raise AssertionError(
                f"Unexpected command: {command}"
            )

        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    monkeypatch.setattr(
        repository_module.subprocess,
        "run",
        fake_run,
    )

    result = read_repository_state(
        tmp_path
    )

    assert result.commit_sha == GIT_SHA
    assert not result.dirty


def test_read_repository_state_detects_dirty_repo(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        if command[1:] == [
            "rev-parse",
            "HEAD",
        ]:
            stdout = f"{GIT_SHA}\n"
        else:
            stdout = " M src/example.py\n"

        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    monkeypatch.setattr(
        repository_module.subprocess,
        "run",
        fake_run,
    )

    result = read_repository_state(
        tmp_path
    )

    assert result.commit_sha == GIT_SHA
    assert result.dirty


def test_read_repository_state_rejects_invalid_sha(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="invalid-sha\n",
            stderr="",
        )

    monkeypatch.setattr(
        repository_module.subprocess,
        "run",
        fake_run,
    )

    with pytest.raises(
        ValueError,
        match="Git HEAD",
    ):
        read_repository_state(
            tmp_path
        )