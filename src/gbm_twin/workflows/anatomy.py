from __future__ import annotations

from pathlib import Path

import numpy as np

from gbm_twin.anatomy.atlas import (
    load_registered_atlas,
)
from gbm_twin.anatomy.models import (
    AnatomicalRiskReport,
)
from gbm_twin.anatomy.risk import (
    DEFAULT_LATENT_RISK_LEVEL,
    DEFAULT_PROXIMITY_THRESHOLD_MM,
    compute_anatomical_risk,
)
from gbm_twin.models.latent_state import (
    LatentStateParameters,
    latent_state_from_gtv,
)
from gbm_twin.workflows.patients import (
    DEFAULT_TARGET_SPACING,
    prepare_patient_timepoint,
)

ANATOMICAL_LATENT_WIDTH_MM = 4.0


def _unavailable_report(
    *,
    patient_id: int,
    timepoint_name: str,
    status_message: str,
) -> AnatomicalRiskReport:
    return AnatomicalRiskReport(
        patient_id=patient_id,
        timepoint_name=timepoint_name,
        configured=False,
        atlas_name=None,
        status_message=status_message,
        latent_level=(
            DEFAULT_LATENT_RISK_LEVEL
        ),
        proximity_threshold_mm=(
            DEFAULT_PROXIMITY_THRESHOLD_MM
        ),
        warnings=(),
    )


def analyze_patient_anatomy(
    *,
    metadata_root: Path,
    patients_root: Path,
    atlas_root: Path | None,
    patient_id: int,
    timepoint_name: str,
) -> AnatomicalRiskReport:
    normalized_timepoint = (
        timepoint_name
        .strip()
        .lower()
    )

    if normalized_timepoint not in {
        "t0",
        "t1",
        "t2",
    }:
        raise ValueError(
            "timepoint_name must be "
            "t0, t1 or t2"
        )

    prepared = (
        prepare_patient_timepoint(
            metadata_root=metadata_root,
            patients_root=patients_root,
            patient_id=patient_id,
            timepoint_name=(
                normalized_timepoint
            ),
            target_spacing=(
                DEFAULT_TARGET_SPACING
            ),
        )
    )

    if atlas_root is None:
        return _unavailable_report(
            patient_id=patient_id,
            timepoint_name=(
                normalized_timepoint
            ),
            status_message=(
                "Atlas analysis is not "
                "configured. Set "
                "GBM_TWIN_ATLAS_ROOT."
            ),
        )

    try:
        atlas = load_registered_atlas(
            atlas_root,
            patient_id=patient_id,
            timepoint_name=(
                normalized_timepoint
            ),
            expected_shape=(
                prepared.gtv.data.shape
            ),
            expected_affine=(
                prepared.gtv.affine
            ),
        )
    except (
        FileNotFoundError,
        ValueError,
    ) as exc:
        return _unavailable_report(
            patient_id=patient_id,
            timepoint_name=(
                normalized_timepoint
            ),
            status_message=str(exc),
        )

    latent_state = (
        latent_state_from_gtv(
            prepared.gtv.data,
            prepared.brain_mask.data,
            spacing=prepared.spacing,
            parameters=(
                LatentStateParameters(
                    transition_width_mm=(
                        ANATOMICAL_LATENT_WIDTH_MM
                    ),
                )
            ),
        )
    )

    gtv_mask = (
        np.asarray(
            prepared.gtv.data
        )
        > 0.5
    )

    return compute_anatomical_risk(
        patient_id=patient_id,
        timepoint_name=(
            normalized_timepoint
        ),
        labelmap=atlas.labelmap,
        regions=atlas.regions,
        gtv_mask=gtv_mask,
        latent_state=latent_state,
        spacing=prepared.spacing,
        atlas_name=atlas.name,
    )
