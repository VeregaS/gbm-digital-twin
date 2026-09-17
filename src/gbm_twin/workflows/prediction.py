from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from gbm_twin.calibration.grid_search import CalibrationResult
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
    TreatmentModel,
    simulate_reaction_diffusion,
)
from gbm_twin.models.treatment import (
    FractionatedRadiotherapy,
    PIRTFractionatedRadiotherapy,
    PostRadiotherapyEffect,
    RadiotherapyProtocol,
)
from gbm_twin.workflows.calibration import (
    V2CalibrationConfig,
    V2CalibrationRun,
    calibrate_v2_interval,
)
from gbm_twin.workflows.contracts import PredictionTarget
from gbm_twin.workflows.patients import PreparedPatientTimepoint
from gbm_twin.workflows.post_rt_selection_artifact import (
    SelectedPostRTCandidate,
)
from gbm_twin.workflows.provenance import PredictionProvenance

PREDICTION_ARTIFACT_SCHEMA_VERSION = 3
V2_PREDICTION_ARTIFACT_SCHEMA_VERSION = (
    PREDICTION_ARTIFACT_SCHEMA_VERSION
)
V3_PREDICTION_ARTIFACT_SCHEMA_VERSION = (
    PREDICTION_ARTIFACT_SCHEMA_VERSION
)

V2_FROZEN_PROTOCOL_VERSION = "v2-frozen-1"
V3_FROZEN_PROTOCOL_VERSION = "v3-post-rt-1"

V2_ASSIMILATION_RULE = (
    "replace_with_observed_t1_latent_state"
)
V3_ASSIMILATION_RULE = V2_ASSIMILATION_RULE

_ARRAY_FILES = {
    "prediction_field": "prediction_field.npy",
    "prediction_mask": "prediction_mask.npy",
    "persistence_mask": "persistence_mask.npy",
    "volume_baseline_mask": "volume_baseline_mask.npy",
}

ManifestFactory = Callable[
    [dict[str, Path]],
    dict[str, Any],
]


@dataclass(frozen=True)
class FrozenPredictionArtifact:
    directory: Path
    manifest: dict[str, Any]
    prediction_field: np.ndarray
    prediction_mask: np.ndarray
    persistence_mask: np.ndarray
    volume_baseline_mask: np.ndarray


FrozenV2PredictionArtifact = FrozenPredictionArtifact
FrozenV3PredictionArtifact = FrozenPredictionArtifact


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def _calibration_result_payload(
    result: CalibrationResult,
) -> dict[str, float]:
    return {
        "diffusion": result.diffusion,
        "proliferation": (
            result.proliferation
        ),
        "dice": result.dice,
        "volume_error": (
            result.volume_error
        ),
        "loss": result.loss,
    }


def _fractionated_payload(
    treatment: FractionatedRadiotherapy,
) -> dict[str, Any]:
    kind = (
        "pirt_fractionated_radiotherapy"
        if isinstance(
            treatment,
            PIRTFractionatedRadiotherapy,
        )
        else "fractionated_radiotherapy"
    )

    return {
        "kind": kind,
        "fraction_days": list(
            treatment.fraction_days
        ),
        "dose_per_fraction_gy": (
            treatment.dose_per_fraction_gy
        ),
        "alpha_per_gy": (
            treatment.alpha_per_gy
        ),
        "beta_per_gy2": (
            treatment.beta_per_gy2
        ),
    }


def _post_rt_payload(
    effect: PostRadiotherapyEffect,
) -> dict[str, float]:
    return {
        "start_day": effect.start_day,
        "initial_kill_rate_per_day": (
            effect.initial_kill_rate
        ),
        "decay_time_days": (
            effect.decay_time_days
        ),
    }


def _treatment_payload(
    treatment: TreatmentModel | None,
) -> dict[str, Any]:
    if treatment is None:
        return {
            "kind": "none",
        }

    if isinstance(
        treatment,
        RadiotherapyProtocol,
    ):
        return {
            "kind": "radiotherapy_protocol",
            "fractions": (
                _fractionated_payload(
                    treatment.fractions
                )
            ),
            "post_rt_effect": (
                None
                if treatment.post_effect
                is None
                else _post_rt_payload(
                    treatment.post_effect
                )
            ),
        }

    if isinstance(
        treatment,
        FractionatedRadiotherapy,
    ):
        return _fractionated_payload(
            treatment
        )

    raise TypeError(
        "Frozen prediction artifacts "
        "support only fractionated "
        "radiotherapy protocols"
    )


