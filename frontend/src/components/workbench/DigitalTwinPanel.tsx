import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Activity,
  Box,
  Download,
  ScanLine,
} from "lucide-react";

import {
  fetchTwinCohort,
  fetchTwinEvaluations,
  fetchTwinPatient,
  fetchTwinPatients,
  fetchTwinViewerMetadata,
  twinEvaluationCsvUrl,
  twinEvaluationJsonUrl,
  twinSliceUrl,
} from "../../api/twin";

import type {
  TwinCohort,
  TwinMethodMetrics,
  TwinOverlayLayer,
  TwinPatientEvaluation,
  TwinPatientListItem,
} from "../../api/twin";

import type {
  ViewerPlane,
  ViewerVolumeMetadata,
} from "../../api/types";

import TwinCohortChart from "./TwinCohortChart";
import TwinThreeDViewer from "./TwinThreeDViewer";


type TwinPatientRequestState =
  | {
      patientId: number;
      status: "success";

      patient:
        TwinPatientEvaluation;

      viewer:
        ViewerVolumeMetadata;
    }
  | {
      patientId: number;
      status: "error";
      error: string;
    };


type ViewerMode =
  | "2d"
  | "3d";


const layers: {
  value: TwinOverlayLayer;
  label: string;
}[] = [
  {
    value: "twin",
    label: "Twin",
  },
  {
    value: "persistence",
    label: "Persistence",
  },
  {
    value: "volume_baseline",
    label: "Volume baseline",
  },
  {
    value: "observed",
    label: "Observed t2",
  },
];


const planes: ViewerPlane[] = [
  "axial",
  "coronal",
  "sagittal",
];


function formatMetric(
  value: number | null,
  digits = 3,
): string {
  if (value === null) {
    return "—";
  }

  return value.toFixed(
    digits,
  );
}


