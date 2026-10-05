"""Invalid numerical inputs must fail before entering a time integration loop."""
import numpy as np
import pytest

from gbm_twin.models.decoupled_damage import (
    DecoupledDamageParameters,
    initial_decoupled_damage_state,
    simulate_decoupled_damage,
)
from gbm_twin.models.delayed_response import (
    DelayedResponseParameters,
    initial_delayed_response_state,
    simulate_delayed_response,
)
from gbm_twin.models.reaction_diffusion import ReactionDiffusionParameters
from gbm_twin.models.solver import simulate_reaction_diffusion
from gbm_twin.models.treatment_memory import (
    FractionResponseEvent,
    TreatmentMemoryState,
    initial_treatment_memory_state,
    simulate_with_treatment_memory,
)


@pytest.mark.parametrize("model", ["rd", "memory", "delayed", "decoupled"])
@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("dt", 0.0), ("dt", -1.0), ("dt", 1e-12),
        ("dt", float("nan")), ("dt", float("inf")),
        ("duration_days", float("nan")), ("duration_days", float("inf")),
        ("start_time_day", float("nan")), ("start_time_day", float("inf")),
    ],
)
def test_simulators_reject_invalid_timing(model: str, key: str, value: float) -> None:
    field = np.full((3, 3, 3), 0.5, dtype=np.float32)
    growth = ReactionDiffusionParameters(diffusion=0.01, proliferation=0.02)
    kwargs = dict(spacing=(2.0, 2.0, 2.0), duration_days=1.0, dt=0.5, start_time_day=0.0)
    kwargs[key] = value
    with pytest.raises(ValueError, match=key):
        if model == "rd":
            simulate_reaction_diffusion(field, growth, **kwargs)
        elif model == "memory":
            simulate_with_treatment_memory(initial_treatment_memory_state(field), growth, **kwargs)
        elif model == "delayed":
            simulate_delayed_response(
                initial_delayed_response_state(field), growth,
                delayed=DelayedResponseParameters(
                    damage_transfer_fraction=1.0, damage_half_life_days=60.0,
                    damaged_visibility=1.0,
                ), **kwargs,
            )
        else:
            simulate_decoupled_damage(
                initial_decoupled_damage_state(field), growth,
                parameters=DecoupledDamageParameters(damage_half_life_days=60.0),
                **kwargs,
            )


@pytest.mark.parametrize("key", ["diffusion", "proliferation"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_growth_parameters_reject_nonfinite_values(key: str, value: float) -> None:
    kwargs = dict(diffusion=0.01, proliferation=0.02)
    kwargs[key] = value
    with pytest.raises(ValueError, match=key):
        ReactionDiffusionParameters(**kwargs)


def test_zero_horizon_preserves_full_geometry_and_masks_domain() -> None:
    field = np.full((7, 8, 9), 0.7, dtype=np.float32)
    domain = np.zeros_like(field, dtype=bool)
    domain[2:5, 3:6, 4:7] = True
    expected = np.where(domain, field, 0.0)
    for crop in (False, True):
        result = simulate_reaction_diffusion(
            field, ReactionDiffusionParameters(0.01, 0.02),
            spacing=(2.0, 2.0, 2.0), duration_days=0.0, dt=1.0,
            domain_mask=domain, crop_to_domain=crop,
        )
        np.testing.assert_array_equal(result, expected)
        assert result.dtype == field.dtype
        assert not np.shares_memory(result, field)


@pytest.mark.parametrize("component", ["field", "proliferation_modifier"])
def test_memory_state_rejects_nonfinite_components(component: str) -> None:
    kwargs = dict(
        field=np.full((3, 3, 3), 0.5),
        proliferation_modifier=np.ones((3, 3, 3)),
    )
    kwargs[component][1, 1, 1] = np.nan
    with pytest.raises(ValueError, match="finite"):
        TreatmentMemoryState(**kwargs)


def test_fraction_response_rejects_nonfinite_day() -> None:
    with pytest.raises(ValueError, match="finite"):
        FractionResponseEvent(day=float("nan"), immediate_survival=0.8)


def test_reaction_diffusion_rejects_nonfinite_initial_concentration() -> None:
    field = np.full((3, 3, 3), 0.5)
    field[1, 1, 1] = np.nan
    with pytest.raises(ValueError, match="finite"):
        simulate_reaction_diffusion(
            field, ReactionDiffusionParameters(0.0, 0.0),
            spacing=(2.0, 2.0, 2.0), duration_days=1.0, dt=0.5,
        )
