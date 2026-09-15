import {
  Brain,
  Layers3,
} from "lucide-react";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  fetchViewerMetadata,
  viewerSliceUrl,
} from "../api/client";

import type {
  PatientSummary,
  ViewerPlane,
  ViewerPlaneMetadata,
  ViewerVolumeMetadata,
} from "../api/types";

import AnatomicalWarningsPanel from "./AnatomicalWarningsPanel";
import ThreeDViewer from "./ThreeDViewer";
import TriPlanarViewer from "./TriPlanarViewer";


type MedicalViewerPanelProps = {
  patient: PatientSummary | null;
};


type ViewerMode =
  | "workstation"
  | "3d"
  | ViewerPlane;


type TimepointSelection = {
  patient: PatientSummary;
  timepointName: string;
};


type ModeSelection = {
  patient: PatientSummary;
  mode: ViewerMode;
};


type MetadataRequestState =
  | {
      patient: PatientSummary;
      timepointName: string;
      status: "success";
      metadata: ViewerVolumeMetadata;
    }
  | {
      patient: PatientSummary;
      timepointName: string;
      status: "error";
      error: string;
    };


const planes: ViewerPlane[] = [
  "axial",
  "coronal",
  "sagittal",
];


function isViewerPlane(
  mode: ViewerMode,
): mode is ViewerPlane {
  return (
    mode === "axial"
    || mode === "coronal"
    || mode === "sagittal"
  );
}


