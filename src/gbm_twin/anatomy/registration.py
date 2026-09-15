from __future__ import annotations

import json
from dataclasses import (
    asdict,
    dataclass,
)
from datetime import (
    UTC,
    datetime,
)
from pathlib import Path

import numpy as np
import SimpleITK as sitk


@dataclass(frozen=True)
class RegistrationConfig:
    histogram_bins: int = 50

    sampling_percentage: float = 0.25

    random_seed: int = 42

    rigid_iterations: int = 200

    affine_iterations: int = 200

    rigid_learning_rate: float = 2.0

    rigid_min_step: float = 0.001

    affine_learning_rate: float = 0.25

    affine_min_step: float = 0.0005

    shrink_factors: tuple[
        int,
        ...,
    ] = (
        4,
        2,
        1,
    )

    smoothing_sigmas: tuple[
        float,
        ...,
    ] = (
        2.0,
        1.0,
        0.0,
    )

    linear_max_brain_dice_drop: float = (
        0.01
    )

    linear_max_inside_fraction_drop: float = (
        0.02
    )

    enable_bspline: bool = True

    bspline_control_point_spacing_mm: float = (
        40.0
    )

    bspline_iterations: int = 100

    bspline_max_coefficient_mm: float = (
        10.0
    )

    bspline_max_displacement_mm: float = (
        12.0
    )

    bspline_min_jacobian: float = (
        0.30
    )

    bspline_max_jacobian: float = (
        3.00
    )

    bspline_max_nonpositive_fraction: float = (
        0.0
    )

    deformable_max_brain_dice_drop: float = (
        0.01
    )

    deformable_max_inside_fraction_drop: float = (
        0.02
    )

    quality_warn_brain_dice: float = (
        0.65
    )

    quality_fail_brain_dice: float = (
        0.45
    )

    quality_warn_inside_fraction: float = (
        0.85
    )

    quality_fail_inside_fraction: float = (
        0.60
    )


DEFAULT_REGISTRATION_CONFIG = (
    RegistrationConfig()
)


@dataclass(frozen=True)
class RegistrationQuality:
    brain_dice: float

    labeled_inside_brain_fraction: float

    status: str


@dataclass(frozen=True)
class DeformationQuality:
    minimum_jacobian: float

    maximum_jacobian: float

    nonpositive_jacobian_fraction: float

    maximum_displacement_mm: float

    acceptable: bool


@dataclass(frozen=True)
class OptimizationStage:
    success: bool

    metric_value: float | None

    valid_metric_points: int | None

    stop_condition: str

    quality: RegistrationQuality | None

    deformation: DeformationQuality | None

    error: str | None = None


@dataclass(frozen=True)
class RegistrationResult:
    output_dir: Path

    candidate_labels_path: Path

    registered_template_path: Path

    registered_brain_mask_path: Path

    linear_transform_path: Path

    deformable_transform_path: (
        Path | None
    )

    provenance_path: Path

    selected_stage: str

    metric_value: float

    optimizer_stop_condition: str

    quality: RegistrationQuality


class RegistrationQualityError(
    RuntimeError
):
    pass


