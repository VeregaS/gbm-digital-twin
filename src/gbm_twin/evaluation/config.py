import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from gbm_twin.evaluation.cohort import (
    EvaluationConfig,
)


@dataclass(frozen=True)
class CohortExperimentConfig:
    patient_ids: tuple[int, ...]
    metadata_root: Path
    patients_root: Path
    evaluation: EvaluationConfig
    trajectory_stable_threshold: float
    raw_output_csv: Path
    analyzed_output_csv: Path


def _require_mapping(
    value: Any,
    name: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(
            f"{name} must be a mapping"
        )

    return value


def _require_list(
    value: Any,
    name: str,
) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(
            f"{name} must be a list"
        )

    return value


def evaluation_signature(
    config: EvaluationConfig,
) -> str:
    payload = {
        "target_spacing": (
            config.target_spacing
        ),
        "threshold": config.threshold,
        "dt": config.dt,
        "diffusion_values": (
            config.diffusion_values
        ),
        "proliferation_values": (
            config.proliferation_values
        ),
        "volume_weight": (
            config.volume_weight
        ),
    }

    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )

    digest = hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()

    return digest[:16]


def load_cohort_experiment_config(
    path: Path,
) -> CohortExperimentConfig:
    if not path.is_file():
        raise FileNotFoundError(
            f"Config file not found: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        raw = yaml.safe_load(file)

    root = _require_mapping(
        raw,
        "config",
    )

    raw_patients = _require_list(
        root.get("patients"),
        "patients",
    )

    patient_ids = tuple(
        int(patient_id)
        for patient_id in raw_patients
    )

    if not patient_ids:
        raise ValueError(
            "patients must not be empty"
        )

    data = _require_mapping(
        root.get("data"),
        "data",
    )

    evaluation = _require_mapping(
        root.get("evaluation"),
        "evaluation",
    )

    analysis = _require_mapping(
        root.get("analysis"),
        "analysis",
    )

    output = _require_mapping(
        root.get("output"),
        "output",
    )

    raw_spacing = _require_list(
        evaluation.get(
            "target_spacing"
        ),
        "evaluation.target_spacing",
    )

    if len(raw_spacing) != 3:
        raise ValueError(
            "evaluation.target_spacing "
            "must contain exactly 3 values"
        )

    target_spacing = (
        float(raw_spacing[0]),
        float(raw_spacing[1]),
        float(raw_spacing[2]),
    )

    raw_diffusion_values = _require_list(
        evaluation.get(
            "diffusion_values"
        ),
        "evaluation.diffusion_values",
    )

    raw_proliferation_values = _require_list(
        evaluation.get(
            "proliferation_values"
        ),
        "evaluation.proliferation_values",
    )

    evaluation_config = EvaluationConfig(
        target_spacing=target_spacing,
        threshold=float(
            evaluation["threshold"]
        ),
        dt=float(
            evaluation["dt"]
        ),
        diffusion_values=tuple(
            float(value)
            for value
            in raw_diffusion_values
        ),
        proliferation_values=tuple(
            float(value)
            for value
            in raw_proliferation_values
        ),
        volume_weight=float(
            evaluation["volume_weight"]
        ),
    )

    trajectory_stable_threshold = float(
        analysis[
            "trajectory_stable_threshold"
        ]
    )

    if trajectory_stable_threshold < 0:
        raise ValueError(
            "analysis."
            "trajectory_stable_threshold "
            "must be non-negative"
        )

    return CohortExperimentConfig(
        patient_ids=patient_ids,
        metadata_root=Path(
            str(data["metadata_root"])
        ),
        patients_root=Path(
            str(data["patients_root"])
        ),
        evaluation=evaluation_config,
        trajectory_stable_threshold=(
            trajectory_stable_threshold
        ),
        raw_output_csv=Path(
            str(output["raw_csv"])
        ),
        analyzed_output_csv=Path(
            str(output["analyzed_csv"])
        ),
    )