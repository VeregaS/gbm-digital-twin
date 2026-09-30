from pathlib import Path

from gbm_twin.workflows.stage10_protocol import (
    load_stage10_protocol_config,
)


def test_stage10_protocol_loads_predefined_grid(
    tmp_path: Path,
) -> None:
    path = (
        tmp_path
        / "stage10.yaml"
    )

    path.write_text(
        """schema_version: 1
design: frozen_stage9_kinetics_decoupled_damage_v1
decoupled:
  visible_damage_half_life_days: [14, 30, 60]
selection:
  catastrophic_delta_vs_persistence: -0.10
  max_mean_dice_degradation: 0.005
  max_growth_delta_degradation: 0.010
  min_regression_delta_gain: 0.0
""",
        encoding="utf-8",
    )

    config = (
        load_stage10_protocol_config(
            path
        )
    )

    assert (
        config
        .visible_damage_half_life_days
        == (
            14.0,
            30.0,
            60.0,
        )
    )

    assert (
        config
        .selection
        .max_mean_dice_degradation
        == 0.005
    )