def _validate_config(
    config: RegistrationConfig,
) -> None:
    if config.histogram_bins <= 1:
        raise ValueError(
            "histogram_bins must be > 1"
        )

    if not (
        0.0
        < config.sampling_percentage
        <= 1.0
    ):
        raise ValueError(
            "sampling_percentage must "
            "be in (0, 1]"
        )

    positive_values = {
        "rigid_iterations": (
            config.rigid_iterations
        ),
        "affine_iterations": (
            config.affine_iterations
        ),
        "rigid_learning_rate": (
            config.rigid_learning_rate
        ),
        "rigid_min_step": (
            config.rigid_min_step
        ),
        "affine_learning_rate": (
            config.affine_learning_rate
        ),
        "affine_min_step": (
            config.affine_min_step
        ),
        (
            "bspline_control_point_"
            "spacing_mm"
        ): (
            config
            .bspline_control_point_spacing_mm
        ),
        "bspline_iterations": (
            config.bspline_iterations
        ),
        (
            "bspline_max_"
            "coefficient_mm"
        ): (
            config
            .bspline_max_coefficient_mm
        ),
        (
            "bspline_max_"
            "displacement_mm"
        ): (
            config
            .bspline_max_displacement_mm
        ),
        "bspline_min_jacobian": (
            config.bspline_min_jacobian
        ),
        "bspline_max_jacobian": (
            config.bspline_max_jacobian
        ),
    }

    for (
        name,
        value,
    ) in positive_values.items():
        if value <= 0:
            raise ValueError(
                f"{name} must be positive"
            )

    if len(
        config.shrink_factors
    ) != len(
        config.smoothing_sigmas
    ):
        raise ValueError(
            "shrink_factors and "
            "smoothing_sigmas must "
            "have equal length"
        )

    if any(
        value <= 0
        for value
        in config.shrink_factors
    ):
        raise ValueError(
            "shrink_factors must "
            "be positive"
        )

    if any(
        value < 0
        for value
        in config.smoothing_sigmas
    ):
        raise ValueError(
            "smoothing_sigmas must "
            "be non-negative"
        )

    fractions = (
        config
        .linear_max_brain_dice_drop,
        config
        .linear_max_inside_fraction_drop,
        config
        .bspline_max_nonpositive_fraction,
        config
        .deformable_max_brain_dice_drop,
        config
        .deformable_max_inside_fraction_drop,
    )

    if any(
        value < 0
        for value
        in fractions
    ):
        raise ValueError(
            "Registration tolerances "
            "must be non-negative"
        )

    if (
        config.bspline_max_jacobian
        <= config.bspline_min_jacobian
    ):
        raise ValueError(
            "bspline_max_jacobian "
            "must exceed "
            "bspline_min_jacobian"
        )


def _read_float_image(
    path: Path,
) -> sitk.Image:
    return sitk.ReadImage(
        str(path),
        sitk.sitkFloat32,
    )


def _read_binary_mask(
    path: Path,
) -> sitk.Image:
    image = sitk.ReadImage(
        str(path)
    )

    return sitk.Cast(
        image > 0,
        sitk.sitkUInt8,
    )


def _dice(
    first: np.ndarray,
    second: np.ndarray,
) -> float:
    first_mask = np.asarray(
        first,
        dtype=bool,
    )

    second_mask = np.asarray(
        second,
        dtype=bool,
    )

    if (
        first_mask.shape
        != second_mask.shape
    ):
        raise ValueError(
            "Dice masks must "
            "share shape"
        )

    first_count = int(
        np.count_nonzero(
            first_mask
        )
    )

    second_count = int(
        np.count_nonzero(
            second_mask
        )
    )

    denominator = (
        first_count
        + second_count
    )

    if denominator == 0:
        return 1.0

    intersection = int(
        np.count_nonzero(
            first_mask
            & second_mask
        )
    )

    return float(
        2.0
        * intersection
        / denominator
    )


def _labels_inside_fraction(
    labels: np.ndarray,
    brain_mask: np.ndarray,
) -> float:
    label_mask = (
        np.asarray(
            labels
        )
        > 0
    )

    brain = np.asarray(
        brain_mask,
        dtype=bool,
    )

    count = int(
        np.count_nonzero(
            label_mask
        )
    )

    if count == 0:
        return 0.0

    inside = int(
        np.count_nonzero(
            label_mask
            & brain
        )
    )

    return float(
        inside
        / count
    )


def evaluate_registration_quality(
    *,
    fixed_brain_mask: np.ndarray,
    registered_template_mask: np.ndarray,
    registered_labels: np.ndarray,
    config: RegistrationConfig,
) -> RegistrationQuality:
    fixed = np.asarray(
        fixed_brain_mask,
        dtype=bool,
    )

    registered = np.asarray(
        registered_template_mask,
        dtype=bool,
    )

    labels = np.asarray(
        registered_labels
    )

    if not (
        fixed.shape
        == registered.shape
        == labels.shape
    ):
        raise ValueError(
            "Registration QC arrays "
            "must share shape"
        )

    brain_dice = _dice(
        fixed,
        registered,
    )

    inside_fraction = (
        _labels_inside_fraction(
            labels,
            fixed,
        )
    )

    if (
        brain_dice
        < config
        .quality_fail_brain_dice
        or inside_fraction
        < config
        .quality_fail_inside_fraction
    ):
        status = "fail"

    elif (
        brain_dice
        < config
        .quality_warn_brain_dice
        or inside_fraction
        < config
        .quality_warn_inside_fraction
    ):
        status = "warn"

    else:
        status = "pass"

    return RegistrationQuality(
        brain_dice=(
            brain_dice
        ),
        labeled_inside_brain_fraction=(
            inside_fraction
        ),
        status=status,
    )


