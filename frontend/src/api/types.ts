export type HealthResponse = {
  status: string;
  service: string;
  version: string;
};


export type PatientListItem = {
  patient_id: number;
  label: string;
};


export type PatientListResponse = {
  patients: PatientListItem[];
};


export type PatientTimepoint = {
  name: string;
  days_from_baseline: number | null;

  gtv_available: boolean | null;
  gtv_type: string | null;

  rtdose_available: boolean | null;
};


export type PatientTreatment = {
  has_record: boolean;

  rt_start_day: number | null;
  rt_start_phase: string;

  rt_started_by_t1: boolean | null;
  rt_started_by_t2: boolean | null;

  dose_gy: number | null;
  fractions: number | null;

  reconstructable: boolean;
};


export type PatientSummary = {
  patient_id: number;

  timepoints: PatientTimepoint[];
  timepoint_count: number;

  dt01_days: number | null;
  dt12_days: number | null;

  treatment: PatientTreatment;
};


export type ViewerPlane =
  | "axial"
  | "coronal"
  | "sagittal";


export type ViewerPlaneMetadata = {
  name: ViewerPlane;

  size: number;
  max_index: number;
  default_index: number;

  image_width: number;
  image_height: number;
};


export type ViewerVolumeMetadata = {
  patient_id: number;
  timepoint_name: string;

  shape: [
    number,
    number,
    number,
  ];

  spacing: [
    number,
    number,
    number,
  ];

  intensity_low: number;
  intensity_high: number;

  gtv_voxels: number;
  gtv_volume_cm3: number;

  planes: ViewerPlaneMetadata[];
};


export type ViewerFocusMetadata = {
  patient_id: number;
  timepoint_name: string;

  axial_index: number | null;
  coronal_index: number | null;
  sagittal_index: number | null;

  gtv_voxels: number;
};


export type SurfaceMesh = {
  name: string;

  vertices: number[];
  triangles: number[];

  vertex_count: number;
  triangle_count: number;

  bounds: [
    number,
    number,
    number,
    number,
    number,
    number,
  ];
};


export type Viewer3DScene = {
  patient_id: number;
  timepoint_name: string;

  spacing: [
    number,
    number,
    number,
  ];

  latent_width_mm: number;
  latent_outer_level: number;
  latent_core_level: number;

  brain: SurfaceMesh;
  gtv: SurfaceMesh;

  latent_outer: SurfaceMesh;
  latent_core: SurfaceMesh;
};


export type AnatomicalSeverity =
  | "high"
  | "moderate";


export type AnatomicalWarning = {
  severity: AnatomicalSeverity;

  region_label: number;
  region_name: string;
  category: string;

  laterality: string | null;
  functional_note: string | null;

  observed_overlap_cm3: number;
  latent_overlap_cm3: number;

  min_observed_distance_mm:
    number | null;

  message: string;
};


export type AnatomicalRiskReport = {
  patient_id: number;
  timepoint_name: string;

  configured: boolean;

  atlas_name: string | null;
  status_message: string;

  latent_level: number;
  proximity_threshold_mm: number;

  high_count: number;
  moderate_count: number;

  warnings: AnatomicalWarning[];

  disclaimer: string;
};
