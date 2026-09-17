import {
  requestJson,
} from "./client";

import type {
  SurfaceMesh,
  ViewerPlane,
  ViewerVolumeMetadata,
} from "./types";


export type TwinMethodMetrics = {
  dice: number;

  relative_volume_error:
    number;

  hd95_mm:
    number | null;

  centroid_distance_mm:
    number | null;
};


export type TwinPatientEvaluation = {
  patient_id: number;

  target_timepoint: string;
  target_day: number;

  twin: TwinMethodMetrics;

  persistence:
    TwinMethodMetrics;

  volume_baseline:
    TwinMethodMetrics;
};


export type TwinPatientListItem = {
  patient_id: number;

  target_timepoint: string;
  target_day: number;
};


export type TwinPatientListResponse = {
  patients:
    TwinPatientListItem[];
};


export type TwinMethodSummary = {
  patient_count: number;

  hd95_count: number;

  centroid_distance_count:
    number;

  mean_dice:
    number | null;

  mean_relative_volume_error:
    number | null;

  mean_hd95_mm:
    number | null;

  mean_centroid_distance_mm:
    number | null;
};


export type TwinCohort = {
  schema_version: number;

  dataset: {
    name: string;
    version: number;
    doi: string;
  };

  repository: {
    commit_sha: string;
    dirty: boolean;
  };

  target_spacing:
    number[];

  patient_count: number;

  twin:
    TwinMethodSummary;

  persistence:
    TwinMethodSummary;

  volume_baseline:
    TwinMethodSummary;

  twin_better_than_persistence_count:
    number;

  twin_equal_to_persistence_count:
    number;

  twin_worse_than_persistence_count:
    number;
};


export type TwinPredictionMethod =
  | "twin"
  | "persistence"
  | "volume_baseline";


export type TwinOverlayLayer =
  | TwinPredictionMethod
  | "observed";


export type TwinComparisonMode =
  | "overlay"
  | "difference";


export type Twin3DScene = {
  patient_id: number;
  timepoint_name: string;

  spacing: [
    number,
    number,
    number,
  ];

  brain: SurfaceMesh;
  observed: SurfaceMesh;

  twin: SurfaceMesh;
  persistence: SurfaceMesh;

  volume_baseline:
    SurfaceMesh;
};


export type TwinMaskQC = {
  name: string;

  voxel_count: number;
  volume_cm3: number;

  component_count: number;

  largest_component_fraction:
    number | null;

  outside_brain_voxels:
    number;

  outside_brain_fraction:
    number | null;

  centroid_inside_brain:
    boolean | null;
};


export type TwinQCWarning = {
  code: string;
  message: string;
};


export type TwinPatientQC = {
  patient_id: number;

  observed: TwinMaskQC;
  twin: TwinMaskQC;
  persistence: TwinMaskQC;

  volume_baseline:
    TwinMaskQC;

  warnings:
    TwinQCWarning[];
};


export type TwinAnalysisTrajectory =
  | "growth"
  | "stable"
  | "regression"
  | "unknown";


export type TwinCorrelation = {
  count: number;
  pearson: number | null;
  spearman: number | null;
};


export type TwinTrajectoryGroup = {
  trajectory: TwinAnalysisTrajectory;
  patient_count: number;
  mean_twin_dice: number | null;
  mean_delta_vs_persistence: number | null;
  mean_hd95_mm: number | null;
};


export type TwinCohortErrorSummary = {
  patient_count: number;

  mean_twin_dice: number | null;
  median_twin_dice: number | null;

  mean_delta_vs_persistence: number | null;
  median_delta_vs_persistence: number | null;

  mean_delta_vs_volume_baseline: number | null;
  median_delta_vs_volume_baseline: number | null;

  twin_better_than_persistence_count: number;
  twin_equal_to_persistence_count: number;
  twin_worse_than_persistence_count: number;

  twin_better_than_volume_baseline_count: number;
  twin_equal_to_volume_baseline_count: number;
  twin_worse_than_volume_baseline_count: number;

  qc_flagged_count: number;
  calibration_non_identifiable_count: number;
  calibration_boundary_count: number;

  worst_twin_dice_patient_ids: number[];
  worst_delta_vs_persistence_patient_ids: number[];

  forecast_horizon_vs_twin_dice: TwinCorrelation;
  volume_change_t1_t2_vs_twin_dice: TwinCorrelation;
  calibration_dice_vs_twin_dice: TwinCorrelation;

  trajectory_groups: TwinTrajectoryGroup[];
};