def _mask_centroid(
    mask: sitk.Image,
) -> tuple[
    float,
    float,
    float,
]:
    binary = sitk.Cast(
        mask > 0,
        sitk.sitkUInt8,
    )

    statistics = (
        sitk.LabelShapeStatisticsImageFilter()
    )

    statistics.Execute(
        binary
    )

    if not statistics.HasLabel(
        1
    ):
        raise ValueError(
            "Cannot compute centroid "
            "of empty mask"
        )

    centroid = (
        statistics.GetCentroid(
            1
        )
    )

    return (
        float(
            centroid[0]
        ),
        float(
            centroid[1]
        ),
        float(
            centroid[2]
        ),
    )


def _initial_rigid_transform(
    *,
    fixed_mask: sitk.Image,
    moving_mask: sitk.Image,
) -> sitk.Euler3DTransform:
    fixed_center = (
        _mask_centroid(
            fixed_mask
        )
    )

    moving_center = (
        _mask_centroid(
            moving_mask
        )
    )

    transform = (
        sitk.Euler3DTransform()
    )

    transform.SetCenter(
        fixed_center
    )

    transform.SetTranslation(
        (
            moving_center[0]
            - fixed_center[0],
            moving_center[1]
            - fixed_center[1],
            moving_center[2]
            - fixed_center[2],
        )
    )

    return transform


def _configure_metric(
    method: sitk.ImageRegistrationMethod,
    *,
    fixed_mask: sitk.Image,
    moving_mask: sitk.Image,
    config: RegistrationConfig,
) -> None:
    method.SetMetricAsMattesMutualInformation(
        config.histogram_bins
    )

    method.SetMetricSamplingStrategy(
        method.RANDOM
    )

    method.SetMetricSamplingPercentage(
        config.sampling_percentage,
        config.random_seed,
    )

    method.SetMetricFixedMask(
        fixed_mask
    )

    method.SetMetricMovingMask(
        moving_mask
    )

    method.SetInterpolator(
        sitk.sitkLinear
    )

    method.SetShrinkFactorsPerLevel(
        list(
            config.shrink_factors
        )
    )

    method.SetSmoothingSigmasPerLevel(
        list(
            config.smoothing_sigmas
        )
    )

    method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()


def _resample(
    *,
    moving: sitk.Image,
    fixed: sitk.Image,
    transform: sitk.Transform,
    interpolation: int,
    pixel_type: int,
) -> sitk.Image:
    return sitk.Resample(
        moving,
        fixed,
        transform,
        interpolation,
        0,
        pixel_type,
    )


def _quality_from_images(
    *,
    fixed_mask: sitk.Image,
    registered_mask: sitk.Image,
    registered_labels: sitk.Image,
    config: RegistrationConfig,
) -> RegistrationQuality:
    fixed_data = (
        sitk.GetArrayFromImage(
            fixed_mask
        )
        > 0
    )

    mask_data = (
        sitk.GetArrayFromImage(
            registered_mask
        )
        > 0
    )

    labels_data = (
        sitk.GetArrayFromImage(
            registered_labels
        )
    )

    return evaluate_registration_quality(
        fixed_brain_mask=(
            fixed_data
        ),
        registered_template_mask=(
            mask_data
        ),
        registered_labels=(
            labels_data
        ),
        config=config,
    )


def _run_rigid(
    *,
    fixed: sitk.Image,
    moving: sitk.Image,
    fixed_mask: sitk.Image,
    moving_mask: sitk.Image,
    initial: sitk.Euler3DTransform,
    config: RegistrationConfig,
) -> tuple[
    sitk.Euler3DTransform,
    float,
    int,
    str,
]:
    method = (
        sitk.ImageRegistrationMethod()
    )

    _configure_metric(
        method,
        fixed_mask=fixed_mask,
        moving_mask=moving_mask,
        config=config,
    )

    method.SetOptimizerAsRegularStepGradientDescent(
        config.rigid_learning_rate,
        config.rigid_min_step,
        config.rigid_iterations,
        0.5,
        1e-6,
    )

    method.SetOptimizerScalesFromPhysicalShift()

    method.SetInitialTransform(
        initial,
        inPlace=True,
    )

    method.Execute(
        fixed,
        moving,
    )

    return (
        initial,
        float(
            method.GetMetricValue()
        ),
        int(
            method
            .GetMetricNumberOfValidPoints()
        ),
        (
            method
            .GetOptimizerStopConditionDescription()
        ),
    )


