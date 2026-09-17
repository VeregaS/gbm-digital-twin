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


export type TwinOverlayLayer =
  | "twin"
  | "persistence"
  | "volume_baseline"
  | "observed";


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


export const twinEvaluationJsonUrl =
  "/api/twin/export/evaluation.json";


export const twinEvaluationCsvUrl =
  "/api/twin/export/evaluation.csv";


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