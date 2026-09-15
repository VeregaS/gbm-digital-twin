from __future__ import annotations

import json
from dataclasses import (
    asdict,
    dataclass,
)
from pathlib import Path

import numpy as np
import SimpleITK as sitk
from PIL import (
    Image,
    ImageDraw,
)
from scipy.ndimage import (
    binary_erosion,
)

_PATIENT_COLOR = (
    34,
    211,
    153,
)

_ATLAS_COLOR = (
    217,
    70,
    239,
)

_LABEL_COLOR = (
    34,
    211,
    238,
)

_BACKGROUND_COLOR = (
    18,
    23,
    29,
)

_TEXT_COLOR = (
    235,
    240,
    245,
)

_SECONDARY_TEXT_COLOR = (
    170,
    182,
    194,
)

_BORDER_COLOR = (
    70,
    82,
    94,
)


@dataclass(frozen=True)
class SourceQCMetrics:
    patient_brain_voxels: int

    atlas_brain_voxels: int

    atlas_label_voxels: int

    atlas_labels_inside_brain_fraction: float


@dataclass(frozen=True)
class SourceQCResult:
    patient_image_path: Path

    atlas_image_path: Path

    report_path: Path

    metrics: SourceQCMetrics


def _validate_3d(
    array: np.ndarray,
    *,
    name: str,
) -> None:
    if array.ndim != 3:
        raise ValueError(
            f"{name} must be 3D, "
            f"got shape {array.shape}"
        )


def _validate_same_shape(
    first: np.ndarray,
    second: np.ndarray,
    *,
    first_name: str,
    second_name: str,
) -> None:
    if first.shape != second.shape:
        raise ValueError(
            f"{first_name} shape "
            f"{first.shape} does not match "
            f"{second_name} shape "
            f"{second.shape}"
        )


def _to_xyz(
    image: sitk.Image,
) -> np.ndarray:
    array_zyx = (
        sitk.GetArrayFromImage(
            image
        )
    )

    return np.transpose(
        array_zyx,
        (
            2,
            1,
            0,
        ),
    )


def _resample_mask_to_reference(
    *,
    mask: sitk.Image,
    reference: sitk.Image,
) -> sitk.Image:
    identity = sitk.Transform(
        3,
        sitk.sitkIdentity,
    )

    return sitk.Resample(
        mask,
        reference,
        identity,
        sitk.sitkNearestNeighbor,
        0,
        sitk.sitkUInt8,
    )


def _resample_labels_to_reference(
    *,
    labels: sitk.Image,
    reference: sitk.Image,
) -> sitk.Image:
    identity = sitk.Transform(
        3,
        sitk.sitkIdentity,
    )

    return sitk.Resample(
        labels,
        reference,
        identity,
        sitk.sitkNearestNeighbor,
        0,
        sitk.sitkUInt16,
    )


def _load_atlas_source(
    *,
    template_path: Path,
    brain_mask_path: Path,
    labels_path: Path,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
]:
    for path in (
        template_path,
        brain_mask_path,
        labels_path,
    ):
        if not path.is_file():
            raise FileNotFoundError(
                "Required atlas source "
                f"file not found: {path}"
            )

    template = sitk.ReadImage(
        str(
            template_path
        ),
        sitk.sitkFloat32,
    )

    brain_mask = sitk.ReadImage(
        str(
            brain_mask_path
        ),
        sitk.sitkUInt8,
    )

    labels = sitk.ReadImage(
        str(
            labels_path
        ),
        sitk.sitkUInt16,
    )

    brain_mask_on_template = (
        _resample_mask_to_reference(
            mask=brain_mask,
            reference=template,
        )
    )

    labels_on_template = (
        _resample_labels_to_reference(
            labels=labels,
            reference=template,
        )
    )

    template_data = np.asarray(
        _to_xyz(
            template
        ),
        dtype=np.float32,
    )

    brain_data = np.asarray(
        _to_xyz(
            brain_mask_on_template
        ),
        dtype=np.uint8,
    )

    brain_data = (
        brain_data > 0
    )

    labels_data = np.asarray(
        _to_xyz(
            labels_on_template
        ),
        dtype=np.uint16,
    )

    return (
        template_data,
        brain_data,
        labels_data,
    )


