from __future__ import annotations

import numpy as np
from scipy.ndimage import (
    distance_transform_edt,
)

from gbm_twin.anatomy.models import (
    AnatomicalRiskReport,
    AnatomicalWarning,
    AtlasRegionDefinition,
)

DEFAULT_LATENT_RISK_LEVEL = 0.2

DEFAULT_PROXIMITY_THRESHOLD_MM = 5.0


def _voxel_volume_cm3(
    spacing: tuple[
        float,
        float,
        float,
    ],
) -> float:
    return (
        float(
            spacing[0]
            * spacing[1]
            * spacing[2]
        )
        / 1000.0
    )


def _minimum_distance_to_region(
    source_mask: np.ndarray,
    region_mask: np.ndarray,
    *,
    spacing: tuple[
        float,
        float,
        float,
    ],
) -> float | None:
    source = np.asarray(
        source_mask,
        dtype=bool,
    )

    region = np.asarray(
        region_mask,
        dtype=bool,
    )

    if (
        source.shape
        != region.shape
    ):
        raise ValueError(
            "source_mask and region_mask "
            "must use the same grid"
        )

    if not np.any(
        source
    ):
        return None

    if not np.any(
        region
    ):
        return None

    if np.any(
        source
        & region
    ):
        return 0.0

    distance_result = (
        distance_transform_edt(
            ~region,
            sampling=spacing,
            return_distances=True,
            return_indices=False,
        )
    )

    if distance_result is None:
        raise RuntimeError(
            "SciPy distance transform "
            "did not return distances"
        )

    distance_to_region = (
        np.asarray(
            distance_result,
            dtype=np.float64,
        )
    )

    source_distances = (
        distance_to_region[
            source
        ]
    )

    if (
        source_distances.size
        == 0
    ):
        return None

    return float(
        np.min(
            source_distances
        )
    )


def _warning_message(
    region: AtlasRegionDefinition,
    *,
    observed_overlap_cm3: float,
    latent_overlap_cm3: float,
    min_distance_mm: float | None,
    latent_level: float,
) -> str:
    region_text = (
        "atlas-defined "
        f"{region.name}"
    )

    if observed_overlap_cm3 > 0:
        return (
            "Observed GTV intersects "
            f"{region_text}."
        )

    if latent_overlap_cm3 > 0:
        return (
            "Latent tumor state "
            f"c(x) ≥ {latent_level:.2f} "
            "intersects "
            f"{region_text}."
        )

    if min_distance_mm is not None:
        return (
            "Observed GTV is "
            f"{min_distance_mm:.1f} mm "
            "from "
            f"{region_text}."
        )

    return (
        "Tumor state is near "
        f"{region_text}."
    )


def _severity_rank(
    warning: AnatomicalWarning,
) -> int:
    if (
        warning.severity
        == "high"
    ):
        return 0

    if (
        warning.severity
        == "moderate"
    ):
        return 1

    return 2


def _warning_sort_key(
    warning: AnatomicalWarning,
) -> tuple[
    int,
    float,
    float,
    str,
]:
    return (
        _severity_rank(
            warning
        ),
        -float(
            warning
            .observed_overlap_cm3
        ),
        -float(
            warning
            .latent_overlap_cm3
        ),
        warning.region_name,
    )


