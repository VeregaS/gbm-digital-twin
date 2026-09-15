from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from gbm_twin.calibration.grid_search import (
    CalibrationResult,
)
from gbm_twin.evaluation.baselines import (
    extrapolate_volume,
    resize_mask_to_volume,
)
from gbm_twin.models.latent_state import (
    LatentStateParameters,
    latent_state_from_gtv,
)
from gbm_twin.models.reaction_diffusion import (
    ReactionDiffusionParameters,
    build_computational_domain,
)
from gbm_twin.models.solver import (
    simulate_reaction_diffusion,
)
from gbm_twin.models.treatment import (
    PIRTFractionatedRadiotherapy,
)
from gbm_twin.workflows.calibration import (
    V2CalibrationConfig,
    V2CalibrationRun,
    calibrate_v2_interval,
)
from gbm_twin.workflows.contracts import (
    PredictionTarget,
)
from gbm_twin.workflows.patients import (
    PreparedPatientTimepoint,
)

V2_PREDICTION_ARTIFACT_SCHEMA_VERSION = 1
V2_FROZEN_PROTOCOL_VERSION = "v2-frozen-1"
V2_ASSIMILATION_RULE = (
    "replace_with_observed_t1_latent_state"
)

_ARRAY_FILES = {
    "prediction_field": (
        "prediction_field.npy"
    ),
    "prediction_mask": (
        "prediction_mask.npy"
    ),
    "persistence_mask": (
        "persistence_mask.npy"
    ),
    "volume_baseline_mask": (
        "volume_baseline_mask.npy"
    ),
}


@dataclass(frozen=True)
class FrozenV2PredictionArtifact:
    directory: Path
    manifest: dict[str, Any]
    prediction_field: np.ndarray
    prediction_mask: np.ndarray
    persistence_mask: np.ndarray
    volume_baseline_mask: np.ndarray