def _normalize_mri(
    image: np.ndarray,
    brain_mask: np.ndarray,
) -> np.ndarray:
    image_float = np.asarray(
        image,
        dtype=np.float32,
    )

    mask = np.asarray(
        brain_mask,
        dtype=bool,
    )

    finite_mask = np.logical_and(
        mask,
        np.isfinite(
            image_float
        ),
    )

    values = (
        image_float[
            finite_mask
        ]
    )

    if values.size == 0:
        return np.zeros(
            image.shape,
            dtype=np.uint8,
        )

    low = float(
        np.percentile(
            values,
            1.0,
        )
    )

    high = float(
        np.percentile(
            values,
            99.0,
        )
    )

    if high <= low:
        return np.zeros(
            image.shape,
            dtype=np.uint8,
        )

    normalized = (
        (
            image_float
            - low
        )
        / (
            high
            - low
        )
    )

    normalized = np.clip(
        normalized,
        0.0,
        1.0,
    )

    return (
        normalized
        * 255.0
    ).astype(
        np.uint8
    )


def _boundary(
    mask: np.ndarray,
) -> np.ndarray:
    binary = np.asarray(
        mask,
        dtype=bool,
    )

    if not np.any(
        binary
    ):
        return np.zeros_like(
            binary,
            dtype=bool,
        )

    erosion_result = (
        binary_erosion(
            binary,
            iterations=1,
            border_value=0,
        )
    )

    eroded = np.asarray(
        erosion_result,
        dtype=bool,
    )

    return np.logical_and(
        binary,
        np.logical_not(
            eroded
        ),
    )


def _slice(
    volume: np.ndarray,
    *,
    plane: str,
    index: int,
) -> np.ndarray:
    if plane == "axial":
        result = (
            volume[
                :,
                :,
                index,
            ].T
        )

    elif plane == "coronal":
        result = (
            volume[
                :,
                index,
                :,
            ].T
        )

    elif plane == "sagittal":
        result = (
            volume[
                index,
                :,
                :,
            ].T
        )

    else:
        raise ValueError(
            "Unsupported plane: "
            f"{plane}"
        )

    return np.flipud(
        result
    )


def _slice_indices(
    mask: np.ndarray,
    *,
    axis: int,
) -> tuple[
    int,
    int,
    int,
]:
    coordinates = np.argwhere(
        mask
    )

    if coordinates.size == 0:
        raise ValueError(
            "Cannot select QC slices "
            "from an empty mask"
        )

    values = (
        coordinates[
            :,
            axis,
        ]
    )

    minimum = int(
        np.min(
            values
        )
    )

    maximum = int(
        np.max(
            values
        )
    )

    span = (
        maximum
        - minimum
    )

    return (
        int(
            round(
                minimum
                + span
                * 0.30
            )
        ),
        int(
            round(
                minimum
                + span
                * 0.50
            )
        ),
        int(
            round(
                minimum
                + span
                * 0.70
            )
        ),
    )


def _overlay(
    grayscale: np.ndarray,
    *,
    primary_boundary: np.ndarray,
    primary_color: tuple[
        int,
        int,
        int,
    ],
    labels: np.ndarray | None = None,
) -> Image.Image:
    rgb = np.stack(
        (
            grayscale,
            grayscale,
            grayscale,
        ),
        axis=-1,
    ).astype(
        np.uint8,
        copy=False,
    )

    if labels is not None:
        label_mask = (
            np.asarray(
                labels
            )
            > 0
        )

        if np.any(
            label_mask
        ):
            original = (
                rgb[
                    label_mask
                ]
                .astype(
                    np.float32
                )
            )

            label_color = np.asarray(
                _LABEL_COLOR,
                dtype=np.float32,
            )

            rgb[
                label_mask
            ] = (
                original
                * 0.82
                + label_color
                * 0.18
            ).astype(
                np.uint8
            )

            label_boundary = (
                _boundary(
                    label_mask
                )
            )

            rgb[
                label_boundary
            ] = _LABEL_COLOR

    boundary = np.asarray(
        primary_boundary,
        dtype=bool,
    )

    rgb[
        boundary
    ] = primary_color

    return Image.fromarray(
        rgb
    )


