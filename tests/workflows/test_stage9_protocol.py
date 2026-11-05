from __future__ import annotations

from pathlib import Path

from gbm_twin.workflows.stage9_protocol import (
    load_stage9_protocol_config,
)


def test_repository_stage9_protocol_is_valid() -> None:
    config = load_stage9_protocol_config(
        Path("configs/research/stage9_delayed_response.yaml")
    )

    assert config.design == "frozen_stage8_kinetics_delayed_response_v1"
    assert config.delayed.half_life_days == (14.0, 30.0, 60.0)
    assert config.delayed.transfer_fractions == (0.5, 0.75, 1.0)
    assert config.delayed.visibility_values == (0.5, 0.75, 1.0)
    assert (
        config.selection.catastrophic_delta_vs_persistence
        == -0.10
    )