def _sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open(
        "rb"
    ) as stream:
        for chunk in iter(
            lambda: stream.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(
                chunk
            )

    return digest.hexdigest()


def _calibration_result_payload(
    result: CalibrationResult,
) -> dict[str, float]:
    return {
        "diffusion": (
            result.diffusion
        ),
        "proliferation": (
            result.proliferation
        ),
        "dice": result.dice,
        "volume_error": (
            result.volume_error
        ),
        "loss": result.loss,
    }


def _treatment_payload(
    treatment: (
        PIRTFractionatedRadiotherapy
        | None
    ),
) -> dict[str, Any]:
    if treatment is None:
        return {
            "kind": "none",
        }

    return {
        "kind": (
            "pirt_fractionated_"
            "radiotherapy"
        ),
        "fraction_days": list(
            treatment.fraction_days
        ),
        "dose_per_fraction_gy": (
            treatment
            .dose_per_fraction_gy
        ),
        "alpha_per_gy": (
            treatment.alpha_per_gy
        ),
        "beta_per_gy2": (
            treatment.beta_per_gy2
        ),
    }


def _array_metadata(
    path: Path,
    array: np.ndarray,
) -> dict[str, Any]:
    return {
        "file": path.name,
        "sha256": _sha256(
            path
        ),
        "dtype": str(
            array.dtype
        ),
        "shape": list(
            array.shape
        ),
    }


def _build_manifest(
    *,
    start: PreparedPatientTimepoint,
    observed: PreparedPatientTimepoint,
    target: PredictionTarget,
    config: V2CalibrationConfig,
    treatment: (
        PIRTFractionatedRadiotherapy
        | None
    ),
    calibration: V2CalibrationRun,
    arrays: dict[
        str,
        np.ndarray,
    ],
    array_paths: dict[
        str,
        Path,
    ],
) -> dict[str, Any]:
    prediction_duration = (
        target.target_day
        - observed.days_from_baseline
    )

    return {
        "schema_version": (
            V2_PREDICTION_ARTIFACT_SCHEMA_VERSION
        ),
        "protocol_version": (
            V2_FROZEN_PROTOCOL_VERSION
        ),
        "model_version": "V2",
        "sealed": True,
        "patient_id": (
            start.patient_id
        ),
        "calibration_interval": {
            "start_timepoint": (
                start.name
            ),
            "start_day": (
                start.days_from_baseline
            ),
            "observed_timepoint": (
                observed.name
            ),
            "observed_day": (
                observed
                .days_from_baseline
            ),
            "duration_days": (
                calibration
                .duration_days
            ),
        },
        "prediction_horizon": {
            "start_timepoint": (
                observed.name
            ),
            "start_day": (
                observed
                .days_from_baseline
            ),
            "target_timepoint": (
                target.timepoint_name
            ),
            "target_day": (
                target.target_day
            ),
            "duration_days": (
                prediction_duration
            ),
        },
        "parameters": {
            "diffusion": (
                calibration
                .best
                .diffusion
            ),
            "proliferation": (
                calibration
                .best
                .proliferation
            ),
            "dt_days": (
                config.dt_days
            ),
            "latent_width_mm": (
                config
                .latent_width_mm
            ),
            "observation_threshold": (
                config
                .observation_threshold
            ),
            "soft_temperature": (
                config
                .soft_temperature
            ),
            "volume_weight": (
                config.volume_weight
            ),
            "assimilation_rule": (
                V2_ASSIMILATION_RULE
            ),
        },
        "treatment": (
            _treatment_payload(
                treatment
            )
        ),
        "calibration": {
            "objective": "soft",
            "best": (
                _calibration_result_payload(
                    calibration.best
                )
            ),
            "coarse_best": (
                _calibration_result_payload(
                    calibration
                    .coarse_best
                )
            ),
            "coarse_diffusion_values": list(
                config
                .diffusion_values
            ),
            "coarse_proliferation_values": list(
                config
                .proliferation_values
            ),
            "refined_diffusion_values": list(
                calibration
                .refined_diffusion_values
            ),
            "refined_proliferation_values": list(
                calibration
                .refined_proliferation_values
            ),
            "candidates": [
                _calibration_result_payload(
                    candidate
                )
                for candidate
                in calibration.candidates
            ],
        },
        "geometry": {
            "shape": list(
                observed.gtv.shape
            ),
            "spacing": list(
                observed.gtv.spacing
            ),
            "affine": np.asarray(
                observed.gtv.affine,
                dtype=float,
            ).tolist(),
        },
        "arrays": {
            name: _array_metadata(
                array_paths[name],
                array,
            )
            for name, array
            in arrays.items()
        },
    }


def _save_artifact(
    *,
    output_dir: Path,
    manifest_factory,
    arrays: dict[
        str,
        np.ndarray,
    ],
) -> FrozenV2PredictionArtifact:
    destination = (
        output_dir.resolve()
    )

    if destination.exists():
        raise FileExistsError(
            "Prediction artifact "
            "already exists: "
            f"{destination}"
        )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = Path(
        tempfile.mkdtemp(
            dir=destination.parent,
            prefix=(
                f".{destination.name}-"
            ),
        )
    )

    try:
        array_paths: dict[
            str,
            Path,
        ] = {}

        for name, array in (
            arrays.items()
        ):
            path = (
                temporary
                / _ARRAY_FILES[name]
            )

            np.save(
                path,
                array,
                allow_pickle=False,
            )

            array_paths[name] = path

        manifest = (
            manifest_factory(
                array_paths
            )
        )

        (
            temporary
            / "manifest.json"
        ).write_text(
            json.dumps(
                manifest,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

        (
            temporary
            / "manifest.sha256"
        ).write_text(
            (
                _sha256(
                    temporary
                    / "manifest.json"
                )
                + "  manifest.json\n"
            ),
            encoding="ascii",
        )

        temporary.rename(
            destination
        )

    except BaseException:
        shutil.rmtree(
            temporary,
            ignore_errors=True,
        )
        raise

    return (
        load_frozen_v2_prediction(
            destination
        )
    )


def freeze_v2_prediction(
    *,
    start: PreparedPatientTimepoint,
    observed: PreparedPatientTimepoint,
    target: PredictionTarget,
    treatment: (
        PIRTFractionatedRadiotherapy
        | None
    ),
    config: V2CalibrationConfig,
    cache_dir: Path,
    output_dir: Path,
    workers: int = 1,
) -> FrozenV2PredictionArtifact:
    if (
        start.name,
        observed.name,
        target.timepoint_name,
    ) != (
        "t0",
        "t1",
        "t2",
    ):
        raise ValueError(
            "Frozen V2 protocol requires "
            "the t0 -> t1 -> t2 sequence"
        )

    if (
        target.target_day
        <= observed.days_from_baseline
    ):
        raise ValueError(
            "Prediction target must occur "
            "after the observed timepoint"
        )

    if (
        output_dir
        .resolve()
        .exists()
    ):
        raise FileExistsError(
            "Prediction artifact "
            "already exists: "
            f"{output_dir.resolve()}"
        )

    calibration = (
        calibrate_v2_interval(
            start=start,
            observed=observed,
            treatment=treatment,
            config=config,
            cache_dir=cache_dir,
            workers=workers,
        )
    )

    prediction_domain = (
        build_computational_domain(
            observed.brain_mask.data,
            observed.gtv.data,
        )
    )

    assimilated_state = (
        latent_state_from_gtv(
            observed.gtv.data,
            observed.brain_mask.data,
            spacing=(
                observed.spacing
            ),
            parameters=(
                LatentStateParameters(
                    transition_width_mm=(
                        config
                        .latent_width_mm
                    ),
                )
            ),
        )
    )

    prediction_duration = (
        target.target_day
        - observed.days_from_baseline
    )

    predicted_field = (
        simulate_reaction_diffusion(
            assimilated_state,
            ReactionDiffusionParameters(
                diffusion=(
                    calibration
                    .best
                    .diffusion
                ),
                proliferation=(
                    calibration
                    .best
                    .proliferation
                ),
            ),
            spacing=(
                observed.spacing
            ),
            duration_days=(
                prediction_duration
            ),
            dt=config.dt_days,
            domain_mask=(
                prediction_domain
            ),
            treatment=treatment,
            start_time_day=(
                observed
                .days_from_baseline
            ),
        )
        .astype(
            np.float32,
            copy=False,
        )
    )

    start_mask = (
        start.gtv.data
        > config.observation_threshold
    )

    observed_mask = (
        observed.gtv.data
        > config.observation_threshold
    )

    prediction_mask = (
        predicted_field
        >= config.observation_threshold
    )

    voxel_volume_cm3 = (
        float(
            np.prod(
                observed.spacing
            )
        )
        / 1000.0
    )

    start_volume_cm3 = (
        float(
            np.count_nonzero(
                start_mask
            )
        )
        * voxel_volume_cm3
    )

    observed_volume_cm3 = (
        float(
            np.count_nonzero(
                observed_mask
            )
        )
        * voxel_volume_cm3
    )

    baseline_target_volume_cm3 = (
        extrapolate_volume(
            start_volume_cm3,
            observed_volume_cm3,
            dt01_days=(
                calibration
                .duration_days
            ),
            dt12_days=(
                prediction_duration
            ),
        )
    )

    volume_baseline_mask = (
        resize_mask_to_volume(
            observed_mask,
            target_volume_cm3=(
                baseline_target_volume_cm3
            ),
            spacing=(
                observed.spacing
            ),
        )
    )

    arrays = {
        "prediction_field": (
            predicted_field
        ),
        "prediction_mask": (
            prediction_mask.astype(
                np.uint8
            )
        ),
        "persistence_mask": (
            observed_mask.astype(
                np.uint8
            )
        ),
        "volume_baseline_mask": (
            volume_baseline_mask.astype(
                np.uint8
            )
        ),
    }

    return _save_artifact(
        output_dir=output_dir,
        arrays=arrays,
        manifest_factory=(
            lambda array_paths: (
                _build_manifest(
                    start=start,
                    observed=observed,
                    target=target,
                    config=config,
                    treatment=treatment,
                    calibration=(
                        calibration
                    ),
                    arrays=arrays,
                    array_paths=(
                        array_paths
                    ),
                )
            )
        ),
    )


def load_frozen_v2_prediction(
    output_dir: Path,
) -> FrozenV2PredictionArtifact:
    directory = (
        output_dir.resolve()
    )

    manifest_path = (
        directory
        / "manifest.json"
    )

    seal_path = (
        directory
        / "manifest.sha256"
    )

    if not manifest_path.is_file():
        raise FileNotFoundError(
            "Prediction manifest "
            "not found: "
            f"{manifest_path}"
        )

    if not seal_path.is_file():
        raise FileNotFoundError(
            "Prediction manifest seal "
            "not found: "
            f"{seal_path}"
        )

    expected_manifest_sha256 = (
        seal_path
        .read_text(
            encoding="ascii"
        )
        .split()[0]
    )

    if (
        _sha256(
            manifest_path
        )
        != expected_manifest_sha256
    ):
        raise ValueError(
            "Prediction manifest "
            "checksum mismatch"
        )

    manifest = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    if (
        manifest.get(
            "schema_version"
        )
        != V2_PREDICTION_ARTIFACT_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported prediction "
            "artifact schema version"
        )

    if (
        manifest.get(
            "protocol_version"
        )
        != V2_FROZEN_PROTOCOL_VERSION
    ):
        raise ValueError(
            "Unsupported frozen V2 "
            "protocol version"
        )

    if (
        manifest.get(
            "model_version"
        )
        != "V2"
        or manifest.get(
            "sealed"
        )
        is not True
    ):
        raise ValueError(
            "Prediction artifact is not "
            "a sealed V2 artifact"
        )

    geometry = manifest.get(
        "geometry"
    )

    array_metadata = (
        manifest.get(
            "arrays"
        )
    )

    if (
        not isinstance(
            geometry,
            dict,
        )
        or not isinstance(
            array_metadata,
            dict,
        )
    ):
        raise ValueError(
            "Prediction manifest is "
            "missing geometry or array "
            "metadata"
        )

    expected_shape = tuple(
        geometry.get(
            "shape",
            (),
        )
    )

    loaded: dict[
        str,
        np.ndarray,
    ] = {}

    for (
        name,
        expected_file,
    ) in _ARRAY_FILES.items():
        metadata = (
            array_metadata.get(
                name
            )
        )

        if (
            not isinstance(
                metadata,
                dict,
            )
            or metadata.get(
                "file"
            )
            != expected_file
        ):
            raise ValueError(
                "Invalid metadata for "
                "artifact array: "
                f"{name}"
            )

        path = (
            directory
            / expected_file
        )

        if not path.is_file():
            raise FileNotFoundError(
                "Prediction artifact "
                "array not found: "
                f"{path}"
            )

        if (
            _sha256(
                path
            )
            != metadata.get(
                "sha256"
            )
        ):
            raise ValueError(
                "Prediction artifact "
                "checksum mismatch: "
                f"{name}"
            )

        array = np.load(
            path,
            allow_pickle=False,
        )

        if (
            array.shape
            != expected_shape
            or list(
                array.shape
            )
            != metadata.get(
                "shape"
            )
        ):
            raise ValueError(
                "Prediction artifact "
                "shape mismatch: "
                f"{name}"
            )

        if (
            str(
                array.dtype
            )
            != metadata.get(
                "dtype"
            )
        ):
            raise ValueError(
                "Prediction artifact "
                "dtype mismatch: "
                f"{name}"
            )

        loaded[name] = array

    prediction_field = (
        loaded[
            "prediction_field"
        ]
    )

    if (
        not np.all(
            np.isfinite(
                prediction_field
            )
        )
        or np.any(
            (
                prediction_field
                < 0.0
            )
            | (
                prediction_field
                > 1.0
            )
        )
    ):
        raise ValueError(
            "Prediction field must "
            "contain finite values "
            "within [0, 1]"
        )

    for name in (
        "prediction_mask",
        "persistence_mask",
        "volume_baseline_mask",
    ):
        if not np.all(
            np.isin(
                loaded[name],
                (
                    0,
                    1,
                ),
            )
        ):
            raise ValueError(
                "Prediction artifact "
                "mask is not binary: "
                f"{name}"
            )

    return FrozenV2PredictionArtifact(
        directory=directory,
        manifest=manifest,
        prediction_field=(
            prediction_field
        ),
        prediction_mask=(
            loaded[
                "prediction_mask"
            ].astype(
                bool
            )
        ),
        persistence_mask=(
            loaded[
                "persistence_mask"
            ].astype(
                bool
            )
        ),
        volume_baseline_mask=(
            loaded[
                "volume_baseline_mask"
            ].astype(
                bool
            )
        ),
    )