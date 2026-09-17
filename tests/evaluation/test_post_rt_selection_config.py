from pathlib import Path

import pytest

from gbm_twin.evaluation.post_rt_selection_config import (
    load_post_rt_selection_config,
)


def test_load_post_rt_selection_config(
    tmp_path: Path,
) -> None:
    path = tmp_path / "post_rt.yaml"
    path.write_text(
        """
schema_version: 1
initial_kill_rates_per_day:
  - 0.0025
  - 0.005
decay_times_days:
  - 30.0
  - 60.0
include_fractionated_only_baseline: true
""".lstrip(),
        encoding="utf-8",
    )

    config = load_post_rt_selection_config(
        path
    )

    assert config.initial_kill_rates_per_day == (
        0.0025,
        0.005,
    )
    assert config.decay_times_days == (
        30.0,
        60.0,
    )
    assert config.include_fractionated_only_baseline is True


def test_post_rt_selection_config_rejects_nonpositive_rate(
    tmp_path: Path,
) -> None:
    path = tmp_path / "post_rt.yaml"
    path.write_text(
        """
schema_version: 1
initial_kill_rates_per_day:
  - 0.0
decay_times_days:
  - 60.0
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="kill rates",
    ):
        load_post_rt_selection_config(
            path
        )


def test_post_rt_selection_config_rejects_unknown_schema(
    tmp_path: Path,
) -> None:
    path = tmp_path / "post_rt.yaml"
    path.write_text(
        """
schema_version: 99
initial_kill_rates_per_day:
  - 0.005
decay_times_days:
  - 60.0
""".lstrip(),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="schema",
    ):
        load_post_rt_selection_config(
            path
        )
