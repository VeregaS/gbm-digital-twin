"""Public workflow exports, imported on demand to keep lightweight callers lightweight."""

from importlib import import_module
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gbm_twin.workflows.calibration import (
        V2_ALPHA_BETA_RATIO_GY,
        V2_EFFECTIVE_ALPHA_PER_GY,
        V2_LATENT_WIDTH_MM,
        V2_OBSERVATION_THRESHOLD,
        V2_SOFT_TEMPERATURE,
        V2CalibrationConfig,
        V2CalibrationRun,
        calibrate_v2_interval,
    )
    from gbm_twin.workflows.cohort_evaluation import (
        COHORT_EVALUATION_SCHEMA_VERSION,
        CohortEvaluationResult,
        evaluate_frozen_cohort,
    )
    from gbm_twin.workflows.cohort_freeze import (
        COHORT_FREEZE_SCHEMA_VERSION,
        CohortFreezeResult,
        freeze_cohort_from_configs,
    )
    from gbm_twin.workflows.contracts import PredictionTarget
    from gbm_twin.workflows.eligibility import (
        EligibilityIssue,
        EligibilityReason,
        PatientEligibility,
        assess_patient_eligibility,
    )
    from gbm_twin.workflows.patient_catalog import (
        PatientCatalogSummary,
        PatientCatalogTimepoint,
        PatientTreatmentSummary,
        discover_patient_ids,
        get_patient_catalog_summary,
    )
    from gbm_twin.workflows.patient_twin import (
        PatientNotEligibleError,
        PatientTwinService,
    )
    from gbm_twin.workflows.patients import (
        DEFAULT_TARGET_SPACING,
        PreparedPatientTimepoint,
        prepare_patient_timepoint,
    )
    from gbm_twin.workflows.prediction import (
        V2_ASSIMILATION_RULE,
        V2_FROZEN_PROTOCOL_VERSION,
        V2_PREDICTION_ARTIFACT_SCHEMA_VERSION,
        FrozenV2PredictionArtifact,
        freeze_v2_prediction,
        load_frozen_v2_prediction,
    )
    from gbm_twin.workflows.provenance import (
        InputFileProvenance,
        PredictionProvenance,
        build_prediction_provenance,
        sha256_file,
        v2_calibration_config_sha256,
    )
    from gbm_twin.workflows.viewer import (
        ViewerPlane,
        ViewerPlaneMetadata,
        ViewerVolumeMetadata,
        clear_viewer_cache,
        get_viewer_volume_metadata,
        render_viewer_slice_png,
    )

