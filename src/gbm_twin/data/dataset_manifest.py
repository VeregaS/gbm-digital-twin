from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

import yaml


@dataclass(frozen=True)
class CFBDatasetManifest:
    name: str
    version: int
    updated: str
    doi: str
    source: str
    license: str
    expected_subjects: int
    metadata_patterns: tuple[str, ...]
    required_timepoints: tuple[str, ...]
    required_modalities: tuple[str, ...]
    required_patient_files: tuple[str, ...]

    def __post_init__(self) -> None:
        text_fields = {
            "name": self.name,
            "updated": self.updated,
            "doi": self.doi,
            "source": self.source,
            "license": self.license,
        }

        for field_name, value in text_fields.items():
            if not value.strip():
                raise ValueError(
                    f"{field_name} must not be empty"
                )

        if self.version < 1:
            raise ValueError(
                "version must be positive"
            )

        if self.expected_subjects < 1:
            raise ValueError(
                "expected_subjects must be positive"
            )

        for field_name, values in (
            ("metadata_patterns", self.metadata_patterns),
            ("required_timepoints", self.required_timepoints),
            ("required_modalities", self.required_modalities),
            ("required_patient_files", self.required_patient_files),
        ):
            if not values:
                raise ValueError(
                    f"{field_name} must not be empty"
                )

            if any(
                not value.strip()
                for value in values
            ):
                raise ValueError(
                    f"{field_name} must contain non-empty strings"
                )

            if len(set(values)) != len(values):
                raise ValueError(
                    f"{field_name} must not contain duplicates"
                )

        for template in self.required_patient_files:
            if "{patient_id}" not in template:
                raise ValueError(
                    "required_patient_files templates must contain "
                    "{patient_id}"
                )

            if "{timepoint}" not in template:
                raise ValueError(
                    "required_patient_files templates must contain "
                    "{timepoint}"
                )


def _mapping(
    value: object,
    *,
    name: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(
            f"{name} must be a mapping"
        )

    return cast(
        dict[str, object],
        value,
    )


def _string(
    mapping: dict[str, object],
    key: str,
) -> str:
    value = mapping.get(key)

    if not isinstance(value, str):
        raise ValueError(
            f"{key} must be a string"
        )

    normalized = value.strip()

    if not normalized:
        raise ValueError(
            f"{key} must not be empty"
        )

    return normalized


def _positive_int(
    mapping: dict[str, object],
    key: str,
) -> int:
    value = mapping.get(key)

    if type(value) is not int or value < 1:
        raise ValueError(
            f"{key} must be a positive integer"
        )

    return value


def _string_tuple(
    mapping: dict[str, object],
    key: str,
) -> tuple[str, ...]:
    value = mapping.get(key)

    if not isinstance(value, list):
        raise ValueError(
            f"{key} must be a list"
        )

    result: list[str] = []

    for item in value:
        if not isinstance(item, str):
            raise ValueError(
                f"{key} must contain strings"
            )

        normalized = item.strip()

        if not normalized:
            raise ValueError(
                f"{key} must contain non-empty strings"
            )

        result.append(
            normalized
        )

    return tuple(
        result
    )


def load_cfb_dataset_manifest(
    path: Path,
) -> CFBDatasetManifest:
    if not path.is_file():
        raise FileNotFoundError(
            path
        )

    raw: object = yaml.safe_load(
        path.read_text(
            encoding="utf-8"
        )
    )

    root = _mapping(
        raw,
        name="dataset manifest",
    )

    dataset = _mapping(
        root.get("dataset"),
        name="dataset",
    )

    contract = _mapping(
        root.get("contract"),
        name="contract",
    )

    return CFBDatasetManifest(
        name=_string(
            dataset,
            "name",
        ),
        version=_positive_int(
            dataset,
            "version",
        ),
        updated=_string(
            dataset,
            "updated",
        ),
        doi=_string(
            dataset,
            "doi",
        ),
        source=_string(
            dataset,
            "source",
        ),
        license=_string(
            dataset,
            "license",
        ),
        expected_subjects=_positive_int(
            dataset,
            "expected_subjects",
        ),
        metadata_patterns=_string_tuple(
            contract,
            "metadata_patterns",
        ),
        required_timepoints=_string_tuple(
            contract,
            "required_timepoints",
        ),
        required_modalities=_string_tuple(
            contract,
            "required_modalities",
        ),
        required_patient_files=_string_tuple(
            contract,
            "required_patient_files",
        ),
    )