function MedicalViewerPanel({
  patient,
}: MedicalViewerPanelProps) {
  const [
    timepointSelection,
    setTimepointSelection,
  ] = useState<TimepointSelection | null>(
    null,
  );

  const [
    modeSelection,
    setModeSelection,
  ] = useState<ModeSelection | null>(
    null,
  );

  const [
    metadataRequest,
    setMetadataRequest,
  ] = useState<
    MetadataRequestState | null
  >(null);

  const [
    sliceIndex,
    setSliceIndex,
  ] = useState(
    0,
  );

  const [
    overlayGtv,
    setOverlayGtv,
  ] = useState(
    true,
  );

  const timepointNames =
    patient?.timepoints.map(
      (timepoint) =>
        timepoint.name,
    ) ?? [];

  const preferredTimepointName =
    timepointNames.includes("t1")
      ? "t1"
      : timepointNames[0] ?? "";

  const timepointName =
    patient !== null
    && timepointSelection?.patient
      === patient
    && timepointNames.includes(
      timepointSelection.timepointName,
    )
      ? timepointSelection.timepointName
      : preferredTimepointName;

  const mode =
    patient !== null
    && modeSelection?.patient
      === patient
      ? modeSelection.mode
      : "workstation";


  useEffect(() => {
    if (
      patient === null
      || !timepointName
    ) {
      return;
    }

    let cancelled = false;

    fetchViewerMetadata(
      patient.patient_id,
      timepointName,
    )
      .then(
        (result) => {
          if (cancelled) {
            return;
          }

          setMetadataRequest({
            patient,
            timepointName,
            status: "success",
            metadata: result,
          });

          const axial =
            result.planes.find(
              (item) =>
                item.name
                === "axial",
            );

          if (axial) {
            setSliceIndex(
              axial.default_index,
            );
          }
        },
      )
      .catch(
        (
          requestError:
            unknown,
        ) => {
          if (cancelled) {
            return;
          }

          setMetadataRequest({
            patient,
            timepointName,
            status: "error",
            error:
              requestError
                instanceof Error
                ? requestError.message
                : (
                  "Failed to load "
                  + "viewer metadata"
                ),
          });
        },
      );

    return () => {
      cancelled = true;
    };
  }, [
    patient,
    timepointName,
  ]);


  const currentMetadataRequest =
    patient !== null
    && metadataRequest?.patient
      === patient
    && metadataRequest.timepointName
      === timepointName
      ? metadataRequest
      : null;

  const metadata =
    currentMetadataRequest?.status
    === "success"
      ? currentMetadataRequest.metadata
      : null;

  const error =
    currentMetadataRequest?.status
    === "error"
      ? currentMetadataRequest.error
      : null;

  const loading =
    patient !== null
    && Boolean(timepointName)
    && currentMetadataRequest === null;


  const activePlane =
    isViewerPlane(
      mode,
    )
      ? mode
      : "axial";


  const planeMetadata =
    useMemo<
      ViewerPlaneMetadata | null
    >(
      () =>
        metadata?.planes.find(
          (item) =>
            item.name
            === activePlane,
        )
        ?? null,
      [
        metadata,
        activePlane,
      ],
    );


  const imageUrl =
    useMemo(
      () => {
        if (
          patient === null
          || metadata === null
          || planeMetadata
            === null
          || !isViewerPlane(
            mode,
          )
        ) {
          return null;
        }

        return viewerSliceUrl(
          patient.patient_id,
          timepointName,
          activePlane,
          sliceIndex,
          overlayGtv,
        );
      },
      [
        patient,
        metadata,
        planeMetadata,
        mode,
        timepointName,
        activePlane,
        sliceIndex,
        overlayGtv,
      ],
    );


  function changePlane(
    plane: ViewerPlane,
  ) {
    if (patient === null) {
      return;
    }

    setModeSelection({
      patient,
      mode: plane,
    });

    const target =
      metadata?.planes.find(
        (item) =>
          item.name
          === plane,
      );

    if (target) {
      setSliceIndex(
        target.default_index,
      );
    }
  }


  return (
    <section className="panel viewer-panel">
      <div className="panel-heading viewer-panel-heading">
        <div>
          <div className="section-eyebrow">
            Imaging
          </div>

          <h3>
            {
              patient
                ? (
                  `Patient ${patient.patient_id} `
                  + "Imaging Workstation"
                )
                : (
                  "Imaging Workstation"
                )
            }
          </h3>
        </div>


        <div className="viewer-heading-controls">
          <select
            className="viewer-timepoint-select"
            disabled={
              patient === null
            }
            value={
              timepointName
            }
            onChange={
              (event) => {
                if (patient === null) {
                  return;
                }

                setTimepointSelection({
                  patient,
                  timepointName:
                    event.target.value,
                });
              }
            }
          >
            {
              patient?.timepoints.map(
                (timepoint) => (
                  <option
                    key={
                      timepoint.name
                    }
                    value={
                      timepoint.name
                    }
                  >
                    {
                      timepoint
                        .name
                        .toUpperCase()
                    }
                  </option>
                ),
              )
            }
          </select>


          <div className="viewer-tabs">
            <button
              type="button"
              className={
                mode
                === "workstation"
                  ? "viewer-tab active"
                  : "viewer-tab"
              }
              disabled={
                patient === null
              }
              onClick={() => {
                if (patient === null) {
                  return;
                }

                setModeSelection({
                  patient,
                  mode: "workstation",
                });
              }}
            >
              Workstation
            </button>

            <button
              type="button"
              className={
                mode === "3d"
                  ? "viewer-tab active"
                  : "viewer-tab"
              }
              disabled={
                patient === null
              }
              onClick={() => {
                if (patient === null) {
                  return;
                }

                setModeSelection({
                  patient,
                  mode: "3d",
                });
              }}
            >
              3D
            </button>

            {
              planes.map(
                (plane) => (
                  <button
                    key={plane}
                    type="button"
                    className={
                      mode === plane
                        ? "viewer-tab active"
                        : "viewer-tab"
                    }
                    disabled={
                      patient === null
                    }
                    onClick={() =>
                      changePlane(
                        plane,
                      )
                    }
                  >
                    {
                      capitalize(
                        plane,
                      )
                    }
                  </button>
                ),
              )
            }
          </div>
        </div>
      </div>


      {
        patient === null
        || !timepointName
          ? (
            <div className="medical-viewer-stage">
              <ViewerEmptyState />
            </div>
          )
          : mode === "workstation"
            ? (
              <WorkstationMode
                patientId={
                  patient.patient_id
                }
                timepointName={
                  timepointName
                }
                metadata={
                  metadata
                }
                loading={
                  loading
                }
                error={
                  error
                }
                overlayGtv={
                  overlayGtv
                }
                onOverlayChange={
                  setOverlayGtv
                }
              />
            )
            : mode === "3d"
              ? (
                <div className="medical-viewer-stage">
                  <ThreeDViewer
                    patientId={
                      patient.patient_id
                    }
                    timepointName={
                      timepointName
                    }
                  />
                </div>
              )
              : (
                <SinglePlaneMode
                  patientId={
                    patient.patient_id
                  }
                  timepointName={
                    timepointName
                  }
                  plane={
                    activePlane
                  }
                  planeMetadata={
                    planeMetadata
                  }
                  metadata={
                    metadata
                  }
                  loading={
                    loading
                  }
                  error={
                    error
                  }
                  imageUrl={
                    imageUrl
                  }
                  sliceIndex={
                    sliceIndex
                  }
                  overlayGtv={
                    overlayGtv
                  }
                  onSliceChange={
                    setSliceIndex
                  }
                  onOverlayChange={
                    setOverlayGtv
                  }
                />
              )
      }
    </section>
  );
}


