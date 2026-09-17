import {
  useEffect,
  useState,
} from "react";

import {
  Activity,
  Download,
} from "lucide-react";

import {
  fetchTwinCohort,
  fetchTwinPatient,
  fetchTwinQC,
  fetchTwinViewerMetadata,
  twinEvaluationCsvUrl,
  twinEvaluationJsonUrl,
} from "../../api/twin";

import type {
  TwinCohort,
  TwinPatientEvaluation,
  TwinPatientQC,
} from "../../api/twin";

import type {
  PatientSummary,
  ViewerVolumeMetadata,
} from "../../api/types";

import TwinCompareTab from "./TwinCompareTab";
import TwinOverviewTab from "./TwinOverviewTab";
import TwinQCTab from "./TwinQCTab";
import TwinTimelineTab from "./TwinTimelineTab";


type TwinTab =
  | "overview"
  | "timeline"
  | "compare"
  | "qc";


type QCResult = {
  qc:
    TwinPatientQC | null;

  error:
    string | null;
};


type RequestState =
  | {
      patientId: number;
      status: "success";

      evaluation:
        TwinPatientEvaluation;

      viewer:
        ViewerVolumeMetadata;

      cohort:
        TwinCohort;

      qc:
        TwinPatientQC | null;

      qcError:
        string | null;
    }
  | {
      patientId: number;
      status: "error";
      error: string;
    };


type DigitalTwinPanelProps = {
  patient:
    PatientSummary;
};


function DigitalTwinPanel({
  patient,
}: DigitalTwinPanelProps) {
  const [
    tab,
    setTab,
  ] = useState<
    TwinTab
  >(
    "overview",
  );

  const [
    request,
    setRequest,
  ] = useState<
    RequestState | null
  >(null);

  useEffect(() => {
    let cancelled = false;

    const qcPromise:
      Promise<QCResult> =
        fetchTwinQC(
          patient.patient_id,
        )
          .then(
            (qc) => ({
              qc,
              error: null,
            }),
          )
          .catch(
            (
              requestError:
                unknown,
            ) => ({
              qc: null,
              error:
                requestError
                instanceof Error
                  ? requestError.message
                  : (
                    "Failed to "
                    + "load QC"
                  ),
            }),
          );

    Promise.all([
      fetchTwinPatient(
        patient.patient_id,
      ),
      fetchTwinViewerMetadata(
        patient.patient_id,
      ),
      fetchTwinCohort(),
      qcPromise,
    ])
      .then(
        ([
          evaluation,
          viewer,
          cohort,
          qcResult,
        ]) => {
          if (cancelled) {
            return;
          }

          setRequest({
            patientId:
              patient.patient_id,
            status: "success",
            evaluation,
            viewer,
            cohort,
            qc:
              qcResult.qc,
            qcError:
              qcResult.error,
          });
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

          setRequest({
            patientId:
              patient.patient_id,
            status: "error",
            error:
              requestError
              instanceof Error
                ? requestError.message
                : (
                  "Failed to load "
                  + "Digital Twin"
                ),
          });
        },
      );

    return () => {
      cancelled = true;
    };
  }, [
    patient.patient_id,
  ]);

  const currentRequest =
    request?.patientId
    === patient.patient_id
      ? request
      : null;

  if (
    currentRequest === null
  ) {
    return (
      <section
        className={
          "workspace-state"
        }
      >
        <strong>
          Loading Patient
          {" "}
          {patient.patient_id}
          {" "}
          Digital Twin
        </strong>

        <span>
          Reading sealed prediction,
          held-out evaluation and QC…
        </span>
      </section>
    );
  }

  if (
    currentRequest.status
    === "error"
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
          {
            currentRequest.error
          }
        </span>
      </section>
    );
  }

  return (
    <div
      className={
        "twin-workspace"
      }
    >
      <section
        className={
          "twin-hero "
          + "twin-patient-hero"
        }
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

            Sealed V2 prediction
          </div>

          <h2>
            Patient
            {" "}
            {patient.patient_id}
            {" "}
            Digital Twin
          </h2>

          <p>
            t0 and t1 are used
            before forecasting.
            The model predicts t2,
            then the sealed forecast
            is compared with the
            held-out observed t2.
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

      <nav
        className={
          "twin-tabs"
        }
        aria-label={
          "Digital Twin sections"
        }
      >
        <TabButton
          label="Overview"
          value="overview"
          active={tab}
          onChange={setTab}
        />

        <TabButton
          label="Timeline"
          value="timeline"
          active={tab}
          onChange={setTab}
        />

        <TabButton
          label="Compare"
          value="compare"
          active={tab}
          onChange={setTab}
        />

        <TabButton
          label={
            currentRequest.qc
            ?.warnings.length
              ? (
                `QC (${
                  currentRequest
                  .qc
                  .warnings
                  .length
                })`
              )
              : "QC"
          }
          value="qc"
          active={tab}
          onChange={setTab}
        />
      </nav>

      {tab === "overview" && (
        <TwinOverviewTab
          patient={patient}
          evaluation={
            currentRequest
            .evaluation
          }
          cohort={
            currentRequest
            .cohort
          }
        />
      )}

      {tab === "timeline" && (
        <TwinTimelineTab
          patient={patient}
        />
      )}

      {tab === "compare" && (
        <TwinCompareTab
          key={
            patient.patient_id
          }
          patientId={
            patient.patient_id
          }
          evaluation={
            currentRequest
            .evaluation
          }
          viewer={
            currentRequest
            .viewer
          }
        />
      )}

      {tab === "qc" && (
        <TwinQCTab
          qc={
            currentRequest.qc
          }
          error={
            currentRequest
            .qcError
          }
        />
      )}

      <div
        className={
          "twin-research-note"
        }
      >
        Research use only.
        Not clinical decision support.
      </div>
    </div>
  );
}


type TabButtonProps = {
  label: string;
  value: TwinTab;
  active: TwinTab;

  onChange: (
    value: TwinTab,
  ) => void;
};


function TabButton({
  label,
  value,
  active,
  onChange,
}: TabButtonProps) {
  return (
    <button
      type="button"
      className={
        active === value
          ? (
            "twin-tab-button "
            + "active"
          )
          : "twin-tab-button"
      }
      onClick={() =>
        onChange(value)
      }
    >
      {label}
    </button>
  );
}


export default DigitalTwinPanel;