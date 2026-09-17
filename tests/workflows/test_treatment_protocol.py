import pytest

from gbm_twin.data.cfb_treatment import TreatmentRecord
from gbm_twin.models.radiobiology import RadiobiologyParameters
from gbm_twin.models.treatment import (
    PIRTFractionatedRadiotherapy,
    RadiotherapyProtocol,
)
from gbm_twin.workflows.treatment_protocol import (
    PostRadiotherapyConfig,
    reconstruct_patient_treatment,
)


def make_record() -> TreatmentRecord:
    return TreatmentRecord(
        patient_id=42,
        delay_t0_to_radiotherapy_weeks=2.0,
        dose_gy=60.0,
        fractions_number=30,
    )


def make_radiobiology() -> RadiobiologyParameters:
    return RadiobiologyParameters(
        alpha_per_gy=0.01,
        alpha_beta_ratio_gy=10.0,
    )


def test_reconstruct_patient_treatment_keeps_v2_fractionated_model() -> None:
    result = reconstruct_patient_treatment(
        make_record(),
        radiobiology=make_radiobiology(),
    )

    assert isinstance(
        result.model,
        PIRTFractionatedRadiotherapy,
    )
    assert result.schedule.start_day == 14.0
    assert result.schedule.fractions_number == 30


def test_reconstruct_patient_treatment_adds_post_rt_effect() -> None:
    result = reconstruct_patient_treatment(
        make_record(),
        radiobiology=make_radiobiology(),
        post_rt=PostRadiotherapyConfig(
            initial_kill_rate_per_day=0.005,
            decay_time_days=60.0,
        ),
    )

    assert isinstance(
        result.model,
        RadiotherapyProtocol,
    )

    effect = result.model.post_effect

    assert effect is not None
    assert effect.start_day == (
        result.schedule.fraction_days[-1]
    )
    assert effect.initial_kill_rate == pytest.approx(
        0.005
    )
    assert effect.decay_time_days == pytest.approx(
        60.0
    )


def test_post_rt_config_rejects_nonpositive_values() -> None:
    with pytest.raises(
        ValueError,
        match="kill rate",
    ):
        PostRadiotherapyConfig(
            initial_kill_rate_per_day=0.0,
            decay_time_days=60.0,
        )

    with pytest.raises(
        ValueError,
        match="decay time",
    ):
        PostRadiotherapyConfig(
            initial_kill_rate_per_day=0.005,
            decay_time_days=0.0,
        )