function DigitalTwinPanel() {
  const [
    cohort,
    setCohort,
  ] = useState<
    TwinCohort | null
  >(null);

  const [
    patients,
    setPatients,
  ] = useState<
    TwinPatientListItem[]
  >([]);

  const [
    cohortEvaluations,
    setCohortEvaluations,
  ] = useState<
    TwinPatientEvaluation[]
  >([]);

  const [
    selectedPatientId,
    setSelectedPatientId,
  ] = useState<
    number | null
  >(null);

  const [
    patientRequest,
    setPatientRequest,
  ] = useState<
    TwinPatientRequestState | null
  >(null);

  const [
    loading,
    setLoading,
  ] = useState(
    true,
  );

  const [
    error,
    setError,
  ] = useState<
    string | null
  >(null);

  const [
    viewerMode,
    setViewerMode,
  ] = useState<
    ViewerMode
  >(
    "2d",
  );

  const [
    layer,
    setLayer,
  ] = useState<
    TwinOverlayLayer
  >(
    "twin",
  );

  const [
    plane,
    setPlane,
  ] = useState<
    ViewerPlane
  >(
    "axial",
  );

  const [
    sliceIndex,
    setSliceIndex,
  ] = useState(
    0,
  );

  useEffect(() => {
    let cancelled = false;

    Promise.all([
      fetchTwinCohort(),
      fetchTwinPatients(),
      fetchTwinEvaluations(),
    ])
      .then(
        ([
          cohortData,
          patientData,
          evaluationsData,
        ]) => {
          if (cancelled) {
            return;
          }

          setCohort(
            cohortData,
          );

          setPatients(
            patientData.patients,
          );

          setCohortEvaluations(
            evaluationsData,
          );

          setError(
            null,
          );

          const firstPatient =
            patientData
            .patients[0];

          if (firstPatient) {
            setSelectedPatientId(
              firstPatient
              .patient_id,
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

          setError(
            requestError
              instanceof Error
                ? requestError.message
                : (
                  "Failed to load "
                  + "Digital Twin "
                  + "workspace"
                ),
          );
        },
      )
      .finally(() => {
        if (!cancelled) {
          setLoading(
            false,
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (
      selectedPatientId
      === null
    ) {
      return;
    }

    let cancelled = false;

    Promise.all([
      fetchTwinPatient(
        selectedPatientId,
      ),
      fetchTwinViewerMetadata(
        selectedPatientId,
      ),
    ])
      .then(
        ([
          patientData,
          viewerData,
        ]) => {
          if (cancelled) {
            return;
          }

          setPatientRequest({
            patientId:
              selectedPatientId,
            status: "success",
            patient:
              patientData,
            viewer:
              viewerData,
          });

          const axial =
            viewerData
            .planes
            .find(
              (item) =>
                item.name
                === "axial",
            );

          setPlane(
            "axial",
          );

          setSliceIndex(
            axial
            ?.default_index
            ?? 0,
          );
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

          setPatientRequest({
            patientId:
              selectedPatientId,
            status: "error",
            error:
              requestError
              instanceof Error
                ? requestError.message
                : (
                  "Failed to load "
                  + "patient twin"
                ),
          });
        },
      );

    return () => {
      cancelled = true;
    };
  }, [
    selectedPatientId,
  ]);

  const selectedPatientRequest =
    selectedPatientId !== null
    && (
      patientRequest
      ?.patientId
      === selectedPatientId
    )
      ? patientRequest
      : null;

  const patient =
    selectedPatientRequest?.status
    === "success"
      ? selectedPatientRequest
        .patient
      : null;

  const viewer =
    selectedPatientRequest?.status
    === "success"
      ? selectedPatientRequest
        .viewer
      : null;

  const patientLoading =
    selectedPatientId !== null
    && selectedPatientRequest
    === null;

  const patientError =
    selectedPatientRequest?.status
    === "error"
      ? selectedPatientRequest
        .error
      : null;

  const planeMetadata =
    useMemo(
      () =>
        viewer
        ?.planes
        .find(
          (item) =>
            item.name
            === plane,
        )
        ?? null,
      [
        viewer,
        plane,
      ],
    );

  if (loading) {
    return (
      <section
        className={
          "workspace-state"
        }
      >
        <strong>
          Loading Digital Twin
        </strong>

        <span>
          Reading sealed V2
          evaluation…
        </span>
      </section>
    );
  }

  if (
    error !== null
    || cohort === null
  ) {
    return (
      <section
        className={
          "workspace-state error"
        }
      >
        <strong>
          Digital Twin unavailable
        </strong>

        <span>
          {error
            ?? (
              "Sealed V2 evaluation "
              + "is unavailable."
            )}
        </span>
      </section>
    );
  }

  const diceDelta =
    cohort.twin.mean_dice
    !== null
    && (
      cohort.persistence
      .mean_dice
      !== null
    )
      ? (
        cohort.twin.mean_dice
        - cohort.persistence
        .mean_dice
      )
      : null;

  const imageUrl =
    selectedPatientId
    !== null
    && viewer !== null
      ? twinSliceUrl(
        selectedPatientId,
        layer,
        plane,
        sliceIndex,
      )
      : null;

  function changePlane(
    nextPlane: ViewerPlane,
  ) {
    setPlane(
      nextPlane,
    );

    const metadata =
      viewer
      ?.planes
      .find(
        (item) =>
          item.name
          === nextPlane,
      );

    setSliceIndex(
      metadata
      ?.default_index
      ?? 0,
    );
  }

  return (
    <div
      className={
        "twin-workspace"
      }
    >
      <section
        className="twin-hero"
      >
        <div>
          <div
            className={
              "twin-eyebrow"
            }
          >
            <Activity
              size={15}
            />

            Frozen V2 cohort
          </div>

          <h2>
            Patient-specific
            glioblastoma Digital Twin
          </h2>

          <p>
            Sealed t1 → t2
            predictions.
            Held-out t2 is used
            only after the cohort
            freeze for evaluation.
          </p>
        </div>

        <div
          className={
            "twin-hero-actions"
          }
        >
          <a
            className={
              "twin-export-link"
            }
            href={
              twinEvaluationJsonUrl
            }
            download
          >
            <Download
              size={14}
            />

            JSON
          </a>

          <a
            className={
              "twin-export-link"
            }
            href={
              twinEvaluationCsvUrl
            }
            download
          >
            <Download
              size={14}
            />

            CSV
          </a>
        </div>
      </section>

      <section
        className={
          "twin-summary-grid"
        }
      >
        <MetricCard
          label={
            "Twin mean Dice"
          }
          value={
            formatMetric(
              cohort.twin
              .mean_dice,
            )
          }
          emphasis
        />

        <MetricCard
          label={
            "Persistence "
            + "mean Dice"
          }
          value={
            formatMetric(
              cohort
              .persistence
              .mean_dice,
            )
          }
        />

        <MetricCard
          label={
            "Dice Δ vs "
            + "persistence"
          }
          value={
            diceDelta === null
              ? "—"
              : (
                diceDelta >= 0
                  ? (
                    "+"
                    + diceDelta
                    .toFixed(3)
                  )
                  : diceDelta
                    .toFixed(3)
              )
          }
        />

        <MetricCard
          label={
            "Twin mean HD95"
          }
          value={
            cohort.twin
            .mean_hd95_mm
            === null
              ? "—"
              : (
                cohort.twin
                .mean_hd95_mm
                .toFixed(1)
                + " mm"
              )
          }
        />
      </section>

      <section
        className={
          "twin-card"
        }
      >
        <div
          className={
            "twin-panel-heading"
          }
        >
          <div>
            <strong>
              Cohort Dice
            </strong>

            <span>
              Per-patient comparison
              across frozen methods
            </span>
          </div>
        </div>

        <TwinCohortChart
          patients={
            cohortEvaluations
          }
        />
      </section>

      <section
        className={
          "twin-card"
        }
      >
        <div
          className={
            "twin-panel-heading"
          }
        >
          <div>
            <strong>
              Provenance
            </strong>

            <span>
              Scientific artifact
              identity
            </span>
          </div>
        </div>

        <div
          className={
            "twin-provenance-grid"
          }
        >
          <ProvenanceItem
            label="Dataset"
            value={
              `${cohort.dataset.name} `
              + (
                `v${
                  cohort.dataset.version
                }`
              )
            }
          />

          <ProvenanceItem
            label="DOI"
            value={
              cohort.dataset.doi
            }
          />

          <ProvenanceItem
            label="Git commit"
            value={
              cohort.repository
              .commit_sha
              .slice(
                0,
                12,
              )
            }
          />

          <ProvenanceItem
            label="Source tree"
            value={
              cohort.repository
              .dirty
                ? "dirty"
                : "clean"
            }
          />

          <ProvenanceItem
            label="Evaluation schema"
            value={
              String(
                cohort.schema_version,
              )
            }
          />

          <ProvenanceItem
            label="Grid spacing"
            value={
              (
                cohort.target_spacing
                .map(
                  (value) =>
                    value.toFixed(1),
                )
                .join(" × ")
                + " mm"
              )
            }
          />
        </div>
      </section>

      <section
        className={
          "twin-main-grid"
        }
      >
        <aside
          className={
            "twin-patient-list"
          }
        >
          <div
            className={
              "twin-panel-heading"
            }
          >
            <div>
              <strong>
                Evaluated patients
              </strong>

              <span>
                {patients.length}
                {" "}
                sealed predictions
              </span>
            </div>
          </div>

          <div
            className={
              "twin-patient-scroll"
            }
          >
            {patients.map(
              (item) => (
                <button
                  key={
                    item.patient_id
                  }
                  type="button"
                  className={
                    selectedPatientId
                    === item.patient_id
                      ? (
                        "twin-patient-row "
                        + "active"
                      )
                      : (
                        "twin-patient-row"
                      )
                  }
                  onClick={() =>
                    setSelectedPatientId(
                      item.patient_id,
                    )
                  }
                >
                  <strong>
                    Patient
                    {" "}
                    {item.patient_id}
                  </strong>

                  <span>
                    {
                      item
                      .target_timepoint
                    }
                    {" · day "}
                    {
                      item
                      .target_day
                      .toFixed(0)
                    }
                  </span>
                </button>
              ),
            )}
          </div>

          <div
            className={
              "twin-outcome-strip"
            }
          >
            <span>
              <strong>
                {
                  cohort
                  .twin_better_than_persistence_count
                }
              </strong>

              better
            </span>

            <span>
              <strong>
                {
                  cohort
                  .twin_equal_to_persistence_count
                }
              </strong>

              equal
            </span>

            <span>
              <strong>
                {
                  cohort
                  .twin_worse_than_persistence_count
                }
              </strong>

              worse
            </span>
          </div>
        </aside>

        <div
          className={
            "twin-detail-stack"
          }
        >
          {patientLoading && (
            <section
              className={
                "twin-card"
              }
            >
              Loading patient twin…
            </section>
          )}

          {patientError
          !== null && (
            <section
              className={
                "twin-card "
                + "twin-error"
              }
            >
              {patientError}
            </section>
          )}

          {patient !== null && (
            <>
              <PatientComparison
                patient={patient}
              />

              <section
                className={
                  "twin-card"
                }
              >
                <div
                  className={
                    "twin-panel-heading"
                  }
                >
                  <div>
                    <strong>
                      Prediction viewer
                    </strong>

                    <span>
                      Observed t2
                      versus sealed
                      prediction
                    </span>
                  </div>

                  <div
                    className={
                      "twin-view-mode"
                    }
                  >
                    <button
                      type="button"
                      className={
                        viewerMode
                        === "2d"
                          ? (
                            "twin-chip "
                            + "active"
                          )
                          : "twin-chip"
                      }
                      onClick={() =>
                        setViewerMode(
                          "2d",
                        )
                      }
                    >
                      <ScanLine
                        size={13}
                      />

                      2D
                    </button>

                    <button
                      type="button"
                      className={
                        viewerMode
                        === "3d"
                          ? (
                            "twin-chip "
                            + "active"
                          )
                          : "twin-chip"
                      }
                      onClick={() =>
                        setViewerMode(
                          "3d",
                        )
                      }
                    >
                      <Box
                        size={13}
                      />

                      3D
                    </button>
                  </div>
                </div>

                {viewerMode
                === "3d" ? (
                  <div
                    className={
                      "twin-3d-frame"
                    }
                  >
                    <TwinThreeDViewer
                      patientId={
                        patient
                        .patient_id
                      }
                    />
                  </div>
                ) : (
                  <>
                    <div
                      className={
                        "twin-control-row"
                      }
                    >
                      {layers.map(
                        (item) => (
                          <button
                            key={
                              item.value
                            }
                            type="button"
                            className={
                              layer
                              === item.value
                                ? (
                                  "twin-chip "
                                  + "active"
                                )
                                : (
                                  "twin-chip"
                                )
                            }
                            onClick={() =>
                              setLayer(
                                item.value,
                              )
                            }
                          >
                            {item.label}
                          </button>
                        ),
                      )}
                    </div>

                    <div
                      className={
                        "twin-control-row"
                      }
                    >
                      {planes.map(
                        (item) => (
                          <button
                            key={item}
                            type="button"
                            className={
                              plane === item
                                ? (
                                  "twin-chip "
                                  + "active"
                                )
                                : (
                                  "twin-chip"
                                )
                            }
                            onClick={() =>
                              changePlane(
                                item,
                              )
                            }
                          >
                            {item}
                          </button>
                        ),
                      )}
                    </div>

                    {(
                      imageUrl !== null
                      && planeMetadata
                      !== null
                    ) ? (
                      <>
                        <div
                          className={
                            "twin-image-frame"
                          }
                        >
                          <img
                            src={imageUrl}
                            alt={
                              `${layer} `
                              + `${plane} `
                              + (
                                "slice "
                                + `${sliceIndex}`
                              )
                            }
                          />
                        </div>

                        <div
                          className={
                            "twin-slider-row"
                          }
                        >
                          <span>
                            0
                          </span>

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
                                setSliceIndex(
                                  Number(
                                    event
                                    .target
                                    .value,
                                  ),
                                )
                            }
                          />

                          <span>
                            {
                              planeMetadata
                              .max_index
                            }
                          </span>

                          <strong>
                            slice
                            {" "}
                            {sliceIndex}
                          </strong>
                        </div>
                      </>
                    ) : (
                      <div
                        className={
                          "twin-image-frame "
                          + "empty"
                        }
                      >
                        Viewer unavailable
                      </div>
                    )}
                  </>
                )}
              </section>
            </>
          )}
        </div>
      </section>

      <div
        className={
          "twin-research-note"
        }
      >
        Research use only.
        This interface is not
        clinical decision support.
      </div>
    </div>
  );
}


type MetricCardProps = {
  label: string;
  value: string;
  emphasis?: boolean;
};


function MetricCard({
  label,
  value,
  emphasis = false,
}: MetricCardProps) {
  return (
    <article
      className={
        emphasis
          ? (
            "twin-summary-card "
            + "emphasis"
          )
          : "twin-summary-card"
      }
    >
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>
    </article>
  );
}


type ProvenanceItemProps = {
  label: string;
  value: string;
};


function ProvenanceItem({
  label,
  value,
}: ProvenanceItemProps) {
  return (
    <div
      className={
        "twin-provenance-item"
      }
    >
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>
    </div>
  );
}


type PatientComparisonProps = {
  patient:
    TwinPatientEvaluation;
};


function PatientComparison({
  patient,
}: PatientComparisonProps) {
  return (
    <section
      className="twin-card"
    >
      <div
        className={
          "twin-panel-heading"
        }
      >
        <div>
          <strong>
            Patient
            {" "}
            {patient.patient_id}
          </strong>

          <span>
            Forecast target
            {" · "}
            {
              patient
              .target_timepoint
            }
            {" · day "}
            {
              patient
              .target_day
              .toFixed(0)
            }
          </span>
        </div>
      </div>

      <div
        className={
          "twin-table-wrap"
        }
      >
        <table
          className={
            "twin-metric-table"
          }
        >
          <thead>
            <tr>
              <th>
                Metric
              </th>

              <th>
                Twin
              </th>

              <th>
                Persistence
              </th>

              <th>
                Volume baseline
              </th>
            </tr>
          </thead>

          <tbody>
            <MetricRow
              label="Dice"
              metric="dice"
              patient={patient}
            />

            <MetricRow
              label={
                "Relative "
                + "volume error"
              }
              metric={
                "relative_volume_error"
              }
              patient={patient}
            />

            <MetricRow
              label="HD95"
              metric="hd95_mm"
              patient={patient}
              suffix=" mm"
            />

            <MetricRow
              label={
                "Centroid distance"
              }
              metric={
                "centroid_distance_mm"
              }
              patient={patient}
              suffix=" mm"
            />
          </tbody>
        </table>
      </div>
    </section>
  );
}


type NumericMetric =
  keyof TwinMethodMetrics;


type MetricRowProps = {
  label: string;

  metric:
    NumericMetric;

  patient:
    TwinPatientEvaluation;

  suffix?: string;
};


function MetricRow({
  label,
  metric,
  patient,
  suffix = "",
}: MetricRowProps) {
  function value(
    method:
      TwinMethodMetrics,
  ): string {
    const raw =
      method[metric];

    if (raw === null) {
      return "—";
    }

    return (
      raw.toFixed(3)
      + suffix
    );
  }

  return (
    <tr>
      <td>
        {label}
      </td>

      <td
        className={
          "twin-value"
        }
      >
        {value(
          patient.twin,
        )}
      </td>

      <td>
        {value(
          patient.persistence,
        )}
      </td>

      <td>
        {value(
          patient
          .volume_baseline,
        )}
      </td>
    </tr>
  );
}


export default DigitalTwinPanel;