from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import (
    label as connected_components,
)

from gbm_twin.workflows.cohort_results import (
    load_sealed_cohort_evaluation,
)
from gbm_twin.workflows.patients import (
    prepare_patient_timepoint,
)
from gbm_twin.workflows.twin_artifacts import (
    find_evaluated_patient,
    load_frozen_patient_artifact,
    target_spacing,
)

BoolArray = NDArray[np.bool_]
IntArray = NDArray[np.int32]


class TwinQCWarningCode(StrEnum):
    OBSERVED_EMPTY = "observed_empty"
    OBSERVED_OUTSIDE_BRAIN = "observed_outside_brain"
    OBSERVED_FRAGMENTED = "observed_fragmented"

    TWIN_EMPTY = "twin_empty"
    TWIN_OUTSIDE_BRAIN = "twin_outside_brain"
    TWIN_FRAGMENTED = "twin_fragmented"

    PERSISTENCE_OUTSIDE_BRAIN = "persistence_outside_brain"

    VOLUME_BASELINE_OUTSIDE_BRAIN = (
        "volume_baseline_outside_brain"
    )


@dataclass(frozen=True)
class TwinMaskQC:
    name: str

    voxel_count: int
    volume_cm3: float

    component_count: int

    largest_component_fraction: float | None

    outside_brain_voxels: int
    outside_brain_fraction: float | None

    centroid_inside_brain: bool | None


@dataclass(frozen=True)
class TwinQCWarning:
    code: TwinQCWarningCode
    message: str


@dataclass(frozen=True)
class TwinPatientQC:
    patient_id: int

    observed: TwinMaskQC
    twin: TwinMaskQC
    persistence: TwinMaskQC
    volume_baseline: TwinMaskQC

    warnings: tuple[
        TwinQCWarning,
        ...,
    ]


def _as_mask(
    value: object,
) -> BoolArray:
    return np.asarray(
        value,
        dtype=np.bool_,
    )


def _validate_shape(
    *,
    name: str,
    mask: BoolArray,
    brain: BoolArray,
) -> None:
    if mask.shape != brain.shape:
        raise ValueError(
            f"{name} shape {mask.shape} "
            "does not match brain mask "
            f"shape {brain.shape}"
        )

    if mask.ndim != 3:
        raise ValueError(
            f"{name} must be 3D"
        )


def _connected_component_statistics(
    mask: BoolArray,
) -> tuple[
    int,
    float | None,
]:
    """
    Return connected-component count and the fraction of mask voxels
    contained in the largest connected component.

    scipy.ndimage.label has overload-dependent return types. Supplying an
    explicit output array makes the operation deterministic for us, and we
    derive the component count from the populated label map instead of using
    scipy's overloaded return value.
    """

    if mask.ndim != 3:
        raise ValueError(
            "Connected-component analysis requires a 3D mask"
        )

    voxel_count = int(
        np.count_nonzero(
            mask
        )
    )

    if voxel_count == 0:
        return (
            0,
            None,
        )

    component_labels: IntArray = np.zeros(
        mask.shape,
        dtype=np.int32,
    )

    # Intentionally ignore scipy.ndimage.label's overload-dependent return
    # value. With output supplied, component_labels is populated in place.
    connected_components(
        mask,
        output=component_labels,
    )

    if component_labels.size == 0:
        return (
            0,
            None,
        )

    component_count = int(
        component_labels.max()
    )

    if component_count <= 0:
        return (
            0,
            None,
        )

    counts = np.bincount(
        component_labels.reshape(-1)
    )

    component_sizes = counts[
        1 : component_count + 1
    ]

    if component_sizes.size == 0:
        return (
            component_count,
            None,
        )

    largest_component = int(
        component_sizes.max()
    )

    largest_component_fraction = (
        largest_component
        / voxel_count
    )

    return (
        component_count,
        float(
            largest_component_fraction
        ),
    )


