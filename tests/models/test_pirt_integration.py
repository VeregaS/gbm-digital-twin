import numpy as np

from gbm_twin.models.pirt import (
    apply_pirt_fraction,
)
from gbm_twin.models.pirt_solver import (
    simulate_reaction_diffusion_pirt,
)
from gbm_twin.models.radiobiology import (
    RadiobiologyParameters,
)
from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
)
from gbm_twin.models.rt_schedule import (
    build_fractionated_radiotherapy,
    build_pirt_radiotherapy,
    reconstruct_weekday_like_schedule,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)
from gbm_twin.models.treatment import (
    FractionatedRadiotherapy,
    PIRTFractionatedRadiotherapy,
)


def _zero_dynamics(
) -> ReactionDiffusionParameters:
    return ReactionDiffusionParameters(
        diffusion=0.0,
        proliferation=0.0,
    )


def test_pirt_builder_preserves_schedule_and_lq() -> None:
    schedule = (
        reconstruct_weekday_like_schedule(
            start_day=14.0,
            total_dose_gy=60.0,
            fractions_number=30,
        )
    )

    radiobiology = (
        RadiobiologyParameters(
            alpha_per_gy=0.1,
            alpha_beta_ratio_gy=10.0,
        )
    )

    multiplicative = (
        build_fractionated_radiotherapy(
            schedule,
            radiobiology,
        )
    )

    pirt = build_pirt_radiotherapy(
        schedule,
        radiobiology,
    )

    assert (
        type(multiplicative)
        is FractionatedRadiotherapy
    )

    assert (
        type(pirt)
        is PIRTFractionatedRadiotherapy
    )

    assert (
        pirt.fraction_days
        == multiplicative.fraction_days
    )

    assert (
        pirt.dose_per_fraction_gy
        == multiplicative.dose_per_fraction_gy
    )

    assert (
        pirt.alpha_per_gy
        == multiplicative.alpha_per_gy
    )

    assert (
        pirt.beta_per_gy2
        == multiplicative.beta_per_gy2
    )

    assert (
        pirt.survival_fraction_per_fraction
        == multiplicative
        .survival_fraction_per_fraction
    )


def test_existing_multiplicative_rt_is_unchanged() -> None:
    initial = np.full(
        (5, 5, 5),
        0.5,
        dtype=np.float64,
    )

    domain = np.ones(
        initial.shape,
        dtype=bool,
    )

    treatment = FractionatedRadiotherapy(
        fraction_days=(
            0.0,
            1.0,
        ),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.1,
        beta_per_gy2=0.01,
    )

    result = simulate_reaction_diffusion(
        initial,
        _zero_dynamics(),
        spacing=(2.0, 2.0, 2.0),
        duration_days=1.0,
        dt=1.0,
        domain_mask=domain,
        treatment=treatment,
    )

    survival = (
        treatment
        .survival_fraction_per_fraction
    )

    expected = (
        initial
        * survival**2
    )

    np.testing.assert_allclose(
        result,
        expected,
    )


def test_integrated_pirt_applies_density_dependent_update(
) -> None:
    initial = np.full(
        (5, 5, 5),
        0.5,
        dtype=np.float64,
    )

    domain = np.ones(
        initial.shape,
        dtype=bool,
    )

    treatment = (
        PIRTFractionatedRadiotherapy(
            fraction_days=(
                0.0,
                1.0,
            ),
            dose_per_fraction_gy=2.0,
            alpha_per_gy=0.1,
            beta_per_gy2=0.01,
        )
    )

    result = simulate_reaction_diffusion(
        initial,
        _zero_dynamics(),
        spacing=(2.0, 2.0, 2.0),
        duration_days=1.0,
        dt=1.0,
        domain_mask=domain,
        treatment=treatment,
    )

    survival = (
        treatment
        .survival_fraction_per_fraction
    )

    expected = apply_pirt_fraction(
        initial,
        survival_fraction=survival,
        domain_mask=domain,
    )

    expected = apply_pirt_fraction(
        expected,
        survival_fraction=survival,
        domain_mask=domain,
    )

    np.testing.assert_allclose(
        result,
        expected,
    )


def test_integrated_pirt_is_not_multiplicative() -> None:
    initial = np.full(
        (5, 5, 5),
        0.5,
        dtype=np.float64,
    )

    domain = np.ones(
        initial.shape,
        dtype=bool,
    )

    pirt = PIRTFractionatedRadiotherapy(
        fraction_days=(0.0,),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.1,
        beta_per_gy2=0.01,
    )

    multiplicative = (
        FractionatedRadiotherapy(
            fraction_days=(0.0,),
            dose_per_fraction_gy=2.0,
            alpha_per_gy=0.1,
            beta_per_gy2=0.01,
        )
    )

    pirt_result = (
        simulate_reaction_diffusion(
            initial,
            _zero_dynamics(),
            spacing=(2.0, 2.0, 2.0),
            duration_days=1.0,
            dt=1.0,
            domain_mask=domain,
            treatment=pirt,
        )
    )

    multiplicative_result = (
        simulate_reaction_diffusion(
            initial,
            _zero_dynamics(),
            spacing=(2.0, 2.0, 2.0),
            duration_days=1.0,
            dt=1.0,
            domain_mask=domain,
            treatment=multiplicative,
        )
    )

    assert not np.allclose(
        pirt_result,
        multiplicative_result,
    )

    assert np.all(
        pirt_result
        > multiplicative_result
    )


def test_integrated_pirt_matches_existing_wrapper() -> None:
    initial = np.full(
        (7, 7, 7),
        0.5,
        dtype=np.float32,
    )

    domain = np.ones(
        initial.shape,
        dtype=bool,
    )

    parameters = ReactionDiffusionParameters(
        diffusion=0.005,
        proliferation=0.02,
    )

    treatment = (
        PIRTFractionatedRadiotherapy(
            fraction_days=(
                1.0,
                2.0,
            ),
            dose_per_fraction_gy=2.0,
            alpha_per_gy=0.025,
            beta_per_gy2=0.0025,
        )
    )

    integrated = (
        simulate_reaction_diffusion(
            initial,
            parameters,
            spacing=(2.0, 2.0, 2.0),
            duration_days=3.0,
            dt=1.0,
            domain_mask=domain,
            treatment=treatment,
        )
    )

    wrapper = (
        simulate_reaction_diffusion_pirt(
            initial,
            parameters,
            spacing=(2.0, 2.0, 2.0),
            duration_days=3.0,
            dt=1.0,
            domain_mask=domain,
            fraction_days=(
                treatment.fraction_days
            ),
            survival_fraction=(
                treatment
                .survival_fraction_per_fraction
            ),
        )
    )

    np.testing.assert_allclose(
        integrated,
        wrapper,
        rtol=1e-6,
        atol=1e-7,
    )


def test_integrated_pirt_preserves_float32() -> None:
    initial = np.full(
        (5, 5, 5),
        0.5,
        dtype=np.float32,
    )

    domain = np.ones(
        initial.shape,
        dtype=bool,
    )

    treatment = (
        PIRTFractionatedRadiotherapy(
            fraction_days=(0.0,),
            dose_per_fraction_gy=2.0,
            alpha_per_gy=0.1,
            beta_per_gy2=0.01,
        )
    )

    result = simulate_reaction_diffusion(
        initial,
        _zero_dynamics(),
        spacing=(2.0, 2.0, 2.0),
        duration_days=1.0,
        dt=1.0,
        domain_mask=domain,
        treatment=treatment,
    )

    assert result.dtype == np.float32