type WorkstationModeProps = {
  patientId: number;
  timepointName: string;

  metadata:
    ViewerVolumeMetadata | null;

  loading: boolean;
  error: string | null;

  overlayGtv: boolean;

  onOverlayChange: (
    value: boolean,
  ) => void;
};


function WorkstationMode({
  patientId,
  timepointName,
  metadata,
  loading,
  error,
  overlayGtv,
  onOverlayChange,
}: WorkstationModeProps) {
  if (loading) {
    return (
      <div className="workstation-loading">
        Loading MRI workstation…
      </div>
    );
  }

  if (error) {
    return (
      <div className="workstation-loading error">
        {error}
      </div>
    );
  }

  if (!metadata) {
    return (
      <div className="workstation-loading">
        Viewer metadata unavailable.
      </div>
    );
  }

  return (
    <>
      <div className="workstation-toolbar">
        <label className="viewer-overlay-toggle">
          <input
            type="checkbox"
            checked={
              overlayGtv
            }
            onChange={
              (event) =>
                onOverlayChange(
                  event
                    .target
                    .checked,
                )
            }
          />

          <span className="overlay-indicator" />

          <span>
            GTV overlay
          </span>
        </label>

        <div className="workstation-meta">
          <span>
            Spacing{" "}
            <strong>
              {
                formatSpacing(
                  metadata.spacing,
                )
              }
            </strong>
          </span>

          <span>
            GTV{" "}
            <strong>
              {
                metadata
                  .gtv_volume_cm3
                  .toFixed(2)
              }
              {" cm³"}
            </strong>
          </span>
        </div>
      </div>


      <div className="medical-workstation-grid">
        <TriPlanarViewer
          key={
            `${patientId}:${timepointName}`
          }
          patientId={
            patientId
          }
          timepointName={
            timepointName
          }
          metadata={
            metadata
          }
          overlayGtv={
            overlayGtv
          }
        />

        <AnatomicalWarningsPanel
          patientId={
            patientId
          }
          timepointName={
            timepointName
          }
        />
      </div>
    </>
  );
}


type SinglePlaneModeProps = {
  patientId: number;
  timepointName: string;

  plane: ViewerPlane;

  planeMetadata:
    ViewerPlaneMetadata | null;

  metadata:
    ViewerVolumeMetadata | null;

  loading: boolean;
  error: string | null;

  imageUrl: string | null;

  sliceIndex: number;
  overlayGtv: boolean;

  onSliceChange: (
    value: number,
  ) => void;

  onOverlayChange: (
    value: boolean,
  ) => void;
};