def _centroid_inside_brain(
    *,
    mask: BoolArray,
    brain: BoolArray,
) -> bool | None:
    coordinates = np.argwhere(
        mask
    )

    if coordinates.size == 0:
        return None

    centroid = np.mean(
        coordinates,
        axis=0,
    )

    if centroid.shape != (3,):
        raise ValueError(
            "Expected a 3D mask centroid"
        )

    x = int(
        round(
            float(
                centroid[0]
            )
        )
    )

    y = int(
        round(
            float(
                centroid[1]
            )
        )
    )

    z = int(
        round(
            float(
                centroid[2]
            )
        )
    )

    x = min(
        max(
            x,
            0,
        ),
        brain.shape[0] - 1,
    )

    y = min(
        max(
            y,
            0,
        ),
        brain.shape[1] - 1,
    )

    z = min(
        max(
            z,
            0,
        ),
        brain.shape[2] - 1,
    )

    return bool(
        brain[
            x,
            y,
            z,
        ]
    )


def _mask_qc(
    *,
    name: str,
    mask: BoolArray,
    brain: BoolArray,
    spacing: tuple[
        float,
        float,
        float,
    ],
) -> TwinMaskQC:
    _validate_shape(
        name=name,
        mask=mask,
        brain=brain,
    )

    voxel_count = int(
        np.count_nonzero(
            mask
        )
    )

    voxel_volume_mm3 = (
        spacing[0]
        * spacing[1]
        * spacing[2]
    )

    volume_cm3 = (
        voxel_count
        * voxel_volume_mm3
        / 1000.0
    )

    (
        component_count,
        largest_component_fraction,
    ) = _connected_component_statistics(
        mask
    )

    outside = np.asarray(
        mask
        & ~brain,
        dtype=np.bool_,
    )

    outside_brain_voxels = int(
        np.count_nonzero(
            outside
        )
    )

    outside_brain_fraction = (
        None
        if voxel_count == 0
        else (
            outside_brain_voxels
            / voxel_count
        )
    )

    centroid_inside_brain = (
        _centroid_inside_brain(
            mask=mask,
            brain=brain,
        )
    )

    return TwinMaskQC(
        name=name,
        voxel_count=voxel_count,
        volume_cm3=float(
            volume_cm3
        ),
        component_count=(
            component_count
        ),
        largest_component_fraction=(
            largest_component_fraction
        ),
        outside_brain_voxels=(
            outside_brain_voxels
        ),
        outside_brain_fraction=(
            outside_brain_fraction
        ),
        centroid_inside_brain=(
            centroid_inside_brain
        ),
    )


def _append_warnings(
    *,
    target: list[
        TwinQCWarning
    ],
    qc: TwinMaskQC,
    display_name: str,
    empty_code: TwinQCWarningCode | None,
    outside_code: TwinQCWarningCode | None,
    fragmented_code: TwinQCWarningCode | None,
) -> None:
    if (
        qc.voxel_count == 0
        and empty_code is not None
    ):
        target.append(
            TwinQCWarning(
                code=empty_code,
                message=(
                    f"{display_name} mask "
                    "is empty."
                ),
            )
        )

    outside_fraction = (
        qc.outside_brain_fraction
    )

    if (
        outside_code is not None
        and outside_fraction is not None
        and outside_fraction > 0.001
    ):
        target.append(
            TwinQCWarning(
                code=outside_code,
                message=(
                    f"{display_name} has "
                    f"{outside_fraction * 100.0:.2f}% "
                    "of mask voxels outside "
                    "the brain mask."
                ),
            )
        )

    largest_fraction = (
        qc.largest_component_fraction
    )

    if (
        fragmented_code is not None
        and qc.component_count > 1
        and largest_fraction is not None
        and largest_fraction < 0.95
    ):
        target.append(
            TwinQCWarning(
                code=fragmented_code,
                message=(
                    f"{display_name} contains "
                    f"{qc.component_count} connected "
                    "components; the largest contains "
                    f"{largest_fraction * 100.0:.1f}% "
                    "of lesion voxels."
                ),
            )
        )