def _affine_from_rigid(
    rigid: sitk.Euler3DTransform,
) -> sitk.AffineTransform:
    affine = (
        sitk.AffineTransform(
            3
        )
    )

    affine.SetCenter(
        rigid.GetCenter()
    )

    affine.SetMatrix(
        rigid.GetMatrix()
    )

    affine.SetTranslation(
        rigid.GetTranslation()
    )

    return affine


def _run_affine(
    *,
    fixed: sitk.Image,
    moving: sitk.Image,
    fixed_mask: sitk.Image,
    moving_mask: sitk.Image,
    initial: sitk.AffineTransform,
    config: RegistrationConfig,
) -> tuple[
    sitk.AffineTransform,
    float,
    int,
    str,
]:
    method = (
        sitk.ImageRegistrationMethod()
    )

    _configure_metric(
        method,
        fixed_mask=fixed_mask,
        moving_mask=moving_mask,
        config=config,
    )

    method.SetOptimizerAsRegularStepGradientDescent(
        config.affine_learning_rate,
        config.affine_min_step,
        config.affine_iterations,
        0.5,
        1e-6,
    )

    method.SetOptimizerScalesFromPhysicalShift()

    method.SetInitialTransform(
        initial,
        inPlace=True,
    )

    method.Execute(
        fixed,
        moving,
    )

    return (
        initial,
        float(
            method.GetMetricValue()
        ),
        int(
            method
            .GetMetricNumberOfValidPoints()
        ),
        (
            method
            .GetOptimizerStopConditionDescription()
        ),
    )


def _mesh_size(
    image: sitk.Image,
    *,
    spacing_mm: float,
) -> list[int]:
    size = image.GetSize()

    spacing = image.GetSpacing()

    result: list[int] = []

    for (
        voxel_count,
        voxel_spacing,
    ) in zip(
        size,
        spacing,
        strict=True,
    ):
        physical_length = (
            max(
                int(voxel_count) - 1,
                1,
            )
            * float(
                voxel_spacing
            )
        )

        cells = max(
            1,
            int(
                round(
                    physical_length
                    / spacing_mm
                )
            ),
        )

        result.append(
            cells
        )

    return result


def _run_bspline(
    *,
    fixed: sitk.Image,
    moving: sitk.Image,
    fixed_mask: sitk.Image,
    moving_mask: sitk.Image,
    config: RegistrationConfig,
) -> tuple[
    sitk.BSplineTransform,
    float,
    int,
    str,
]:
    mesh_size = (
        _mesh_size(
            fixed,
            spacing_mm=(
                config
                .bspline_control_point_spacing_mm
            ),
        )
    )

    transform = (
        sitk.BSplineTransformInitializer(
            fixed,
            mesh_size,
            order=3,
        )
    )

    method = (
        sitk.ImageRegistrationMethod()
    )

    _configure_metric(
        method,
        fixed_mask=fixed_mask,
        moving_mask=moving_mask,
        config=config,
    )

    maximum = (
        config
        .bspline_max_coefficient_mm
    )

    method.SetOptimizerAsLBFGSB(
        gradientConvergenceTolerance=(
            1e-5
        ),
        numberOfIterations=(
            config.bspline_iterations
        ),
        maximumNumberOfCorrections=5,
        maximumNumberOfFunctionEvaluations=(
            config.bspline_iterations
            * 20
        ),
        costFunctionConvergenceFactor=(
            1e7
        ),
        lowerBound=-maximum,
        upperBound=maximum,
        trace=False,
    )

    method.SetInitialTransform(
        transform,
        inPlace=True,
    )

    method.Execute(
        fixed,
        moving,
    )

    return (
        transform,
        float(
            method.GetMetricValue()
        ),
        int(
            method
            .GetMetricNumberOfValidPoints()
        ),
        (
            method
            .GetOptimizerStopConditionDescription()
        ),
    )


