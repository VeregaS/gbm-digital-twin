import numpy as np
import pytest

from gbm_twin.anatomy.models import (
    AtlasRegionDefinition,
)
from gbm_twin.anatomy.risk import (
    compute_anatomical_risk,
)


def test_observed_overlap_is_high() -> None:
    shape = (
        12,
        12,
        12,
    )

    labels = np.zeros(
        shape,
        dtype=np.int32,
    )

    labels[
        4:7,
        4:7,
        4:7,
    ] = 1

    gtv = np.zeros(
        shape,
        dtype=bool,
    )

    gtv[
        5:8,
        5:8,
        5:8,
    ] = True

    latent = (
        gtv.astype(
            np.float32
        )
    )

    regions = (
        AtlasRegionDefinition(
            label=1,
            name=(
                "Left precentral region"
            ),
            category="motor",
            laterality="left",
            functional_note=(
                "Motor-associated cortex"
            ),
        ),
    )

    result = (
        compute_anatomical_risk(
            patient_id=108,
            timepoint_name="t1",
            labelmap=labels,
            regions=regions,
            gtv_mask=gtv,
            latent_state=latent,
            spacing=(
                2.0,
                2.0,
                2.0,
            ),
            atlas_name=(
                "Synthetic atlas"
            ),
        )
    )

    assert result.configured
    assert result.high_count == 1
    assert result.moderate_count == 0

    warning = (
        result.warnings[0]
    )

    assert (
        warning.severity
        == "high"
    )

    assert (
        warning
        .observed_overlap_cm3
        > 0
    )


def test_latent_overlap_is_moderate() -> None:
    shape = (
        12,
        12,
        12,
    )

    labels = np.zeros(
        shape,
        dtype=np.int32,
    )

    labels[
        8:10,
        8:10,
        8:10,
    ] = 2

    gtv = np.zeros(
        shape,
        dtype=bool,
    )

    gtv[
        2:4,
        2:4,
        2:4,
    ] = True

    latent = np.zeros(
        shape,
        dtype=np.float32,
    )

    latent[
        8:10,
        8:10,
        8:10,
    ] = 0.4

    regions = (
        AtlasRegionDefinition(
            label=2,
            name=(
                "Left language region"
            ),
            category="language",
            laterality="left",
        ),
    )

    result = (
        compute_anatomical_risk(
            patient_id=108,
            timepoint_name="t1",
            labelmap=labels,
            regions=regions,
            gtv_mask=gtv,
            latent_state=latent,
            spacing=(
                2.0,
                2.0,
                2.0,
            ),
            atlas_name="Test",
        )
    )

    assert result.high_count == 0
    assert result.moderate_count == 1

    warning = (
        result.warnings[0]
    )

    assert (
        warning.severity
        == "moderate"
    )

    assert (
        warning.latent_overlap_cm3
        > 0
    )


def test_near_region_is_moderate() -> None:
    shape = (
        12,
        12,
        12,
    )

    labels = np.zeros(
        shape,
        dtype=np.int32,
    )

    labels[
        6,
        5,
        5,
    ] = 1

    gtv = np.zeros(
        shape,
        dtype=bool,
    )

    gtv[
        4,
        5,
        5,
    ] = True

    latent = (
        gtv.astype(
            np.float32
        )
    )

    regions = (
        AtlasRegionDefinition(
            label=1,
            name="Motor region",
            category="motor",
        ),
    )

    result = (
        compute_anatomical_risk(
            patient_id=1,
            timepoint_name="t0",
            labelmap=labels,
            regions=regions,
            gtv_mask=gtv,
            latent_state=latent,
            spacing=(
                2.0,
                2.0,
                2.0,
            ),
            atlas_name="Test",
            proximity_threshold_mm=5.0,
        )
    )

    assert len(
        result.warnings
    ) == 1

    assert (
        result.warnings[0]
        .min_observed_distance_mm
        == pytest.approx(
            4.0
        )
    )


def test_far_region_is_not_reported() -> None:
    shape = (
        20,
        20,
        20,
    )

    labels = np.zeros(
        shape,
        dtype=np.int32,
    )

    labels[
        18,
        18,
        18,
    ] = 1

    gtv = np.zeros(
        shape,
        dtype=bool,
    )

    gtv[
        1,
        1,
        1,
    ] = True

    latent = (
        gtv.astype(
            np.float32
        )
    )

    regions = (
        AtlasRegionDefinition(
            label=1,
            name="Visual region",
            category="visual",
        ),
    )

    result = (
        compute_anatomical_risk(
            patient_id=1,
            timepoint_name="t0",
            labelmap=labels,
            regions=regions,
            gtv_mask=gtv,
            latent_state=latent,
            spacing=(
                2.0,
                2.0,
                2.0,
            ),
            atlas_name="Test",
        )
    )

    assert result.warnings == ()