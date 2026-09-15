from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    TypedDict,
    cast,
)

import nibabel as nib
import numpy as np
from nibabel.nifti1 import Nifti1Image
from nilearn.datasets import (
    fetch_atlas_harvard_oxford,
)
from templateflow import TemplateFlowClient

TEMPLATE_SPACE = "MNI152NLin6Asym"

CORTICAL_ATLAS = (
    "cort-maxprob-thr25-1mm"
)

SUBCORTICAL_ATLAS = (
    "sub-maxprob-thr25-1mm"
)


_TEMPLATEFLOW_CLIENT = (
    TemplateFlowClient()
)


class ManifestRegion(
    TypedDict,
):
    label_value: int
    name: str
    category: str
    laterality: str | None
    functional_note: str


@dataclass(frozen=True)
class AtlasBootstrapResult:
    atlas_root: Path

    template_path: Path

    brain_mask_path: Path

    labelmap_path: Path

    manifest_path: Path

    region_count: int


def classify_functional_region(
    name: str,
) -> tuple[str, str] | None:
    normalized = (
        name.strip().lower()
    )

    groups: tuple[
        tuple[
            str,
            tuple[str, ...],
            str,
        ],
        ...,
    ] = (
        (
            "language-associated",
            (
                "inferior frontal gyrus",
                "frontal operculum",
                "superior temporal gyrus",
                "middle temporal gyrus",
                "supramarginal gyrus",
                "angular gyrus",
                "planum temporale",
            ),
            (
                "Population-atlas region "
                "associated with language "
                "processing. This is not "
                "patient-specific functional "
                "mapping."
            ),
        ),
        (
            "motor-associated",
            (
                "precentral gyrus",
                "supplementary motor cortex",
            ),
            (
                "Population-atlas region "
                "associated with motor "
                "function."
            ),
        ),
        (
            "somatosensory-associated",
            (
                "postcentral gyrus",
                "parietal operculum cortex",
            ),
            (
                "Population-atlas region "
                "associated with "
                "somatosensory function."
            ),
        ),
        (
            "visual-associated",
            (
                "intracalcarine cortex",
                "cuneal cortex",
                "lingual gyrus",
                "occipital pole",
                "lateral occipital cortex",
            ),
            (
                "Population-atlas region "
                "associated with visual "
                "processing."
            ),
        ),
        (
            "memory-associated",
            (
                "hippocampus",
            ),
            (
                "Population-atlas structure "
                "associated with memory."
            ),
        ),
        (
            "critical-subcortical",
            (
                "thalamus",
                "caudate",
                "putamen",
                "pallidum",
                "brain-stem",
                "brain stem",
                "brainstem",
            ),
            (
                "Atlas-defined deep or "
                "subcortical structure."
            ),
        ),
    )

    for (
        category,
        keywords,
        note,
    ) in groups:
        if any(
            keyword in normalized
            for keyword in keywords
        ):
            return (
                category,
                note,
            )

    return None


def _laterality(
    name: str,
) -> str | None:
    normalized = (
        name.strip().lower()
    )

    if (
        normalized.startswith(
            "left "
        )
        or " left " in normalized
        or normalized.endswith(
            " left"
        )
    ):
        return "left"

    if (
        normalized.startswith(
            "right "
        )
        or " right " in normalized
        or normalized.endswith(
            " right"
        )
    ):
        return "right"

    return None


def _atlas_image(
    dataset: Any,
) -> Nifti1Image:
    maps = getattr(
        dataset,
        "maps",
        None,
    )

    if maps is None:
        maps = getattr(
            dataset,
            "filename",
            None,
        )

    if maps is None:
        raise RuntimeError(
            "Nilearn atlas result "
            "contains neither "
            "'maps' nor 'filename'"
        )

    if isinstance(
        maps,
        Nifti1Image,
    ):
        return maps

    loaded = nib.load(
        str(maps)
    )

    return cast(
        Nifti1Image,
        loaded,
    )


