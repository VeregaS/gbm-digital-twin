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
                  : "Не удалось загрузить контроль качества",
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
                : "Не удалось загрузить цифровой двойник",
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
        className="workspace-state"
      >
        <strong>
          Загружаем цифровой двойник пациента {patient.patient_id}
        </strong>

        <span>
          Читаем зафиксированный прогноз, отложенную оценку и технический QC…
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
        className="workspace-state error"
      >
        <strong>
          Цифровой двойник недоступен
        </strong>

        <span>
          {currentRequest.error}
        </span>
      </section>
    );
  }

  return (
    <div
      className="twin-workspace"
    >
      <section
        className="twin-hero twin-patient-hero"
      >
        <div>
          <div
            className="twin-eyebrow"
          >
            <Activity
              size={15}
            />

            Зафиксированный прогноз V2
          </div>

          <h2>
            Цифровой двойник пациента {patient.patient_id}
          </h2>

          <p>
            Наблюдения t0 и t1 используются до прогнозирования. Модель строит прогноз состояния опухоли на t2, прогноз фиксируется, и только после этого он сравнивается с реальной опухолью на t2.
          </p>
        </div>

        <div
          className="twin-hero-actions"
        >
          <a
            className="twin-export-link"
            href={twinEvaluationJsonUrl}
            download
            title="Скачать исходную оценку cohort в JSON"
          >
            <Download
              size={14}
            />

            JSON
          </a>

          <a
            className="twin-export-link"
            href={twinEvaluationCsvUrl}
            download
            title="Скачать таблицу оценки cohort в CSV"
          >
            <Download
              size={14}
            />

            CSV
          </a>
        </div>
      </section>

      <nav
        className="twin-tabs"
        aria-label="Разделы цифрового двойника"
      >
        <TabButton
          label="Обзор"
          value="overview"
          active={tab}
          onChange={setTab}
        />

        <TabButton
          label="Динамика"
          value="timeline"
          active={tab}
          onChange={setTab}
        />

        <TabButton
          label="Сравнение"
          value="compare"
          active={tab}
          onChange={setTab}
        />

        <TabButton
          label={
            currentRequest.qc
            ?.warnings.length
              ? (
                `Контроль качества (${currentRequest.qc.warnings.length})`
              )
              : "Контроль качества"
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
            currentRequest.evaluation
          }
          cohort={
            currentRequest.cohort
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
          key={patient.patient_id}
          patientId={
            patient.patient_id
          }
          evaluation={
            currentRequest.evaluation
          }
          viewer={
            currentRequest.viewer
          }
        />
      )}

      {tab === "qc" && (
        <TwinQCTab
          qc={currentRequest.qc}
          error={
            currentRequest.qcError
          }
        />
      )}

      <div
        className="twin-research-note"
      >
        Только для исследовательского использования. Не является системой поддержки клинических решений.
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
          ? "twin-tab-button active"
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
