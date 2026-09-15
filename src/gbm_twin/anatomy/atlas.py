from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import nibabel as nib
import numpy as np
from nibabel.nifti1 import Nifti1Image

from gbm_twin.anatomy.models import (
    AtlasRegionDefinition,
)


@dataclass(frozen=True)
class LoadedRegisteredAtlas:
    name: str

    labelmap: np.ndarray

    regions: tuple[
        AtlasRegionDefinition,
        ...,
    ]

    source_path: Path


def _load_region_definitions(
    manifest_path: Path,
) -> tuple[
    str,
    tuple[
        AtlasRegionDefinition,
        ...,
    ],
]:
    payload = json.loads(
        manifest_path.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(
        payload,
        dict,
    ):
        raise ValueError(
            "Atlas manifest root "
            "must be an object"
        )

    atlas_name = str(
        payload.get(
            "atlas_name",
            "Unnamed research atlas",
        )
    ).strip()

    if not atlas_name:
        atlas_name = (
            "Unnamed research atlas"
        )

    raw_regions = payload.get(
        "regions"
    )

    if not isinstance(
        raw_regions,
        list,
    ):
        raise ValueError(
            "Atlas manifest must contain "
            "a 'regions' list"
        )

    regions: list[
        AtlasRegionDefinition
    ] = []

    labels_seen: set[int] = set()

    for item in raw_regions:
        if not isinstance(
            item,
            dict,
        ):
            raise ValueError(
                "Each atlas region must "
                "be an object"
            )

        if "label" not in item:
            raise ValueError(
                "Atlas region is missing "
                "'label'"
            )

        if "name" not in item:
            raise ValueError(
                "Atlas region is missing "
                "'name'"
            )

        if "category" not in item:
            raise ValueError(
                "Atlas region is missing "
                "'category'"
            )

        label_value = item[
            "label"
        ]

        if not isinstance(
            label_value,
            (int, float, str),
        ):
            raise ValueError(
                "Atlas region label must "
                "be integer-like"
            )

        label = int(
            label_value
        )

        if label <= 0:
            raise ValueError(
                "Atlas region labels "
                "must be positive"
            )

        if label in labels_seen:
            raise ValueError(
                f"Duplicate atlas label: "
                f"{label}"
            )

        labels_seen.add(
            label
        )

        name = str(
            item["name"]
        ).strip()

        category = str(
            item["category"]
        ).strip()

        if not name:
            raise ValueError(
                "Atlas region name "
                "cannot be empty"
            )

        if not category:
            raise ValueError(
                "Atlas region category "
                "cannot be empty"
            )

        laterality_value = (
            item.get(
                "laterality"
            )
        )

        functional_note_value = (
            item.get(
                "functional_note"
            )
        )

        if laterality_value is None:
            laterality = None
        else:
            laterality_text = str(
                laterality_value
            ).strip()

            laterality = (
                laterality_text
                if laterality_text
                else None
            )

        if functional_note_value is None:
            functional_note = None
        else:
            functional_note_text = str(
                functional_note_value
            ).strip()

            functional_note = (
                functional_note_text
                if functional_note_text
                else None
            )

        regions.append(
            AtlasRegionDefinition(
                label=label,
                name=name,
                category=category,
                laterality=laterality,
                functional_note=(
                    functional_note
                ),
            )
        )

    return (
        atlas_name,
        tuple(
            regions
        ),
    )


def registered_labelmap_path(
    atlas_root: Path,
    *,
    patient_id: int,
    timepoint_name: str,
) -> Path:
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

    return (
        atlas_root
        / "patients"
        / str(
            patient_id
        )
        / normalized_timepoint
        / "labels.nii.gz"
    )


def load_registered_atlas(
    atlas_root: Path,
    *,
    patient_id: int,
    timepoint_name: str,
    expected_shape: tuple[
        int,
        int,
        int,
    ],
    expected_affine: np.ndarray,
) -> LoadedRegisteredAtlas:
    manifest_path = (
        atlas_root
        / "manifest.json"
    )

    if not manifest_path.is_file():
        raise FileNotFoundError(
            "Atlas manifest not found: "
            f"{manifest_path}"
        )

    labelmap_path = (
        registered_labelmap_path(
            atlas_root,
            patient_id=patient_id,
            timepoint_name=(
                timepoint_name
            ),
        )
    )

    if not labelmap_path.is_file():
        raise FileNotFoundError(
            "Registered atlas labelmap "
            "not found: "
            f"{labelmap_path}"
        )

    (
        atlas_name,
        regions,
    ) = _load_region_definitions(
        manifest_path
    )

    image = cast(
        Nifti1Image,
        nib.load(
            str(
                labelmap_path
            )
        ),
    )

    raw = np.asarray(
        image.dataobj,
    )

    if raw.ndim != 3:
        raise ValueError(
            "Registered atlas labelmap "
            "must be 3D"
        )

    actual_shape = tuple(
        int(value)
        for value in raw.shape
    )

    if (
        actual_shape
        != expected_shape
    ):
        raise ValueError(
            "Registered atlas shape "
            f"{actual_shape} does not match "
            "patient grid "
            f"{expected_shape}"
        )

    atlas_affine = np.asarray(
        image.affine,
        dtype=np.float64,
    )

    patient_affine = np.asarray(
        expected_affine,
        dtype=np.float64,
    )

    if atlas_affine.shape != (
        4,
        4,
    ):
        raise ValueError(
            "Registered atlas affine "
            "must have shape (4, 4)"
        )

    if patient_affine.shape != (
        4,
        4,
    ):
        raise ValueError(
            "Expected patient affine "
            "must have shape (4, 4)"
        )

    if not np.allclose(
        atlas_affine,
        patient_affine,
        rtol=0.0,
        atol=1e-3,
    ):
        raise ValueError(
            "Registered atlas affine "
            "does not match patient grid. "
            "Atlas analysis requires a "
            "patient-space labelmap."
        )

    if not np.all(
        np.isfinite(
            raw
        )
    ):
        raise ValueError(
            "Atlas labelmap contains "
            "non-finite values"
        )

    rounded = np.rint(
        raw
    )

    if not np.allclose(
        raw,
        rounded,
        rtol=0.0,
        atol=1e-5,
    ):
        raise ValueError(
            "Atlas labelmap contains "
            "non-integer labels"
        )

    if np.any(
        rounded < 0
    ):
        raise ValueError(
            "Atlas labelmap contains "
            "negative labels"
        )

    labelmap = rounded.astype(
        np.int32,
        copy=False,
    )

    return LoadedRegisteredAtlas(
        name=atlas_name,
        labelmap=labelmap,
        regions=regions,
        source_path=(
            labelmap_path
        ),
    )