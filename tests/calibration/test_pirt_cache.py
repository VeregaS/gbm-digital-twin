import numpy as np

from gbm_twin.calibration.cache import (
    build_calibration_signature,
    candidate_cache_key,
    treatment_signature,
)
from gbm_twin.models.treatment import (
    FractionatedRadiotherapy,
    PIRTFractionatedRadiotherapy,
)


def _multiplicative_rt(
) -> FractionatedRadiotherapy:
    return FractionatedRadiotherapy(
        fraction_days=(
            1.0,
            2.0,
        ),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.1,
        beta_per_gy2=0.01,
    )


def _pirt_rt(
) -> PIRTFractionatedRadiotherapy:
    return PIRTFractionatedRadiotherapy(
        fraction_days=(
            1.0,
            2.0,
        ),
        dose_per_fraction_gy=2.0,
        alpha_per_gy=0.1,
        beta_per_gy2=0.01,
    )


def test_pirt_has_distinct_treatment_signature() -> None:
    multiplicative = treatment_signature(
        _multiplicative_rt()
    )

    pirt = treatment_signature(
        _pirt_rt()
    )

    assert multiplicative is not None
    assert pirt is not None

    assert (
        multiplicative["type"]
        == "fractionated_rt"
    )

    assert (
        pirt["type"]
        == "pirt_fractionated_rt"
    )

    assert (
        multiplicative
        != pirt
    )


def test_pirt_and_multiplicative_cache_keys_differ() -> None:
    initial = np.full(
        (3, 3, 3),
        0.5,
        dtype=np.float32,
    )

    observed = np.ones(
        initial.shape,
        dtype=bool,
    )

    domain = np.ones(
        initial.shape,
        dtype=bool,
    )

    common = {
        "initial_field": initial,
        "observed_mask": observed,
        "domain_mask": domain,
        "spacing": (
            2.0,
            2.0,
            2.0,
        ),
        "duration_days": 10.0,
        "dt": 1.0,
        "threshold": 0.5,
        "start_time_day": 0.0,
    }

    multiplicative_signature = (
        build_calibration_signature(
            **common,
            treatment=(
                _multiplicative_rt()
            ),
        )
    )

    pirt_signature = (
        build_calibration_signature(
            **common,
            treatment=_pirt_rt(),
        )
    )

    multiplicative_key = (
        candidate_cache_key(
            multiplicative_signature,
            diffusion=0.005,
            proliferation=0.035,
        )
    )

    pirt_key = candidate_cache_key(
        pirt_signature,
        diffusion=0.005,
        proliferation=0.035,
    )

    assert (
        multiplicative_key
        != pirt_key
    )