def get_twin_patient_qc(
    *,
    metadata_root: Path,
    patients_root: Path,
    cohort_freeze_root: Path,
    cohort_evaluation_root: Path,
    patient_id: int,
) -> TwinPatientQC:
    evaluation = (
        load_sealed_cohort_evaluation(
            cohort_evaluation_root
        )
    )

    payload = (
        evaluation.manifest
    )

    patient = (
        find_evaluated_patient(
            payload,
            patient_id,
        )
    )

    spacing = (
        target_spacing(
            payload
        )
    )

    target = (
        prepare_patient_timepoint(
            metadata_root=(
                metadata_root
            ),
            patients_root=(
                patients_root
            ),
            patient_id=(
                patient_id
            ),
            timepoint_name=(
                patient[
                    "target_timepoint"
                ]
            ),
            target_spacing=(
                spacing
            ),
        )
    )

    artifact = (
        load_frozen_patient_artifact(
            cohort_freeze_root=(
                cohort_freeze_root
            ),
            payload=payload,
            patient_id=(
                patient_id
            ),
        )
    )

    brain = _as_mask(
        np.asarray(
            target.brain_mask.data
        )
        > 0.5
    )

    observed = _as_mask(
        np.asarray(
            target.gtv.data
        )
        > 0.5
    )

    twin = _as_mask(
        artifact.prediction_mask
    )

    persistence = _as_mask(
        artifact.persistence_mask
    )

    volume_baseline = _as_mask(
        artifact.volume_baseline_mask
    )

    observed_qc = (
        _mask_qc(
            name="observed",
            mask=observed,
            brain=brain,
            spacing=spacing,
        )
    )

    twin_qc = (
        _mask_qc(
            name="twin",
            mask=twin,
            brain=brain,
            spacing=spacing,
        )
    )

    persistence_qc = (
        _mask_qc(
            name="persistence",
            mask=persistence,
            brain=brain,
            spacing=spacing,
        )
    )

    volume_baseline_qc = (
        _mask_qc(
            name="volume_baseline",
            mask=volume_baseline,
            brain=brain,
            spacing=spacing,
        )
    )

    warnings: list[
        TwinQCWarning
    ] = []

    _append_warnings(
        target=warnings,
        qc=observed_qc,
        display_name=(
            "Observed t2"
        ),
        empty_code=(
            TwinQCWarningCode
            .OBSERVED_EMPTY
        ),
        outside_code=(
            TwinQCWarningCode
            .OBSERVED_OUTSIDE_BRAIN
        ),
        fragmented_code=(
            TwinQCWarningCode
            .OBSERVED_FRAGMENTED
        ),
    )

    _append_warnings(
        target=warnings,
        qc=twin_qc,
        display_name=(
            "Twin prediction"
        ),
        empty_code=(
            TwinQCWarningCode
            .TWIN_EMPTY
        ),
        outside_code=(
            TwinQCWarningCode
            .TWIN_OUTSIDE_BRAIN
        ),
        fragmented_code=(
            TwinQCWarningCode
            .TWIN_FRAGMENTED
        ),
    )

    _append_warnings(
        target=warnings,
        qc=persistence_qc,
        display_name=(
            "Persistence baseline"
        ),
        empty_code=None,
        outside_code=(
            TwinQCWarningCode
            .PERSISTENCE_OUTSIDE_BRAIN
        ),
        fragmented_code=None,
    )

    _append_warnings(
        target=warnings,
        qc=volume_baseline_qc,
        display_name=(
            "Volume baseline"
        ),
        empty_code=None,
        outside_code=(
            TwinQCWarningCode
            .VOLUME_BASELINE_OUTSIDE_BRAIN
        ),
        fragmented_code=None,
    )

    return TwinPatientQC(
        patient_id=(
            patient_id
        ),
        observed=(
            observed_qc
        ),
        twin=(
            twin_qc
        ),
        persistence=(
            persistence_qc
        ),
        volume_baseline=(
            volume_baseline_qc
        ),
        warnings=tuple(
            warnings
        ),
    )