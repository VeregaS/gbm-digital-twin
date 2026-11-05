import importlib
import subprocess
import sys

import pytest


def test_lightweight_workflow_import_does_not_load_scientific_stack() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; import gbm_twin.workflows.repository; "
            "assert not ({'numpy', 'scipy', 'pandas', 'matplotlib'} & sys.modules.keys())",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_public_exports_keep_their_original_objects() -> None:
    workflows = importlib.import_module("gbm_twin.workflows")
    for name, (module, symbol) in workflows._EXPORTS.items():
        assert getattr(workflows, name) is getattr(importlib.import_module(module), symbol)
        assert name in dir(workflows)
    assert set(workflows.__all__) == set(workflows._EXPORTS)

    with pytest.raises(AttributeError, match="has no attribute"):
        _ = workflows.not_a_workflow
