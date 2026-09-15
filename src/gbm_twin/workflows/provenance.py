from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from gbm_twin.data.dataset_manifest import CFBDatasetManifest
from gbm_twin.workflows.calibration import V2CalibrationConfig
from gbm_twin.workflows.patients import PreparedPatientTimepoint

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_COMMIT_PATTERN = re.compile(
    r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$"
)


class InputFileProvenancePayload(TypedDict):
    logical_name: str
    filename: str
    sha256: str


class PredictionProvenancePayload(TypedDict):
    dataset_name: str
    dataset_version: int
    dataset_doi: str
    git_commit_sha: str
    git_dirty: bool
    config_sha256: str
    inputs: list[InputFileProvenancePayload]


class V2CalibrationConfigPayload(TypedDict):
    diffusion_values: list[float]
    proliferation_values: list[float]
    dt_days: float
    latent_width_mm: float
    observation_threshold: float
    soft_temperature: float
    volume_weight: float


@dataclass(frozen=True)
class InputFileProvenance:
    logical_name: str
    filename: str
    sha256: str

    def __post_init__(self) -> None:
        logical_name = self.logical_name.strip()
        filename = self.filename.strip()

        if not logical_name:
            raise ValueError(
                "Input provenance logical name must not be empty"
            )

        if not filename:
            raise ValueError(
                "Input provenance filename must not be empty"
            )

        if Path(filename).name != filename:
            raise ValueError(
                "Input provenance must contain a filename, not a path"
            )

        if _SHA256_PATTERN.fullmatch(self.sha256) is None:
            raise ValueError(
                "Input provenance SHA-256 must be 64 lowercase hex characters"
            )

        object.__setattr__(
            self,
            "logical_name",
            logical_name,
        )
        object.__setattr__(
            self,
            "filename",
            filename,
        )

    def to_payload(self) -> InputFileProvenancePayload:
        return {
            "logical_name": self.logical_name,
            "filename": self.filename,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class PredictionProvenance:
    dataset_name: str
    dataset_version: int
    dataset_doi: str
    git_commit_sha: str
    git_dirty: bool
    config_sha256: str
    inputs: tuple[InputFileProvenance, ...]

    def __post_init__(self) -> None:
        dataset_name = self.dataset_name.strip()
        dataset_doi = self.dataset_doi.strip()
        git_commit_sha = self.git_commit_sha.strip().lower()

        if not dataset_name:
            raise ValueError(
                "Dataset name must not be empty"
            )

        if self.dataset_version < 1:
            raise ValueError(
                "Dataset version must be positive"
            )

        if not dataset_doi:
            raise ValueError(
                "Dataset DOI must not be empty"
            )

        if _GIT_COMMIT_PATTERN.fullmatch(
            git_commit_sha
        ) is None:
            raise ValueError(
                "Git commit SHA must contain 40 or 64 lowercase hex characters"
            )

        if _SHA256_PATTERN.fullmatch(
            self.config_sha256
        ) is None:
            raise ValueError(
                "Config SHA-256 must be 64 lowercase hex characters"
            )

        if not self.inputs:
            raise ValueError(
                "Prediction provenance must contain input files"
            )

        logical_names = tuple(
            item.logical_name
            for item in self.inputs
        )

        if len(set(logical_names)) != len(logical_names):
            raise ValueError(
                "Input provenance logical names must be unique"
            )

        object.__setattr__(
            self,
            "dataset_name",
            dataset_name,
        )
        object.__setattr__(
            self,
            "dataset_doi",
            dataset_doi,
        )
        object.__setattr__(
            self,
            "git_commit_sha",
            git_commit_sha,
        )

    def to_payload(self) -> PredictionProvenancePayload:
        return {
            "dataset_name": self.dataset_name,
            "dataset_version": self.dataset_version,
            "dataset_doi": self.dataset_doi,
            "git_commit_sha": self.git_commit_sha,
            "git_dirty": self.git_dirty,
            "config_sha256": self.config_sha256,
            "inputs": [
                item.to_payload()
                for item in self.inputs
            ],
        }


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(
            f"Provenance input file not found: {path}"
        )

    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def v2_calibration_config_payload(
    config: V2CalibrationConfig,
) -> V2CalibrationConfigPayload:
    return {
        "diffusion_values": list(
            config.diffusion_values
        ),
        "proliferation_values": list(
            config.proliferation_values
        ),
        "dt_days": config.dt_days,
        "latent_width_mm": config.latent_width_mm,
        "observation_threshold": (
            config.observation_threshold
        ),
        "soft_temperature": config.soft_temperature,
        "volume_weight": config.volume_weight,
    }


def v2_calibration_config_sha256(
    config: V2CalibrationConfig,
) -> str:
    payload = v2_calibration_config_payload(
        config
    )

    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")

    return hashlib.sha256(
        serialized
    ).hexdigest()


def _input_file_provenance(
    *,
    logical_name: str,
    path: Path,
) -> InputFileProvenance:
    return InputFileProvenance(
        logical_name=logical_name,
        filename=path.name,
        sha256=sha256_file(path),
    )


def build_prediction_provenance(
    *,
    dataset: CFBDatasetManifest,
    config: V2CalibrationConfig,
    start: PreparedPatientTimepoint,
    observed: PreparedPatientTimepoint,
    git_commit_sha: str,
    git_dirty: bool,
) -> PredictionProvenance:
    if start.patient_id != observed.patient_id:
        raise ValueError(
            "Prediction provenance timepoints belong to different patients"
        )

    inputs = (
        _input_file_provenance(
            logical_name=f"{start.name}_t1gd",
            path=start.t1gd.path,
        ),
        _input_file_provenance(
            logical_name=f"{start.name}_gtv",
            path=start.gtv.path,
        ),
        _input_file_provenance(
            logical_name=f"{start.name}_brain_mask",
            path=start.brain_mask.path,
        ),
        _input_file_provenance(
            logical_name=f"{observed.name}_t1gd",
            path=observed.t1gd.path,
        ),
        _input_file_provenance(
            logical_name=f"{observed.name}_gtv",
            path=observed.gtv.path,
        ),
        _input_file_provenance(
            logical_name=f"{observed.name}_brain_mask",
            path=observed.brain_mask.path,
        ),
    )

    return PredictionProvenance(
        dataset_name=dataset.name,
        dataset_version=dataset.version,
        dataset_doi=dataset.doi,
        git_commit_sha=git_commit_sha,
        git_dirty=git_dirty,
        config_sha256=(
            v2_calibration_config_sha256(
                config
            )
        ),
        inputs=inputs,
    )