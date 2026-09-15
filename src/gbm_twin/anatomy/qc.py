from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import (
    Image,
    ImageDraw,
)
from scipy.ndimage import (
    binary_erosion,
)


@dataclass(frozen=True)
class RegistrationQCResult:
    output_path: Path

    axial_indices: tuple[
        int,
        int,
        int,
    ]

    coronal_indices: tuple[
        int,
        int,
        int,
    ]

    sagittal_indices: tuple[
        int,
        int,
        int,
    ]

    brain_dice: float

    labeled_inside_brain_fraction: float


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
    arrays: tuple[
        np.ndarray,
        ...,
    ],
) -> None:
    shapes = {
        array.shape
        for array in arrays
    }

    if len(shapes) != 1:
        raise ValueError(
            "All registration QC "
            "volumes must share shape, "
            f"got {sorted(shapes)}"
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

    denominator = (
        int(
            np.count_nonzero(
                first_mask
            )
        )
        + int(
            np.count_nonzero(
                second_mask
            )
        )
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


def _label_inside_fraction(
    labels: np.ndarray,
    brain_mask: np.ndarray,
) -> float:
    labeled = (
        np.asarray(
            labels
        )
        > 0
    )

    brain = np.asarray(
        brain_mask,
        dtype=bool,
    )

    total = int(
        np.count_nonzero(
            labeled
        )
    )

    if total == 0:
        return 0.0

    inside = int(
        np.count_nonzero(
            labeled
            & brain
        )
    )

    return float(
        inside
        / total
    )


def _mask_extent_indices(
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
            "Cannot choose QC slices "
            "from an empty brain mask"
        )

    axis_values = (
        coordinates[
            :,
            axis,
        ]
    )

    minimum = int(
        np.min(
            axis_values
        )
    )

    maximum = int(
        np.max(
            axis_values
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
                + span * 0.35
            )
        ),
        int(
            round(
                minimum
                + span * 0.50
            )
        ),
        int(
            round(
                minimum
                + span * 0.65
            )
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
            f"Unknown plane: {plane}"
        )

    return np.flipud(
        result
    )


def _normalize_mri(
    image: np.ndarray,
    mask: np.ndarray,
) -> np.ndarray:
    finite = (
        np.isfinite(
            image
        )
        & mask
    )

    values = (
        image[
            finite
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
            np.asarray(
                image,
                dtype=np.float32,
            )
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
            binary
        )

    eroded = binary_erosion(
        binary,
        iterations=1,
        border_value=0,
    )

    return (
        binary
        & ~eroded
    )


def _overlay_pixels(
    base: np.ndarray,
    *,
    patient_boundary: np.ndarray,
    atlas_boundary: np.ndarray,
    labels: np.ndarray,
) -> Image.Image:
    rgb = np.stack(
        (
            base,
            base,
            base,
        ),
        axis=-1,
    )

    rgb = np.asarray(
        rgb,
        dtype=np.uint8,
    )

    labeled = (
        labels > 0
    )

    if np.any(
        labeled
    ):
        original = (
            rgb[
                labeled
            ]
            .astype(
                np.float32
            )
        )

        overlay = np.array(
            [
                46.0,
                170.0,
                190.0,
            ],
            dtype=np.float32,
        )

        rgb[
            labeled
        ] = (
            original
            * 0.72
            + overlay
            * 0.28
        ).astype(
            np.uint8
        )

    rgb[
        atlas_boundary
    ] = (
        217,
        70,
        239,
    )

    rgb[
        patient_boundary
    ] = (
        34,
        211,
        153,
    )

    return Image.fromarray(
        rgb,
        mode="RGB",
    )


def _render_tile(
    *,
    t1: np.ndarray,
    patient_brain: np.ndarray,
    atlas_brain: np.ndarray,
    labels: np.ndarray,
    plane: str,
    index: int,
    tile_size: int,
) -> Image.Image:
    t1_slice = _slice(
        t1,
        plane=plane,
        index=index,
    )

    patient_slice = (
        _slice(
            patient_brain,
            plane=plane,
            index=index,
        )
        > 0
    )

    atlas_slice = (
        _slice(
            atlas_brain,
            plane=plane,
            index=index,
        )
        > 0
    )

    label_slice = _slice(
        labels,
        plane=plane,
        index=index,
    )

    gray = _normalize_mri(
        t1_slice,
        patient_slice,
    )

    image = _overlay_pixels(
        gray,
        patient_boundary=(
            _boundary(
                patient_slice
            )
        ),
        atlas_boundary=(
            _boundary(
                atlas_slice
            )
        ),
        labels=label_slice,
    )

    image = image.resize(
        (
            tile_size,
            tile_size,
        ),
        resample=(
            Image.Resampling.BILINEAR
        ),
    )

    draw = ImageDraw.Draw(
        image
    )

    draw.rectangle(
        (
            0,
            0,
            tile_size - 1,
            tile_size - 1,
        ),
        outline=(
            80,
            90,
            100,
        ),
        width=1,
    )

    draw.rectangle(
        (
            8,
            8,
            155,
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
        f"{plane}  #{index}",
        fill=(
            255,
            255,
            255,
        ),
    )

    return image


def render_registration_qc_png(
    *,
    patient_t1: np.ndarray,
    patient_brain_mask: np.ndarray,
    registered_atlas_brain_mask: np.ndarray,
    registered_labels: np.ndarray,
    output_path: Path,
    patient_id: int,
    timepoint_name: str,
    tile_size: int = 320,
) -> RegistrationQCResult:
    patient_t1 = np.asarray(
        patient_t1,
        dtype=np.float32,
    )

    patient_brain = (
        np.asarray(
            patient_brain_mask
        )
        > 0.5
    )

    atlas_brain = (
        np.asarray(
            registered_atlas_brain_mask
        )
        > 0.5
    )

    labels = np.asarray(
        registered_labels
    )

    for (
        name,
        volume,
    ) in (
        (
            "patient_t1",
            patient_t1,
        ),
        (
            "patient_brain_mask",
            patient_brain,
        ),
        (
            (
                "registered_"
                "atlas_brain_mask"
            ),
            atlas_brain,
        ),
        (
            "registered_labels",
            labels,
        ),
    ):
        _validate_3d(
            volume,
            name=name,
        )

    _validate_same_shape(
        (
            patient_t1,
            patient_brain,
            atlas_brain,
            labels,
        )
    )

    axial_indices = (
        _mask_extent_indices(
            patient_brain,
            axis=2,
        )
    )

    coronal_indices = (
        _mask_extent_indices(
            patient_brain,
            axis=1,
        )
    )

    sagittal_indices = (
        _mask_extent_indices(
            patient_brain,
            axis=0,
        )
    )

    canvas_width = (
        tile_size
        * 3
    )

    header_height = 94

    canvas_height = (
        header_height
        + tile_size
        * 3
    )

    canvas = Image.new(
        "RGB",
        (
            canvas_width,
            canvas_height,
        ),
        (
            18,
            23,
            29,
        ),
    )

    draw = ImageDraw.Draw(
        canvas
    )

    brain_dice = _dice(
        patient_brain,
        atlas_brain,
    )

    inside_fraction = (
        _label_inside_fraction(
            labels,
            patient_brain,
        )
    )

    draw.text(
        (
            16,
            12,
        ),
        (
            f"Patient {patient_id} / "
            f"{timepoint_name} "
            "— atlas registration QC"
        ),
        fill=(
            255,
            255,
            255,
        ),
    )

    draw.text(
        (
            16,
            36,
        ),
        (
            "green = patient brain | "
            "magenta = registered atlas brain | "
            "cyan = atlas labels"
        ),
        fill=(
            190,
            200,
            210,
        ),
    )

    draw.text(
        (
            16,
            60,
        ),
        (
            f"brain Dice = "
            f"{brain_dice:.4f} | "
            "labels inside brain = "
            f"{inside_fraction:.4f}"
        ),
        fill=(
            190,
            200,
            210,
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
            slice_index,
        ) in enumerate(
            indices
        ):
            tile = _render_tile(
                t1=patient_t1,
                patient_brain=(
                    patient_brain
                ),
                atlas_brain=(
                    atlas_brain
                ),
                labels=labels,
                plane=plane,
                index=(
                    slice_index
                ),
                tile_size=(
                    tile_size
                ),
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

    output_path = (
        output_path.resolve()
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

    return RegistrationQCResult(
        output_path=(
            output_path
        ),
        axial_indices=(
            axial_indices
        ),
        coronal_indices=(
            coronal_indices
        ),
        sagittal_indices=(
            sagittal_indices
        ),
        brain_dice=(
            brain_dice
        ),
        labeled_inside_brain_fraction=(
            inside_fraction
        ),
    )