def _deformation_quality(
    *,
    transform: sitk.Transform,
    reference: sitk.Image,
    config: RegistrationConfig,
) -> DeformationQuality:
    converter = (
        sitk.TransformToDisplacementFieldFilter()
    )

    converter.SetReferenceImage(
        reference
    )

    converter.SetOutputPixelType(
        sitk.sitkVectorFloat64
    )

    displacement = (
        converter.Execute(
            transform
        )
    )

    displacement_data = np.asarray(
        sitk.GetArrayFromImage(
            displacement
        ),
        dtype=np.float64,
    )

    magnitudes = np.linalg.norm(
        displacement_data,
        axis=-1,
    )

    maximum_displacement = float(
        np.max(
            magnitudes
        )
    )

    jacobian_image = (
        sitk
        .DisplacementFieldJacobianDeterminant(
            displacement
        )
    )

    jacobian = np.asarray(
        sitk.GetArrayFromImage(
            jacobian_image
        ),
        dtype=np.float64,
    )

    minimum_jacobian = float(
        np.min(
            jacobian
        )
    )

    maximum_jacobian = float(
        np.max(
            jacobian
        )
    )

    nonpositive_fraction = float(
        np.mean(
            jacobian <= 0.0
        )
    )

    acceptable = (
        minimum_jacobian
        >= config
        .bspline_min_jacobian
        and maximum_jacobian
        <= config
        .bspline_max_jacobian
        and nonpositive_fraction
        <= config
        .bspline_max_nonpositive_fraction
        and maximum_displacement
        <= config
        .bspline_max_displacement_mm
    )

    return DeformationQuality(
        minimum_jacobian=(
            minimum_jacobian
        ),
        maximum_jacobian=(
            maximum_jacobian
        ),
        nonpositive_jacobian_fraction=(
            nonpositive_fraction
        ),
        maximum_displacement_mm=(
            maximum_displacement
        ),
        acceptable=(
            acceptable
        ),
    )


def _stage_payload(
    stage: OptimizationStage,
) -> dict[str, object]:
    return {
        "success": (
            stage.success
        ),
        "metric_value": (
            stage.metric_value
        ),
        "valid_metric_points": (
            stage.valid_metric_points
        ),
        "stop_condition": (
            stage.stop_condition
        ),
        "quality": (
            (
                asdict(
                    stage.quality
                )
            )
            if stage.quality
            is not None
            else None
        ),
        "deformation": (
            (
                asdict(
                    stage.deformation
                )
            )
            if stage.deformation
            is not None
            else None
        ),
        "error": (
            stage.error
        ),
    }


def _geometry_payload(
    image: sitk.Image,
) -> dict[str, object]:
    return {
        "size": [
            int(value)
            for value
            in image.GetSize()
        ],
        "spacing": [
            float(value)
            for value
            in image.GetSpacing()
        ],
        "origin": [
            float(value)
            for value
            in image.GetOrigin()
        ],
        "direction": [
            float(value)
            for value
            in image.GetDirection()
        ],
    }


def _is_linear_candidate_acceptable(
    *,
    current: RegistrationQuality,
    candidate: RegistrationQuality,
    config: RegistrationConfig,
) -> bool:
    return (
        candidate.brain_dice
        >= (
            current.brain_dice
            - config
            .linear_max_brain_dice_drop
        )
        and (
            candidate
            .labeled_inside_brain_fraction
            >= (
                current
                .labeled_inside_brain_fraction
                - config
                .linear_max_inside_fraction_drop
            )
        )
    )


def _is_deformable_candidate_acceptable(
    *,
    current: RegistrationQuality,
    candidate: RegistrationQuality,
    deformation: DeformationQuality,
    config: RegistrationConfig,
) -> bool:
    if not deformation.acceptable:
        return False

    return (
        candidate.brain_dice
        >= (
            current.brain_dice
            - config
            .deformable_max_brain_dice_drop
        )
        and (
            candidate
            .labeled_inside_brain_fraction
            >= (
                current
                .labeled_inside_brain_fraction
                - config
                .deformable_max_inside_fraction_drop
            )
        )
    )