def compute_anatomical_risk(
    *,
    patient_id: int,
    timepoint_name: str,
    labelmap: np.ndarray,
    regions: tuple[
        AtlasRegionDefinition,
        ...,
    ],
    gtv_mask: np.ndarray,
    latent_state: np.ndarray,
    spacing: tuple[
        float,
        float,
        float,
    ],
    atlas_name: str,
    latent_level: float = (
        DEFAULT_LATENT_RISK_LEVEL
    ),
    proximity_threshold_mm: float = (
        DEFAULT_PROXIMITY_THRESHOLD_MM
    ),
) -> AnatomicalRiskReport:
    if patient_id <= 0:
        raise ValueError(
            "patient_id must be positive"
        )

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

    if labelmap.ndim != 3:
        raise ValueError(
            "labelmap must be 3D"
        )

    if gtv_mask.ndim != 3:
        raise ValueError(
            "gtv_mask must be 3D"
        )

    if latent_state.ndim != 3:
        raise ValueError(
            "latent_state must be 3D"
        )

    if (
        labelmap.shape
        != gtv_mask.shape
        or labelmap.shape
        != latent_state.shape
    ):
        raise ValueError(
            "Atlas, GTV and latent state "
            "must use the same grid"
        )

    if any(
        value <= 0
        for value in spacing
    ):
        raise ValueError(
            "spacing must be positive"
        )

    if not (
        0.0
        < latent_level
        < 1.0
    ):
        raise ValueError(
            "latent_level must be "
            "between 0 and 1"
        )

    if (
        proximity_threshold_mm
        < 0
    ):
        raise ValueError(
            "proximity_threshold_mm "
            "must be non-negative"
        )

    if not np.all(
        np.isfinite(
            latent_state
        )
    ):
        raise ValueError(
            "latent_state contains "
            "non-finite values"
        )

    atlas_name_clean = (
        atlas_name.strip()
    )

    if not atlas_name_clean:
        raise ValueError(
            "atlas_name cannot be empty"
        )

    observed = np.asarray(
        gtv_mask,
        dtype=bool,
    )

    latent = np.asarray(
        latent_state,
        dtype=np.float32,
    )

    atlas_labels = np.asarray(
        labelmap,
        dtype=np.int32,
    )

    latent_mask = (
        latent
        >= latent_level
    )

    voxel_volume = (
        _voxel_volume_cm3(
            spacing
        )
    )

    warnings: list[
        AnatomicalWarning
    ] = []

    for region in regions:
        region_mask = (
            atlas_labels
            == region.label
        )

        if not np.any(
            region_mask
        ):
            continue

        observed_overlap_voxels = (
            int(
                np.count_nonzero(
                    observed
                    & region_mask
                )
            )
        )

        latent_overlap_voxels = (
            int(
                np.count_nonzero(
                    latent_mask
                    & region_mask
                )
            )
        )

        observed_overlap_cm3 = (
            float(
                observed_overlap_voxels
                * voxel_volume
            )
        )

        latent_overlap_cm3 = (
            float(
                latent_overlap_voxels
                * voxel_volume
            )
        )

        min_distance_mm = (
            _minimum_distance_to_region(
                observed,
                region_mask,
                spacing=spacing,
            )
        )

        if (
            observed_overlap_voxels
            > 0
        ):
            severity = "high"

        elif (
            latent_overlap_voxels
            > 0
        ):
            severity = "moderate"

        elif (
            min_distance_mm
            is not None
            and min_distance_mm
            <= proximity_threshold_mm
        ):
            severity = "moderate"

        else:
            continue

        warning = (
            AnatomicalWarning(
                severity=severity,
                region_label=(
                    region.label
                ),
                region_name=(
                    region.name
                ),
                category=(
                    region.category
                ),
                laterality=(
                    region.laterality
                ),
                functional_note=(
                    region.functional_note
                ),
                observed_overlap_cm3=(
                    observed_overlap_cm3
                ),
                latent_overlap_cm3=(
                    latent_overlap_cm3
                ),
                min_observed_distance_mm=(
                    min_distance_mm
                ),
                message=_warning_message(
                    region,
                    observed_overlap_cm3=(
                        observed_overlap_cm3
                    ),
                    latent_overlap_cm3=(
                        latent_overlap_cm3
                    ),
                    min_distance_mm=(
                        min_distance_mm
                    ),
                    latent_level=(
                        latent_level
                    ),
                ),
            )
        )

        warnings.append(
            warning
        )

    warnings.sort(
        key=_warning_sort_key
    )

    return AnatomicalRiskReport(
        patient_id=patient_id,
        timepoint_name=(
            normalized_timepoint
        ),
        configured=True,
        atlas_name=(
            atlas_name_clean
        ),
        status_message=(
            "Patient-space atlas analysis "
            "completed."
        ),
        latent_level=(
            latent_level
        ),
        proximity_threshold_mm=(
            proximity_threshold_mm
        ),
        warnings=tuple(
            warnings
        ),
    )