def _atlas_labels(
    dataset: Any,
) -> tuple[str, ...]:
    raw_labels = getattr(
        dataset,
        "labels",
        None,
    )

    if raw_labels is None:
        raise RuntimeError(
            "Nilearn atlas result "
            "contains no labels"
        )

    return tuple(
        str(label)
        for label in raw_labels
    )


def _template_resource_path(
    *,
    desc: str,
    suffix: str,
) -> Path:
    result = (
        _TEMPLATEFLOW_CLIENT.get(
            TEMPLATE_SPACE,
            resolution=1,
            desc=desc,
            suffix=suffix,
            extension=".nii.gz",
            raise_empty=True,
        )
    )

    if isinstance(
        result,
        Path,
    ):
        candidates = (
            result.resolve(),
        )

    else:
        candidates = tuple(
            Path(
                str(value)
            ).resolve()
            for value in result
        )

    existing = tuple(
        path
        for path in candidates
        if (
            path.is_file()
            and path.stat().st_size > 0
        )
    )

    if len(existing) != 1:
        raise RuntimeError(
            "Expected exactly one "
            "TemplateFlow resource for "
            f"space={TEMPLATE_SPACE}, "
            f"desc={desc}, "
            f"suffix={suffix}; "
            f"got {existing}"
        )

    return existing[0]


def _validate_labelmap(
    data: np.ndarray,
    *,
    name: str,
) -> None:
    if data.ndim != 3:
        raise RuntimeError(
            f"{name} atlas must be "
            f"3D, got {data.shape}"
        )

    if not np.all(
        np.isfinite(
            data
        )
    ):
        raise RuntimeError(
            f"{name} atlas contains "
            "non-finite values"
        )

    if np.any(
        data < 0
    ):
        raise RuntimeError(
            f"{name} atlas contains "
            "negative labels"
        )


def _region_entries(
    labels: tuple[str, ...],
    *,
    label_offset: int,
) -> list[
    ManifestRegion
]:
    result: list[
        ManifestRegion
    ] = []

    for (
        atlas_label,
        name,
    ) in enumerate(
        labels
    ):
        if atlas_label == 0:
            continue

        classification = (
            classify_functional_region(
                name
            )
        )

        if classification is None:
            continue

        (
            category,
            functional_note,
        ) = classification

        result.append(
            {
                "label_value": (
                    atlas_label
                    + label_offset
                ),
                "name": name,
                "category": category,
                "laterality": (
                    _laterality(
                        name
                    )
                ),
                "functional_note": (
                    functional_note
                ),
            }
        )

    return result


def _load_integer_labelmap(
    image: Nifti1Image,
    *,
    name: str,
) -> np.ndarray:
    raw = np.asarray(
        image.dataobj
    )

    _validate_labelmap(
        raw,
        name=name,
    )

    rounded = np.rint(
        raw
    )

    if not np.allclose(
        raw,
        rounded,
        rtol=0.0,
        atol=1e-6,
    ):
        raise RuntimeError(
            f"{name} atlas contains "
            "non-integer labels"
        )

    return rounded.astype(
        np.int32,
        copy=False,
    )


def _validate_matching_geometry(
    first: Nifti1Image,
    second: Nifti1Image,
) -> None:
    if first.shape != second.shape:
        raise RuntimeError(
            "Harvard-Oxford cortical "
            "and subcortical atlas "
            "shapes differ: "
            f"{first.shape} vs "
            f"{second.shape}"
        )

    first_affine = np.asarray(
        first.affine,
        dtype=np.float64,
    )

    second_affine = np.asarray(
        second.affine,
        dtype=np.float64,
    )

    if not np.allclose(
        first_affine,
        second_affine,
        rtol=0.0,
        atol=1e-5,
    ):
        raise RuntimeError(
            "Harvard-Oxford cortical "
            "and subcortical atlas "
            "affines differ"
        )