def _write_json(
    path: Path,
    payload: dict[str, object],
) -> None:
    path.write_text(
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def register_atlas_to_patient(
    *,
    fixed_t1_path: Path,
    fixed_registration_mask_path: Path,
    atlas_template_path: Path,
    atlas_brain_mask_path: Path,
    atlas_labelmap_path: Path,
    output_dir: Path,
    patient_id: int,
    timepoint_name: str,
    config: RegistrationConfig = (
        DEFAULT_REGISTRATION_CONFIG
    ),
) -> RegistrationResult:
    _validate_config(
        config
    )

    required_paths = (
        fixed_t1_path,
        fixed_registration_mask_path,
        atlas_template_path,
        atlas_brain_mask_path,
        atlas_labelmap_path,
    )

    for path in required_paths:
        if not path.is_file():
            raise FileNotFoundError(
                "Required registration "
                f"input not found: {path}"
            )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    fixed = _read_float_image(
        fixed_t1_path
    )

    fixed_mask = (
        _read_binary_mask(
            fixed_registration_mask_path
        )
    )

    moving = _read_float_image(
        atlas_template_path
    )

    moving_mask = (
        _read_binary_mask(
            atlas_brain_mask_path
        )
    )

    atlas_labels = sitk.ReadImage(
        str(
            atlas_labelmap_path
        ),
        sitk.sitkUInt16,
    )

    initial_rigid = (
        _initial_rigid_transform(
            fixed_mask=fixed_mask,
            moving_mask=moving_mask,
        )
    )

    try:
        (
            rigid_transform,
            rigid_metric,
            rigid_points,
            rigid_stop,
        ) = _run_rigid(
            fixed=fixed,
            moving=moving,
            fixed_mask=fixed_mask,
            moving_mask=moving_mask,
            initial=initial_rigid,
            config=config,
        )

    except RuntimeError as exc:
        raise RuntimeError(
            "Rigid atlas registration "
            "failed"
        ) from exc

    rigid_template = _resample(
        moving=moving,
        fixed=fixed,
        transform=rigid_transform,
        interpolation=sitk.sitkLinear,
        pixel_type=sitk.sitkFloat32,
    )

    rigid_mask = _resample(
        moving=moving_mask,
        fixed=fixed,
        transform=rigid_transform,
        interpolation=(
            sitk.sitkNearestNeighbor
        ),
        pixel_type=sitk.sitkUInt8,
    )

    rigid_labels = _resample(
        moving=atlas_labels,
        fixed=fixed,
        transform=rigid_transform,
        interpolation=(
            sitk.sitkNearestNeighbor
        ),
        pixel_type=sitk.sitkUInt16,
    )

    rigid_quality = (
        _quality_from_images(
            fixed_mask=fixed_mask,
            registered_mask=rigid_mask,
            registered_labels=(
                rigid_labels
            ),
            config=config,
        )
    )

    rigid_stage = OptimizationStage(
        success=True,
        metric_value=(
            rigid_metric
        ),
        valid_metric_points=(
            rigid_points
        ),
        stop_condition=(
            rigid_stop
        ),
        quality=(
            rigid_quality
        ),
        deformation=None,
    )

    selected_stage = "rigid"

    selected_template = (
        rigid_template
    )

    selected_mask = (
        rigid_mask
    )

    selected_labels = (
        rigid_labels
    )

    selected_quality = (
        rigid_quality
    )

    selected_metric = (
        rigid_metric
    )

    selected_stop = (
        rigid_stop
    )

    selected_linear_transform: (
        sitk.Transform
    ) = rigid_transform

    affine_stage: OptimizationStage

    affine_transform = (
        _affine_from_rigid(
            rigid_transform
        )
    )

    try:
        (
            affine_transform,
            affine_metric,
            affine_points,
            affine_stop,
        ) = _run_affine(
            fixed=fixed,
            moving=moving,
            fixed_mask=fixed_mask,
            moving_mask=moving_mask,
            initial=affine_transform,
            config=config,
        )

        affine_template = _resample(
            moving=moving,
            fixed=fixed,
            transform=(
                affine_transform
            ),
            interpolation=(
                sitk.sitkLinear
            ),
            pixel_type=(
                sitk.sitkFloat32
            ),
        )

        affine_mask = _resample(
            moving=moving_mask,
            fixed=fixed,
            transform=(
                affine_transform
            ),
            interpolation=(
                sitk
                .sitkNearestNeighbor
            ),
            pixel_type=(
                sitk.sitkUInt8
            ),
        )

        affine_labels = _resample(
            moving=atlas_labels,
            fixed=fixed,
            transform=(
                affine_transform
            ),
            interpolation=(
                sitk
                .sitkNearestNeighbor
            ),
            pixel_type=(
                sitk.sitkUInt16
            ),
        )

        affine_quality = (
            _quality_from_images(
                fixed_mask=fixed_mask,
                registered_mask=(
                    affine_mask
                ),
                registered_labels=(
                    affine_labels
                ),
                config=config,
            )
        )

        affine_stage = (
            OptimizationStage(
                success=True,
                metric_value=(
                    affine_metric
                ),
                valid_metric_points=(
                    affine_points
                ),
                stop_condition=(
                    affine_stop
                ),
                quality=(
                    affine_quality
                ),
                deformation=None,
            )
        )

        if (
            _is_linear_candidate_acceptable(
                current=(
                    selected_quality
                ),
                candidate=(
                    affine_quality
                ),
                config=config,
            )
        ):
            selected_stage = (
                "affine"
            )

            selected_template = (
                affine_template
            )

            selected_mask = (
                affine_mask
            )

            selected_labels = (
                affine_labels
            )

            selected_quality = (
                affine_quality
            )

            selected_metric = (
                affine_metric
            )

            selected_stop = (
                affine_stop
            )

            selected_linear_transform = (
                affine_transform
            )

    except RuntimeError as exc:
        affine_stage = (
            OptimizationStage(
                success=False,
                metric_value=None,
                valid_metric_points=None,
                stop_condition=(
                    "Affine registration "
                    "raised RuntimeError"
                ),
                quality=None,
                deformation=None,
                error=str(exc),
            )
        )

    linear_transform_path = (
        output_dir
        / "linear_atlas_to_patient.tfm"
    )

    sitk.WriteTransform(
        selected_linear_transform,
        str(
            linear_transform_path
        ),
    )

    linear_template_path = (
        output_dir
        / "atlas_template_linear.nii.gz"
    )

    linear_mask_path = (
        output_dir
        / (
            "atlas_brain_mask_"
            "linear.nii.gz"
        )
    )

    linear_labels_path = (
        output_dir
        / "labels_linear.nii.gz"
    )

    sitk.WriteImage(
        selected_template,
        str(
            linear_template_path
        ),
        True,
    )

    sitk.WriteImage(
        selected_mask,
        str(
            linear_mask_path
        ),
        True,
    )

    sitk.WriteImage(
        selected_labels,
        str(
            linear_labels_path
        ),
        True,
    )

    bspline_stage = (
        OptimizationStage(
            success=False,
            metric_value=None,
            valid_metric_points=None,
            stop_condition=(
                "B-spline disabled"
            ),
            quality=None,
            deformation=None,
        )
    )

    deformable_transform_path: (
        Path | None
    ) = None

    if config.enable_bspline:
        try:
            (
                bspline_transform,
                bspline_metric,
                bspline_points,
                bspline_stop,
            ) = _run_bspline(
                fixed=fixed,
                moving=(
                    selected_template
                ),
                fixed_mask=(
                    fixed_mask
                ),
                moving_mask=(
                    selected_mask
                ),
                config=config,
            )

            deformation = (
                _deformation_quality(
                    transform=(
                        bspline_transform
                    ),
                    reference=fixed,
                    config=config,
                )
            )

            deformable_template = (
                _resample(
                    moving=(
                        selected_template
                    ),
                    fixed=fixed,
                    transform=(
                        bspline_transform
                    ),
                    interpolation=(
                        sitk.sitkLinear
                    ),
                    pixel_type=(
                        sitk.sitkFloat32
                    ),
                )
            )

            deformable_mask = (
                _resample(
                    moving=(
                        selected_mask
                    ),
                    fixed=fixed,
                    transform=(
                        bspline_transform
                    ),
                    interpolation=(
                        sitk
                        .sitkNearestNeighbor
                    ),
                    pixel_type=(
                        sitk.sitkUInt8
                    ),
                )
            )

            deformable_labels = (
                _resample(
                    moving=(
                        selected_labels
                    ),
                    fixed=fixed,
                    transform=(
                        bspline_transform
                    ),
                    interpolation=(
                        sitk
                        .sitkNearestNeighbor
                    ),
                    pixel_type=(
                        sitk.sitkUInt16
                    ),
                )
            )

            deformable_quality = (
                _quality_from_images(
                    fixed_mask=(
                        fixed_mask
                    ),
                    registered_mask=(
                        deformable_mask
                    ),
                    registered_labels=(
                        deformable_labels
                    ),
                    config=config,
                )
            )

            bspline_stage = (
                OptimizationStage(
                    success=True,
                    metric_value=(
                        bspline_metric
                    ),
                    valid_metric_points=(
                        bspline_points
                    ),
                    stop_condition=(
                        bspline_stop
                    ),
                    quality=(
                        deformable_quality
                    ),
                    deformation=(
                        deformation
                    ),
                )
            )

            deformable_transform_path = (
                output_dir
                / (
                    "deformable_"
                    "patient_grid.tfm"
                )
            )

            sitk.WriteTransform(
                bspline_transform,
                str(
                    deformable_transform_path
                ),
            )

            sitk.WriteImage(
                deformable_template,
                str(
                    output_dir
                    / (
                        "atlas_template_"
                        "deformable.nii.gz"
                    )
                ),
                True,
            )

            sitk.WriteImage(
                deformable_mask,
                str(
                    output_dir
                    / (
                        "atlas_brain_mask_"
                        "deformable.nii.gz"
                    )
                ),
                True,
            )

            sitk.WriteImage(
                deformable_labels,
                str(
                    output_dir
                    / (
                        "labels_"
                        "deformable.nii.gz"
                    )
                ),
                True,
            )

            if (
                _is_deformable_candidate_acceptable(
                    current=(
                        selected_quality
                    ),
                    candidate=(
                        deformable_quality
                    ),
                    deformation=(
                        deformation
                    ),
                    config=config,
                )
            ):
                selected_stage = (
                    f"{selected_stage}"
                    "+bspline"
                )

                selected_template = (
                    deformable_template
                )

                selected_mask = (
                    deformable_mask
                )

                selected_labels = (
                    deformable_labels
                )

                selected_quality = (
                    deformable_quality
                )

                selected_metric = (
                    bspline_metric
                )

                selected_stop = (
                    bspline_stop
                )

        except RuntimeError as exc:
            bspline_stage = (
                OptimizationStage(
                    success=False,
                    metric_value=None,
                    valid_metric_points=None,
                    stop_condition=(
                        "B-spline "
                        "registration raised "
                        "RuntimeError"
                    ),
                    quality=None,
                    deformation=None,
                    error=str(exc),
                )
            )

    registered_template_path = (
        output_dir
        / (
            "atlas_template_"
            "registered.nii.gz"
        )
    )

    registered_brain_mask_path = (
        output_dir
        / (
            "atlas_brain_mask_"
            "registered.nii.gz"
        )
    )

    candidate_labels_path = (
        output_dir
        / "labels_candidate.nii.gz"
    )

    sitk.WriteImage(
        selected_template,
        str(
            registered_template_path
        ),
        True,
    )

    sitk.WriteImage(
        selected_mask,
        str(
            registered_brain_mask_path
        ),
        True,
    )

    sitk.WriteImage(
        selected_labels,
        str(
            candidate_labels_path
        ),
        True,
    )

    provenance_path = (
        output_dir
        / "registration.json"
    )

    provenance = {
        "patient_id": (
            patient_id
        ),
        "timepoint_name": (
            timepoint_name
        ),
        "created_at_utc": (
            datetime.now(
                UTC
            ).isoformat()
        ),
        "method": (
            "registration-only mask -> "
            "centroid initialization -> "
            "rigid -> affine -> "
            "optional B-spline"
        ),
        "selected_stage": (
            selected_stage
        ),
        "quality": (
            asdict(
                selected_quality
            )
        ),
        "rigid": (
            _stage_payload(
                rigid_stage
            )
        ),
        "affine": (
            _stage_payload(
                affine_stage
            )
        ),
        "bspline": (
            _stage_payload(
                bspline_stage
            )
        ),
        "fixed_geometry": (
            _geometry_payload(
                fixed
            )
        ),
        "moving_geometry": (
            _geometry_payload(
                moving
            )
        ),
        "config": (
            asdict(
                config
            )
        ),
        "candidate_labels": (
            candidate_labels_path.name
        ),
        "manual_review_required": True,
        "accepted_labels_present": False,
    }

    _write_json(
        provenance_path,
        provenance,
    )

    if (
        selected_quality.status
        == "fail"
    ):
        raise RegistrationQualityError(
            "Registration completed, "
            "but automatic QC failed. "
            f"Stage={selected_stage}; "
            "brain Dice="
            f"{selected_quality.brain_dice:.4f}; "
            "labels inside brain="
            f"{selected_quality.labeled_inside_brain_fraction:.4f}. "
            "Candidate was preserved "
            "for diagnostics but cannot "
            "be accepted."
        )

    return RegistrationResult(
        output_dir=(
            output_dir
        ),
        candidate_labels_path=(
            candidate_labels_path
        ),
        registered_template_path=(
            registered_template_path
        ),
        registered_brain_mask_path=(
            registered_brain_mask_path
        ),
        linear_transform_path=(
            linear_transform_path
        ),
        deformable_transform_path=(
            deformable_transform_path
        ),
        provenance_path=(
            provenance_path
        ),
        selected_stage=(
            selected_stage
        ),
        metric_value=(
            selected_metric
        ),
        optimizer_stop_condition=(
            selected_stop
        ),
        quality=(
            selected_quality
        ),
    )