def _render_tile(
    *,
    image: np.ndarray,
    brain_mask: np.ndarray,
    plane: str,
    index: int,
    boundary_color: tuple[
        int,
        int,
        int,
    ],
    tile_size: int,
    labels: np.ndarray | None,
) -> Image.Image:
    image_slice = _slice(
        image,
        plane=plane,
        index=index,
    )

    brain_slice = np.asarray(
        _slice(
            brain_mask,
            plane=plane,
            index=index,
        ),
        dtype=bool,
    )

    if labels is None:
        labels_slice = None

    else:
        labels_slice = _slice(
            labels,
            plane=plane,
            index=index,
        )

    grayscale = (
        _normalize_mri(
            image_slice,
            brain_slice,
        )
    )

    tile = _overlay(
        grayscale,
        primary_boundary=(
            _boundary(
                brain_slice
            )
        ),
        primary_color=(
            boundary_color
        ),
        labels=(
            labels_slice
        ),
    )

    tile = tile.resize(
        (
            tile_size,
            tile_size,
        ),
        resample=(
            Image.Resampling.BILINEAR
        ),
    )

    draw = ImageDraw.Draw(
        tile
    )

    draw.rectangle(
        (
            0,
            0,
            tile_size - 1,
            tile_size - 1,
        ),
        outline=(
            _BORDER_COLOR
        ),
        width=1,
    )

    draw.rectangle(
        (
            8,
            8,
            160,
            32,
        ),
        fill=(
            0,
            0,
            0,
        ),
    )

    draw.text(
        (
            14,
            13,
        ),
        (
            f"{plane} "
            f"#{index}"
        ),
        fill=(
            255,
            255,
            255,
        ),
    )

    return tile


def _render_mosaic(
    *,
    image: np.ndarray,
    brain_mask: np.ndarray,
    output_path: Path,
    title: str,
    subtitle: str,
    boundary_color: tuple[
        int,
        int,
        int,
    ],
    labels: np.ndarray | None = None,
    tile_size: int = 320,
) -> None:
    _validate_3d(
        image,
        name="image",
    )

    _validate_3d(
        brain_mask,
        name="brain_mask",
    )

    _validate_same_shape(
        image,
        brain_mask,
        first_name="image",
        second_name="brain_mask",
    )

    if labels is not None:
        _validate_3d(
            labels,
            name="labels",
        )

        _validate_same_shape(
            image,
            labels,
            first_name="image",
            second_name="labels",
        )

    brain = np.asarray(
        brain_mask,
        dtype=bool,
    )

    axial_indices = (
        _slice_indices(
            brain,
            axis=2,
        )
    )

    coronal_indices = (
        _slice_indices(
            brain,
            axis=1,
        )
    )

    sagittal_indices = (
        _slice_indices(
            brain,
            axis=0,
        )
    )

    header_height = 82

    width = (
        tile_size
        * 3
    )

    height = (
        header_height
        + tile_size
        * 3
    )

    canvas = Image.new(
        "RGB",
        (
            width,
            height,
        ),
        _BACKGROUND_COLOR,
    )

    draw = ImageDraw.Draw(
        canvas
    )

    draw.text(
        (
            16,
            14,
        ),
        title,
        fill=(
            _TEXT_COLOR
        ),
    )

    draw.text(
        (
            16,
            42,
        ),
        subtitle,
        fill=(
            _SECONDARY_TEXT_COLOR
        ),
    )

    rows = (
        (
            "axial",
            axial_indices,
        ),
        (
            "coronal",
            coronal_indices,
        ),
        (
            "sagittal",
            sagittal_indices,
        ),
    )

    for (
        row_index,
        (
            plane,
            indices,
        ),
    ) in enumerate(
        rows
    ):
        for (
            column_index,
            index,
        ) in enumerate(
            indices
        ):
            tile = _render_tile(
                image=image,
                brain_mask=brain,
                plane=plane,
                index=index,
                boundary_color=(
                    boundary_color
                ),
                tile_size=(
                    tile_size
                ),
                labels=labels,
            )

            canvas.paste(
                tile,
                (
                    column_index
                    * tile_size,
                    header_height
                    + row_index
                    * tile_size,
                ),
            )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    canvas.save(
        output_path,
        format="PNG",
        optimize=True,
    )