def bootstrap_harvard_oxford_atlas(
    output_root: Path,
    *,
    overwrite: bool = False,
) -> AtlasBootstrapResult:
    output_root = (
        output_root.resolve()
    )

    if output_root.exists():
        has_contents = any(
            output_root.iterdir()
        )

        if has_contents:
            if not overwrite:
                raise FileExistsError(
                    "Atlas output directory "
                    "is not empty: "
                    f"{output_root}"
                )

            shutil.rmtree(
                output_root
            )

    output_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    cortical_dataset = (
        fetch_atlas_harvard_oxford(
            CORTICAL_ATLAS,
            symmetric_split=True,
            verbose=1,
        )
    )

    subcortical_dataset = (
        fetch_atlas_harvard_oxford(
            SUBCORTICAL_ATLAS,
            symmetric_split=True,
            verbose=1,
        )
    )

    cortical_image = (
        _atlas_image(
            cortical_dataset
        )
    )

    subcortical_image = (
        _atlas_image(
            subcortical_dataset
        )
    )

    _validate_matching_geometry(
        cortical_image,
        subcortical_image,
    )

    cortical_data = (
        _load_integer_labelmap(
            cortical_image,
            name="Cortical",
        )
    )

    subcortical_data = (
        _load_integer_labelmap(
            subcortical_image,
            name="Subcortical",
        )
    )

    cortical_offset = int(
        np.max(
            cortical_data
        )
    )

    merged = (
        cortical_data.copy()
    )

    subcortical_mask = (
        subcortical_data > 0
    )

    merged[
        subcortical_mask
    ] = (
        subcortical_data[
            subcortical_mask
        ]
        + cortical_offset
    )

    labelmap_path = (
        output_root
        / "template_labels.nii.gz"
    )

    nib.save(
        nib.Nifti1Image(
            merged.astype(
                np.int16,
                copy=False,
            ),
            np.asarray(
                cortical_image.affine,
                dtype=np.float64,
            ),
        ),
        str(
            labelmap_path
        ),
    )

    source_template = (
        _template_resource_path(
            desc="brain",
            suffix="T1w",
        )
    )

    source_brain_mask = (
        _template_resource_path(
            desc="brain",
            suffix="mask",
        )
    )

    template_path = (
        output_root
        / "template_t1.nii.gz"
    )

    brain_mask_path = (
        output_root
        / "template_brain_mask.nii.gz"
    )

    shutil.copy2(
        source_template,
        template_path,
    )

    shutil.copy2(
        source_brain_mask,
        brain_mask_path,
    )

    cortical_regions = (
        _region_entries(
            _atlas_labels(
                cortical_dataset
            ),
            label_offset=0,
        )
    )

    subcortical_regions = (
        _region_entries(
            _atlas_labels(
                subcortical_dataset
            ),
            label_offset=(
                cortical_offset
            ),
        )
    )

    regions = (
        cortical_regions
        + subcortical_regions
    )

    regions.sort(
        key=lambda region: (
            region["label_value"]
        )
    )

    manifest = {
        "atlas_name": (
            "Harvard-Oxford "
            "functional-risk subset"
        ),
        "template_space": (
            TEMPLATE_SPACE
        ),
        "template_file": (
            template_path.name
        ),
        "template_brain_mask_file": (
            brain_mask_path.name
        ),
        "template_labelmap_file": (
            labelmap_path.name
        ),
        "interpretation": (
            "Research-only "
            "population-derived atlas. "
            "Anatomical overlap does not "
            "establish patient-specific "
            "functional localization."
        ),
        "regions": regions,
    }

    manifest_path = (
        output_root
        / "manifest.json"
    )

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return AtlasBootstrapResult(
        atlas_root=(
            output_root
        ),
        template_path=(
            template_path
        ),
        brain_mask_path=(
            brain_mask_path
        ),
        labelmap_path=(
            labelmap_path
        ),
        manifest_path=(
            manifest_path
        ),
        region_count=len(
            regions
        ),
    )