function SinglePlaneMode({
  timepointName,
  plane,
  planeMetadata,
  metadata,
  loading,
  error,
  imageUrl,
  sliceIndex,
  overlayGtv,
  onSliceChange,
  onOverlayChange,
}: SinglePlaneModeProps) {
  return (
    <>
      <div className="medical-viewer-stage">
        {
          loading
            ? (
              <div className="viewer-loading">
                Loading MRI volume…
              </div>
            )
            : error
              ? (
                <div className="viewer-error">
                  <strong>
                    Unable to load MRI
                  </strong>

                  <span>
                    {error}
                  </span>
                </div>
              )
              : imageUrl
                ? (
                  <>
                    <img
                      className="medical-viewer-image"
                      src={
                        imageUrl
                      }
                      alt={
                        `${timepointName} `
                        + `${plane} MRI `
                        + `slice ${sliceIndex}`
                      }
                      draggable={
                        false
                      }
                    />

                    <div className="viewer-image-badge">
                      <strong>
                        {
                          timepointName
                            .toUpperCase()
                        }
                      </strong>

                      <span>
                        {
                          capitalize(
                            plane,
                          )
                        }
                      </span>
                    </div>
                  </>
                )
                : (
                  <ViewerEmptyState />
                )
        }
      </div>


      {
        metadata
        && planeMetadata
        && (
          <div className="viewer-controls">
            <div className="slice-control">
              <div className="slice-control-header">
                <span>
                  Slice
                </span>

                <strong>
                  {sliceIndex}
                  {" / "}
                  {
                    planeMetadata
                      .max_index
                  }
                </strong>
              </div>

              <input
                type="range"
                min={0}
                max={
                  planeMetadata
                    .max_index
                }
                value={
                  sliceIndex
                }
                onChange={
                  (event) =>
                    onSliceChange(
                      Number(
                        event
                          .target
                          .value,
                      ),
                    )
                }
              />
            </div>


            <label className="viewer-overlay-toggle">
              <input
                type="checkbox"
                checked={
                  overlayGtv
                }
                onChange={
                  (event) =>
                    onOverlayChange(
                      event
                        .target
                        .checked,
                    )
                }
              />

              <span className="overlay-indicator" />

              <span>
                GTV overlay
              </span>
            </label>


            <div className="viewer-volume-info">
              <div>
                <span>
                  Spacing
                </span>

                <strong>
                  {
                    formatSpacing(
                      metadata.spacing,
                    )
                  }
                </strong>
              </div>

              <div>
                <span>
                  GTV volume
                </span>

                <strong>
                  {
                    metadata
                      .gtv_volume_cm3
                      .toFixed(2)
                  }
                  {" cm³"}
                </strong>
              </div>
            </div>
          </div>
        )
      }
    </>
  );
}


function ViewerEmptyState() {
  return (
    <div className="medical-viewer-empty">
      <div className="medical-viewer-empty-icon">
        <Brain
          size={52}
          strokeWidth={
            1.3
          }
        />

        <Layers3
          size={20}
          strokeWidth={
            1.5
          }
        />
      </div>

      <strong>
        Select a patient
      </strong>

      <span>
        MRI, GTV, latent tumor state
        and anatomical analysis will
        appear here.
      </span>
    </div>
  );
}


function capitalize(
  value: string,
): string {
  return (
    value.charAt(0)
      .toUpperCase()
    + value.slice(1)
  );
}


function formatSpacing(
  spacing: [
    number,
    number,
    number,
  ],
): string {
  return (
    spacing
      .map(
        (value) =>
          value.toFixed(1),
      )
      .join(" × ")
    + " mm"
  );
}


export default MedicalViewerPanel;
