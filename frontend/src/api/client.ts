import type {
  AnatomicalRiskReport,
  HealthResponse,
  PatientListResponse,
  PatientSummary,
  Viewer3DScene,
  ViewerPlane,
  ViewerVolumeMetadata,
} from "./types";


async function requestJson<T>(
  path: string,
): Promise<T> {
  const response = await fetch(
    path,
  );

  if (!response.ok) {
    let detail =
      `Request failed: HTTP ${response.status}`;

    try {
      const payload: unknown =
        await response.json();

      if (
        typeof payload === "object"
        && payload !== null
        && "detail" in payload
      ) {
        const responseDetail = (
          payload as {
            detail?: unknown;
          }
        ).detail;

        if (
          typeof responseDetail
          === "string"
        ) {
          detail =
            responseDetail;
        }
      }
    } catch {
      // Keep fallback HTTP error.
    }

    throw new Error(
      detail,
    );
  }

  return (
    await response.json()
  ) as T;
}


export function fetchHealth():
Promise<HealthResponse> {
  return requestJson<
    HealthResponse
  >(
    "/api/health",
  );
}


export function fetchPatients():
Promise<PatientListResponse> {
  return requestJson<
    PatientListResponse
  >(
    "/api/patients",
  );
}


export function fetchPatient(
  patientId: number,
): Promise<PatientSummary> {
  return requestJson<
    PatientSummary
  >(
    `/api/patients/${patientId}`,
  );
}


export function fetchViewerMetadata(
  patientId: number,
  timepointName: string,
): Promise<ViewerVolumeMetadata> {
  return requestJson<
    ViewerVolumeMetadata
  >(
    (
      `/api/patients/${patientId}`
      + `/viewer/${timepointName}`
    ),
  );
}


export function viewerSliceUrl(
  patientId: number,
  timepointName: string,
  plane: ViewerPlane,
  index: number,
  overlayGtv: boolean,
): string {
  const query =
    new URLSearchParams({
      plane,
      index: String(
        index,
      ),
      overlay_gtv: String(
        overlayGtv,
      ),
    });

  return (
    `/api/patients/${patientId}`
    + `/viewer/${timepointName}/slice`
    + `?${query.toString()}`
  );
}


export function fetchViewer3DScene(
  patientId: number,
  timepointName: string,
): Promise<Viewer3DScene> {
  return requestJson<
    Viewer3DScene
  >(
    (
      `/api/patients/${patientId}`
      + `/viewer/${timepointName}`
      + "/scene3d"
    ),
  );
}


export function fetchAnatomicalRisk(
  patientId: number,
  timepointName: string,
): Promise<AnatomicalRiskReport> {
  return requestJson<
    AnatomicalRiskReport
  >(
    (
      `/api/patients/${patientId}`
      + `/anatomy/${timepointName}`
    ),
  );
}