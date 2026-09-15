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
    timepointName,
    setTimepointName,
  ] = useState("");

  const [
    mode,
    setMode,
  ] = useState<ViewerMode>(
    "workstation",
  );

  const [
    metadata,
    setMetadata,
  ] = useState<
    ViewerVolumeMetadata | null
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

  const [
    loading,
    setLoading,
  ] = useState(
    false,
  );

  const [
    error,
    setError,
  ] = useState<
    string | null
  >(
    null,
  );


  useEffect(() => {
    if (
      patient === null
    ) {
      setTimepointName(
        "",
      );

      setMetadata(
        null,
      );

      setError(
        null,
      );

      setMode(
        "workstation",
      );

      return;
    }

    const names =
      patient.timepoints.map(
        (timepoint) =>
          timepoint.name,
      );

    const preferred =
      names.includes("t1")
        ? "t1"
        : names[0] ?? "";

    setTimepointName(
      preferred,
    );

    setMode(
      "workstation",
    );
  }, [
    patient,
  ]);


  useEffect(() => {
    if (
      patient === null
      || !timepointName
    ) {
      setMetadata(
        null,
      );

      return;
    }

    let cancelled = false;

    setLoading(
      true,
    );

    setError(
      null,
    );

    fetchViewerMetadata(
      patient.patient_id,
      timepointName,
    )
      .then(
        (result) => {
          if (cancelled) {
            return;
          }

          setMetadata(
            result,
          );

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

          setMetadata(
            null,
          );

          setError(
            requestError
              instanceof Error
              ? requestError.message
              : (
                "Failed to load "
                + "viewer metadata"
              ),
          );
        },
      )
      .finally(
        () => {
          if (!cancelled) {
            setLoading(
              false,
            );
          }
        },
      );

    return () => {
      cancelled = true;
    };
  }, [
    patient,
    timepointName,
  ]);


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
    setMode(
      plane,
    );

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
              (event) =>
                setTimepointName(
                  event
                    .target
                    .value,
                )
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
              onClick={() =>
                setMode(
                  "workstation",
                )
              }
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
              onClick={() =>
                setMode(
                  "3d",
                )
              }
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