def _array_metadata(
    path: Path,
    array: np.ndarray,
) -> dict[str, Any]:
    return {
        "file": path.name,
        "sha256": _sha256(path),
        "dtype": str(array.dtype),
        "shape": list(array.shape),
    }


def _build_manifest(
    *,
    start: PreparedPatientTimepoint,
    observed: PreparedPatientTimepoint,
    target: PredictionTarget,
    provenance: PredictionProvenance,
    config: V2CalibrationConfig,
    treatment: TreatmentModel | None,
    calibration: V2CalibrationRun,
    arrays: dict[str, np.ndarray],
    array_paths: dict[str, Path],
    protocol_version: str,
    model_version: str,
    assimilation_rule: str,
    model_selection: (
        SelectedPostRTCandidate
        | None
    ) = None,
) -> dict[str, Any]:
    prediction_duration = (
        target.target_day
        - observed.days_from_baseline
    )

    manifest: dict[str, Any] = {
        "schema_version": (
            PREDICTION_ARTIFACT_SCHEMA_VERSION
        ),
        "protocol_version": (
            protocol_version
        ),
        "model_version": model_version,
        "sealed": True,
        "patient_id": start.patient_id,
        "provenance": (
            provenance.to_payload()
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
                observed.days_from_baseline
            ),
            "duration_days": (
                calibration.duration_days
            ),
        },
        "prediction_horizon": {
            "start_timepoint": (
                observed.name
            ),
            "start_day": (
                observed.days_from_baseline
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
                calibration.best.diffusion
            ),
            "proliferation": (
                calibration.best.proliferation
            ),
            "dt_days": config.dt_days,
            "latent_width_mm": (
                config.latent_width_mm
            ),
            "observation_threshold": (
                config.observation_threshold
            ),
            "soft_temperature": (
                config.soft_temperature
            ),
            "volume_weight": (
                config.volume_weight
            ),
            "assimilation_rule": (
                assimilation_rule
            ),
        },
        "treatment": (
            _treatment_payload(
                treatment
            )
        ),
        "calibration": {
            "objective": "soft",
            "diagnostics": {
                "diffusion_at_boundary": (
                    calibration
                    .diagnostics
                    .diffusion_at_boundary
                ),
                "proliferation_at_boundary": (
                    calibration
                    .diagnostics
                    .proliferation_at_boundary
                ),
                "diffusion_bracketed": (
                    calibration
                    .diagnostics
                    .diffusion_bracketed
                ),
                "proliferation_bracketed": (
                    calibration
                    .diagnostics
                    .proliferation_bracketed
                ),
                "identifiable": (
                    calibration
                    .diagnostics
                    .identifiable
                ),
            },
            "best": (
                _calibration_result_payload(
                    calibration.best
                )
            ),
            "coarse_best": (
                _calibration_result_payload(
                    calibration.coarse_best
                )
            ),
            "coarse_diffusion_values": (
                list(
                    config.diffusion_values
                )
            ),
            "coarse_proliferation_values": (
                list(
                    config
                    .proliferation_values
                )
            ),
            "refined_diffusion_values": (
                list(
                    calibration
                    .refined_diffusion_values
                )
            ),
            "refined_proliferation_values": (
                list(
                    calibration
                    .refined_proliferation_values
                )
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

    if model_selection is not None:
        manifest[
            "model_selection"
        ] = (
            model_selection
            .to_provenance_payload()
        )

    return manifest


def _save_artifact(
    *,
    output_dir: Path,
    manifest_factory: ManifestFactory,
    arrays: dict[str, np.ndarray],
    expected_protocol_version: str,
    expected_model_version: str,
) -> FrozenPredictionArtifact:
    destination = (
        output_dir.resolve()
    )

    if destination.exists():
        raise FileExistsError(
            "Prediction artifact "
            f"already exists: {destination}"
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

        manifest_path = (
            temporary
            / "manifest.json"
        )

        manifest_path.write_text(
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
            _sha256(
                manifest_path
            )
            + "  manifest.json\n",
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

    return _load_frozen_prediction(
        destination,
        expected_protocol_version=(
            expected_protocol_version
        ),
        expected_model_version=(
            expected_model_version
        ),
    )


def _freeze_prediction(
    *,
    start: PreparedPatientTimepoint,
    observed: PreparedPatientTimepoint,
    target: PredictionTarget,
    provenance: PredictionProvenance,
    treatment: TreatmentModel | None,
    config: V2CalibrationConfig,
    cache_dir: Path,
    output_dir: Path,
    workers: int,
    protocol_version: str,
    model_version: str,
    assimilation_rule: str,
    model_selection: (
        SelectedPostRTCandidate
        | None
    ) = None,
) -> FrozenPredictionArtifact:
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
            "Frozen prediction protocol "
            "requires the "
            "t0 -> t1 -> t2 sequence"
        )

    if (
        start.patient_id
        != observed.patient_id
    ):
        raise ValueError(
            "Prediction timepoints belong "
            "to different patients"
        )

    if (
        target.target_day
        <= observed.days_from_baseline
    ):
        raise ValueError(
            "Prediction target must occur "
            "after the observed timepoint"
        )

    if output_dir.resolve().exists():
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
            spacing=observed.spacing,
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
            spacing=observed.spacing,
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
        expected_protocol_version=(
            protocol_version
        ),
        expected_model_version=(
            model_version
        ),
        manifest_factory=(
            lambda array_paths: (
                _build_manifest(
                    start=start,
                    observed=observed,
                    target=target,
                    provenance=provenance,
                    config=config,
                    treatment=treatment,
                    calibration=(
                        calibration
                    ),
                    arrays=arrays,
                    array_paths=(
                        array_paths
                    ),
                    protocol_version=(
                        protocol_version
                    ),
                    model_version=(
                        model_version
                    ),
                    assimilation_rule=(
                        assimilation_rule
                    ),
                    model_selection=(
                        model_selection
                    ),
                )
            )
        ),
    )


def freeze_v2_prediction(
    *,
    start: PreparedPatientTimepoint,
    observed: PreparedPatientTimepoint,
    target: PredictionTarget,
    provenance: PredictionProvenance,
    treatment: (
        PIRTFractionatedRadiotherapy
        | None
    ),
    config: V2CalibrationConfig,
    cache_dir: Path,
    output_dir: Path,
    workers: int = 1,
) -> FrozenV2PredictionArtifact:
    return _freeze_prediction(
        start=start,
        observed=observed,
        target=target,
        provenance=provenance,
        treatment=treatment,
        config=config,
        cache_dir=cache_dir,
        output_dir=output_dir,
        workers=workers,
        protocol_version=(
            V2_FROZEN_PROTOCOL_VERSION
        ),
        model_version="V2",
        assimilation_rule=(
            V2_ASSIMILATION_RULE
        ),
    )


def freeze_v3_prediction(
    *,
    start: PreparedPatientTimepoint,
    observed: PreparedPatientTimepoint,
    target: PredictionTarget,
    provenance: PredictionProvenance,
    treatment: RadiotherapyProtocol,
    model_selection: SelectedPostRTCandidate,
    config: V2CalibrationConfig,
    cache_dir: Path,
    output_dir: Path,
    workers: int = 1,
) -> FrozenV3PredictionArtifact:
    if treatment.post_effect is None:
        raise ValueError(
            "V3 requires a delayed "
            "post-radiotherapy effect"
        )

    return _freeze_prediction(
        start=start,
        observed=observed,
        target=target,
        provenance=provenance,
        treatment=treatment,
        config=config,
        cache_dir=cache_dir,
        output_dir=output_dir,
        workers=workers,
        protocol_version=(
            V3_FROZEN_PROTOCOL_VERSION
        ),
        model_version="V3",
        assimilation_rule=(
            V3_ASSIMILATION_RULE
        ),
        model_selection=(
            model_selection
        ),
    )


def _load_frozen_prediction(
    output_dir: Path,
    *,
    expected_protocol_version: str,
    expected_model_version: str,
) -> FrozenPredictionArtifact:
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
            f"not found: {manifest_path}"
        )

    if not seal_path.is_file():
        raise FileNotFoundError(
            "Prediction manifest seal "
            f"not found: {seal_path}"
        )

    seal_tokens = (
        seal_path.read_text(
            encoding="ascii"
        ).split()
    )

    if not seal_tokens:
        raise ValueError(
            "Prediction manifest seal "
            "is empty"
        )

    expected_manifest_sha256 = (
        seal_tokens[0]
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

    raw: object = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        raw,
        dict,
    ):
        raise ValueError(
            "Prediction manifest "
            "must contain a JSON object"
        )

    manifest = dict(raw)

    if (
        manifest.get(
            "schema_version"
        )
        != (
            PREDICTION_ARTIFACT_SCHEMA_VERSION
        )
    ):
        raise ValueError(
            "Unsupported prediction "
            "artifact schema version"
        )

    if (
        manifest.get(
            "protocol_version"
        )
        != expected_protocol_version
    ):
        raise ValueError(
            "Unsupported frozen "
            f"{expected_model_version} "
            "protocol version"
        )

    if (
        manifest.get(
            "model_version"
        )
        != expected_model_version
        or manifest.get(
            "sealed"
        )
        is not True
    ):
        raise ValueError(
            "Prediction artifact is not "
            f"a sealed {expected_model_version} "
            "artifact"
        )

    provenance = manifest.get(
        "provenance"
    )

    if not isinstance(
        provenance,
        dict,
    ):
        raise ValueError(
            "Prediction manifest is "
            "missing provenance"
        )

    calibration_payload = (
        manifest.get(
            "calibration"
        )
    )

    if not isinstance(
        calibration_payload,
        dict,
    ):
        raise ValueError(
            "Prediction manifest is "
            "missing calibration metadata"
        )

    diagnostics_payload = (
        calibration_payload.get(
            "diagnostics"
        )
    )

    if not isinstance(
        diagnostics_payload,
        dict,
    ):
        raise ValueError(
            "Prediction manifest is "
            "missing calibration diagnostics"
        )

    required_diagnostic_fields = {
        "diffusion_at_boundary",
        "proliferation_at_boundary",
        "diffusion_bracketed",
        "proliferation_bracketed",
        "identifiable",
    }

    if not (
        required_diagnostic_fields
        .issubset(
            diagnostics_payload
        )
    ):
        raise ValueError(
            "Prediction manifest "
            "calibration diagnostics "
            "are incomplete"
        )

    required_provenance_fields = {
        "dataset_name",
        "dataset_version",
        "dataset_doi",
        "git_commit_sha",
        "git_dirty",
        "config_sha256",
        "inputs",
    }

    if not (
        required_provenance_fields
        .issubset(
            provenance
        )
    ):
        raise ValueError(
            "Prediction manifest "
            "provenance is incomplete"
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
            "missing geometry or "
            "array metadata"
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
                f"array not found: {path}"
            )

        if (
            _sha256(path)
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
                (0, 1),
            )
        ):
            raise ValueError(
                "Prediction artifact "
                "mask is not binary: "
                f"{name}"
            )

    return FrozenPredictionArtifact(
        directory=directory,
        manifest=manifest,
        prediction_field=(
            prediction_field
        ),
        prediction_mask=(
            loaded[
                "prediction_mask"
            ].astype(bool)
        ),
        persistence_mask=(
            loaded[
                "persistence_mask"
            ].astype(bool)
        ),
        volume_baseline_mask=(
            loaded[
                "volume_baseline_mask"
            ].astype(bool)
        ),
    )