def _labels_inside_brain_fraction(
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

    label_count = int(
        np.count_nonzero(
            label_mask
        )
    )

    if label_count == 0:
        return 0.0

    inside = np.logical_and(
        label_mask,
        brain,
    )

    inside_count = int(
        np.count_nonzero(
            inside
        )
    )

    return float(
        inside_count
        / label_count
    )


def render_anatomy_source_qc(
    *,
    patient_t1: np.ndarray,
    patient_brain_mask: np.ndarray,
    atlas_template_path: Path,
    atlas_brain_mask_path: Path,
    atlas_labels_path: Path,
    output_dir: Path,
    patient_id: int,
    timepoint_name: str,
    tile_size: int = 320,
) -> SourceQCResult:
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

    if tile_size < 128:
        raise ValueError(
            "tile_size must be "
            "at least 128"
        )

    patient_t1_array = np.asarray(
        patient_t1,
        dtype=np.float32,
    )

    patient_brain = (
        np.asarray(
            patient_brain_mask
        )
        > 0.5
    )

    _validate_3d(
        patient_t1_array,
        name="patient_t1",
    )

    _validate_3d(
        patient_brain,
        name="patient_brain_mask",
    )

    _validate_same_shape(
        patient_t1_array,
        patient_brain,
        first_name="patient_t1",
        second_name=(
            "patient_brain_mask"
        ),
    )

    if not np.any(
        patient_brain
    ):
        raise ValueError(
            "patient_brain_mask "
            "is empty"
        )

    (
        atlas_template,
        atlas_brain,
        atlas_labels,
    ) = _load_atlas_source(
        template_path=(
            atlas_template_path
        ),
        brain_mask_path=(
            atlas_brain_mask_path
        ),
        labels_path=(
            atlas_labels_path
        ),
    )

    if not np.any(
        atlas_brain
    ):
        raise ValueError(
            "atlas brain mask "
            "is empty"
        )

    output_dir = (
        output_dir.resolve()
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    patient_output_path = (
        output_dir
        / "patient_source_qc.png"
    )

    atlas_output_path = (
        output_dir
        / "atlas_source_qc.png"
    )

    report_path = (
        output_dir
        / "source_qc.json"
    )

    _render_mosaic(
        image=(
            patient_t1_array
        ),
        brain_mask=(
            patient_brain
        ),
        output_path=(
            patient_output_path
        ),
        title=(
            f"Patient {patient_id} / "
            f"{normalized_timepoint} "
            "source QC"
        ),
        subtitle=(
            "green = patient brain mask"
        ),
        boundary_color=(
            _PATIENT_COLOR
        ),
        tile_size=(
            tile_size
        ),
    )

    _render_mosaic(
        image=(
            atlas_template
        ),
        brain_mask=(
            atlas_brain
        ),
        labels=(
            atlas_labels
        ),
        output_path=(
            atlas_output_path
        ),
        title=(
            "Atlas source QC"
        ),
        subtitle=(
            "magenta = MNI brain mask | "
            "cyan = Harvard-Oxford "
            "label support"
        ),
        boundary_color=(
            _ATLAS_COLOR
        ),
        tile_size=(
            tile_size
        ),
    )

    metrics = SourceQCMetrics(
        patient_brain_voxels=int(
            np.count_nonzero(
                patient_brain
            )
        ),
        atlas_brain_voxels=int(
            np.count_nonzero(
                atlas_brain
            )
        ),
        atlas_label_voxels=int(
            np.count_nonzero(
                atlas_labels > 0
            )
        ),
        atlas_labels_inside_brain_fraction=(
            _labels_inside_brain_fraction(
                atlas_labels,
                atlas_brain,
            )
        ),
    )

    report = {
        "patient_id": (
            patient_id
        ),
        "timepoint_name": (
            normalized_timepoint
        ),
        "patient_shape": list(
            patient_t1_array.shape
        ),
        "atlas_template_shape": list(
            atlas_template.shape
        ),
        "metrics": (
            asdict(
                metrics
            )
        ),
        "patient_image": (
            patient_output_path.name
        ),
        "atlas_image": (
            atlas_output_path.name
        ),
    }

    report_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return SourceQCResult(
        patient_image_path=(
            patient_output_path
        ),
        atlas_image_path=(
            atlas_output_path
        ),
        report_path=(
            report_path
        ),
        metrics=metrics,
    )