_EXPORTS = {
    "COHORT_EVALUATION_SCHEMA_VERSION": (
        "gbm_twin.workflows.cohort_evaluation",
        "COHORT_EVALUATION_SCHEMA_VERSION",
    ),
    "COHORT_FREEZE_SCHEMA_VERSION": (
        "gbm_twin.workflows.cohort_freeze",
        "COHORT_FREEZE_SCHEMA_VERSION",
    ),
    "CohortEvaluationResult": ("gbm_twin.workflows.cohort_evaluation", "CohortEvaluationResult"),
    "CohortFreezeResult": ("gbm_twin.workflows.cohort_freeze", "CohortFreezeResult"),
    "DEFAULT_TARGET_SPACING": ("gbm_twin.workflows.patients", "DEFAULT_TARGET_SPACING"),
    "EligibilityIssue": ("gbm_twin.workflows.eligibility", "EligibilityIssue"),
    "EligibilityReason": ("gbm_twin.workflows.eligibility", "EligibilityReason"),
    "FrozenV2PredictionArtifact": ("gbm_twin.workflows.prediction", "FrozenV2PredictionArtifact"),
    "InputFileProvenance": ("gbm_twin.workflows.provenance", "InputFileProvenance"),
    "PatientCatalogSummary": ("gbm_twin.workflows.patient_catalog", "PatientCatalogSummary"),
    "PatientCatalogTimepoint": ("gbm_twin.workflows.patient_catalog", "PatientCatalogTimepoint"),
    "PatientEligibility": ("gbm_twin.workflows.eligibility", "PatientEligibility"),
    "PatientNotEligibleError": ("gbm_twin.workflows.patient_twin", "PatientNotEligibleError"),
    "PatientTreatmentSummary": ("gbm_twin.workflows.patient_catalog", "PatientTreatmentSummary"),
    "PatientTwinService": ("gbm_twin.workflows.patient_twin", "PatientTwinService"),
    "PredictionProvenance": ("gbm_twin.workflows.provenance", "PredictionProvenance"),
    "PredictionTarget": ("gbm_twin.workflows.contracts", "PredictionTarget"),
    "PreparedPatientTimepoint": ("gbm_twin.workflows.patients", "PreparedPatientTimepoint"),
    "V2CalibrationConfig": ("gbm_twin.workflows.calibration", "V2CalibrationConfig"),
    "V2CalibrationRun": ("gbm_twin.workflows.calibration", "V2CalibrationRun"),
    "V2_ALPHA_BETA_RATIO_GY": ("gbm_twin.workflows.calibration", "V2_ALPHA_BETA_RATIO_GY"),
    "V2_ASSIMILATION_RULE": ("gbm_twin.workflows.prediction", "V2_ASSIMILATION_RULE"),
    "V2_EFFECTIVE_ALPHA_PER_GY": ("gbm_twin.workflows.calibration", "V2_EFFECTIVE_ALPHA_PER_GY"),
    "V2_FROZEN_PROTOCOL_VERSION": ("gbm_twin.workflows.prediction", "V2_FROZEN_PROTOCOL_VERSION"),
    "V2_LATENT_WIDTH_MM": ("gbm_twin.workflows.calibration", "V2_LATENT_WIDTH_MM"),
    "V2_OBSERVATION_THRESHOLD": ("gbm_twin.workflows.calibration", "V2_OBSERVATION_THRESHOLD"),
    "V2_PREDICTION_ARTIFACT_SCHEMA_VERSION": (
        "gbm_twin.workflows.prediction",
        "V2_PREDICTION_ARTIFACT_SCHEMA_VERSION",
    ),
    "V2_SOFT_TEMPERATURE": ("gbm_twin.workflows.calibration", "V2_SOFT_TEMPERATURE"),
    "ViewerPlane": ("gbm_twin.workflows.viewer", "ViewerPlane"),
    "ViewerPlaneMetadata": ("gbm_twin.workflows.viewer", "ViewerPlaneMetadata"),
    "ViewerVolumeMetadata": ("gbm_twin.workflows.viewer", "ViewerVolumeMetadata"),
    "assess_patient_eligibility": ("gbm_twin.workflows.eligibility", "assess_patient_eligibility"),
    "build_prediction_provenance": ("gbm_twin.workflows.provenance", "build_prediction_provenance"),
    "calibrate_v2_interval": ("gbm_twin.workflows.calibration", "calibrate_v2_interval"),
    "clear_viewer_cache": ("gbm_twin.workflows.viewer", "clear_viewer_cache"),
    "discover_patient_ids": ("gbm_twin.workflows.patient_catalog", "discover_patient_ids"),
    "evaluate_frozen_cohort": ("gbm_twin.workflows.cohort_evaluation", "evaluate_frozen_cohort"),
    "freeze_cohort_from_configs": (
        "gbm_twin.workflows.cohort_freeze",
        "freeze_cohort_from_configs",
    ),
    "freeze_v2_prediction": ("gbm_twin.workflows.prediction", "freeze_v2_prediction"),
    "get_patient_catalog_summary": (
        "gbm_twin.workflows.patient_catalog",
        "get_patient_catalog_summary",
    ),
    "get_viewer_volume_metadata": ("gbm_twin.workflows.viewer", "get_viewer_volume_metadata"),
    "load_frozen_v2_prediction": ("gbm_twin.workflows.prediction", "load_frozen_v2_prediction"),
    "prepare_patient_timepoint": ("gbm_twin.workflows.patients", "prepare_patient_timepoint"),
    "render_viewer_slice_png": ("gbm_twin.workflows.viewer", "render_viewer_slice_png"),
    "sha256_file": ("gbm_twin.workflows.provenance", "sha256_file"),
    "v2_calibration_config_sha256": (
        "gbm_twin.workflows.provenance",
        "v2_calibration_config_sha256",
    ),
}

__all__ = [
    "DEFAULT_TARGET_SPACING",
    "EligibilityIssue",
    "EligibilityReason",
    "FrozenV2PredictionArtifact",
    "InputFileProvenance",
    "PatientCatalogSummary",
    "PatientCatalogTimepoint",
    "PatientEligibility",
    "PatientTreatmentSummary",
    "PredictionProvenance",
    "PredictionTarget",
    "PreparedPatientTimepoint",
    "V2_ALPHA_BETA_RATIO_GY",
    "V2_ASSIMILATION_RULE",
    "V2_EFFECTIVE_ALPHA_PER_GY",
    "V2_FROZEN_PROTOCOL_VERSION",
    "V2_LATENT_WIDTH_MM",
    "V2_OBSERVATION_THRESHOLD",
    "V2_PREDICTION_ARTIFACT_SCHEMA_VERSION",
    "V2_SOFT_TEMPERATURE",
    "V2CalibrationConfig",
    "V2CalibrationRun",
    "ViewerPlane",
    "ViewerPlaneMetadata",
    "ViewerVolumeMetadata",
    "assess_patient_eligibility",
    "build_prediction_provenance",
    "calibrate_v2_interval",
    "clear_viewer_cache",
    "discover_patient_ids",
    "freeze_v2_prediction",
    "get_patient_catalog_summary",
    "get_viewer_volume_metadata",
    "load_frozen_v2_prediction",
    "prepare_patient_timepoint",
    "render_viewer_slice_png",
    "sha256_file",
    "v2_calibration_config_sha256",
    "PatientNotEligibleError",
    "PatientTwinService",
    "COHORT_FREEZE_SCHEMA_VERSION",
    "CohortFreezeResult",
    "freeze_cohort_from_configs",
    "COHORT_EVALUATION_SCHEMA_VERSION",
    "CohortEvaluationResult",
    "evaluate_frozen_cohort",
]


def __getattr__(name: str) -> Any:
    try:
        module_name, symbol = _EXPORTS[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    value = getattr(import_module(module_name), symbol)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