def load_frozen_v2_prediction(
    output_dir: Path,
) -> FrozenV2PredictionArtifact:
    return _load_frozen_prediction(
        output_dir,
        expected_protocol_version=(
            V2_FROZEN_PROTOCOL_VERSION
        ),
        expected_model_version="V2",
    )


def load_frozen_v3_prediction(
    output_dir: Path,
) -> FrozenV3PredictionArtifact:
    artifact = (
        _load_frozen_prediction(
            output_dir,
            expected_protocol_version=(
                V3_FROZEN_PROTOCOL_VERSION
            ),
            expected_model_version="V3",
        )
    )

    treatment = (
        artifact.manifest.get(
            "treatment"
        )
    )
    model_selection = (
        artifact.manifest.get(
            "model_selection"
        )
    )

    if (
        not isinstance(
            treatment,
            dict,
        )
        or treatment.get(
            "kind"
        )
        != "radiotherapy_protocol"
    ):
        raise ValueError(
            "V3 prediction artifact "
            "is missing its RT protocol"
        )

    if not isinstance(
        model_selection,
        dict,
    ):
        raise ValueError(
            "V3 prediction artifact "
            "is missing model-selection "
            "provenance"
        )

    required_selection_fields = {
        "kind",
        "candidate_id",
        "initial_kill_rate_per_day",
        "decay_time_days",
        "source_manifest_sha256",
        "selection_config_sha256",
        "experiment_config_sha256",
    }

    if not (
        required_selection_fields
        .issubset(
            model_selection
        )
    ):
        raise ValueError(
            "V3 model-selection "
            "provenance is incomplete"
        )

    return artifact