export type TwinCohortPatientError = {
  patient_id: number;

  calibration_days: number | null;
  forecast_horizon_days: number | null;
  target_day: number;

  rt_start_day: number | null;
  rt_started_by_t1: boolean | null;
  treatment_reconstructable: boolean;

  volume_t0_cm3: number;
  volume_t1_cm3: number;
  volume_t2_cm3: number;

  volume_change_t0_t1: number | null;
  volume_change_t1_t2: number | null;

  trajectory_t0_t1: TwinAnalysisTrajectory;
  trajectory_t1_t2: TwinAnalysisTrajectory;

  diffusion: number;
  proliferation: number;

  calibration_dice: number;
  calibration_volume_error: number;
  calibration_loss: number;

  calibration_identifiable: boolean;
  diffusion_at_boundary: boolean;
  proliferation_at_boundary: boolean;

  twin_dice: number;
  twin_volume_error: number;
  twin_hd95_mm: number | null;
  twin_centroid_distance_mm: number | null;

  persistence_dice: number;
  persistence_volume_error: number;

  volume_baseline_dice: number;
  volume_baseline_volume_error: number;

  twin_minus_persistence_dice: number;
  twin_minus_volume_baseline_dice: number;

  qc_warning_codes: string[];

  observed_outside_brain_fraction: number | null;
  twin_outside_brain_fraction: number | null;

  observed_component_count: number;
  twin_component_count: number;

  observed_largest_component_fraction: number | null;
  twin_largest_component_fraction: number | null;
};


export type TwinCohortAnalysis = {
  schema_version: number;
  kind: string;
  sealed: boolean;

  source_evaluation_sha256: string;
  source_freeze_manifest_sha256: string;
  analysis_config_sha256: string;

  dataset: {
    name: string;
    version: number;
    doi: string;
  };

  repository: {
    commit_sha: string;
    dirty: boolean;
  };

  analysis_config: {
    stable_volume_change_fraction: number;
    worst_patient_count: number;
    min_correlation_patients: number;
  };

  summary: TwinCohortErrorSummary;
  patients: TwinCohortPatientError[];
};


export const twinEvaluationJsonUrl =
  "/api/twin/export/evaluation.json";


export const twinEvaluationCsvUrl =
  "/api/twin/export/evaluation.csv";


export const twinAnalysisJsonUrl =
  "/api/twin/analysis/export.json";


export const twinAnalysisCsvUrl =
  "/api/twin/analysis/export.csv";


export function fetchTwinCohort():
Promise<TwinCohort> {
  return requestJson<TwinCohort>(
    "/api/twin/cohort",
  );
}


export function fetchTwinEvaluations():
Promise<TwinPatientEvaluation[]> {
  return requestJson<
    TwinPatientEvaluation[]
  >(
    "/api/twin/evaluations",
  );
}


export function fetchTwinPatients():
Promise<TwinPatientListResponse> {
  return requestJson<
    TwinPatientListResponse
  >(
    "/api/twin/patients",
  );
}


export function fetchTwinPatient(
  patientId: number,
): Promise<TwinPatientEvaluation> {
  return requestJson<
    TwinPatientEvaluation
  >(
    `/api/twin/patients/${patientId}`,
  );
}


export function fetchTwinViewerMetadata(
  patientId: number,
): Promise<ViewerVolumeMetadata> {
  return requestJson<
    ViewerVolumeMetadata
  >(
    (
      `/api/twin/patients/${patientId}`
      + "/viewer"
    ),
  );
}


export function fetchTwin3DScene(
  patientId: number,
): Promise<Twin3DScene> {
  return requestJson<
    Twin3DScene
  >(
    (
      `/api/twin/patients/${patientId}`
      + "/scene3d"
    ),
  );
}


export function fetchTwinQC(
  patientId: number,
): Promise<TwinPatientQC> {
  return requestJson<
    TwinPatientQC
  >(
    (
      `/api/twin/patients/${patientId}`
      + "/qc"
    ),
  );
}


export function fetchTwinCohortAnalysis():
Promise<TwinCohortAnalysis> {
  return requestJson<
    TwinCohortAnalysis
  >(
    "/api/twin/analysis",
  );
}


export function twinSliceUrl(
  patientId: number,
  layer: TwinOverlayLayer,
  plane: ViewerPlane,
  index: number,
): string {
  const query =
    new URLSearchParams({
      layer,
      plane,
      index: String(index),
    });

  return (
    `/api/twin/patients/${patientId}`
    + `/slice?${query.toString()}`
  );
}


export function twinCompareSliceUrl(
  patientId: number,
  method: TwinPredictionMethod,
  mode: TwinComparisonMode,
  plane: ViewerPlane,
  index: number,
): string {
  const query =
    new URLSearchParams({
      method,
      mode,
      plane,
      index: String(index),
    });

  return (
    `/api/twin/patients/${patientId}`
    + `/compare-slice?${query.toString()}`
  );
}
