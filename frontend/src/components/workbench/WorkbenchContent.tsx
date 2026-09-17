import type {
  Capabilities,
} from "../../api/capabilities";

import type {
  PatientListItem,
  PatientSummary,
} from "../../api/types";

import MedicalViewerPanel from "../MedicalViewerPanel";

import type {
  WorkbenchSection,
} from "../layout/navigation";

import DigitalTwinPanel from "./DigitalTwinPanel";
import PatientContextBar from "./PatientContextBar";
import PatientDetails from "./PatientDetails";
import PatientMetrics from "./PatientMetrics";
import PatientToolbar from "./PatientToolbar";
import TimelinePanel from "./TimelinePanel";


type WorkbenchContentProps = {
  section:
    WorkbenchSection;

  capabilities:
    Capabilities | null;

  capabilitiesError:
    string | null;

  patients:
    PatientListItem[];

  selectedPatientId:
    number | null;

  selectedPatientHasTwin:
    boolean | null;

  twinPatientsError:
    string | null;

  patient:
    PatientSummary | null;

  patientsLoading:
    boolean;

  patientLoading:
    boolean;

  patientError:
    string | null;

  onSelectPatient: (
    patientId: number | null,
  ) => void;

  onChangePatient:
    () => void;

  onOpenViewer:
    () => void;
};


function WorkbenchContent({
  section,
  capabilities,
  capabilitiesError,
  patients,
  selectedPatientId,
  selectedPatientHasTwin,
  twinPatientsError,
  patient,
  patientsLoading,
  patientLoading,
  patientError,
  onSelectPatient,
  onChangePatient,
  onOpenViewer,
}: WorkbenchContentProps) {
  if (
    capabilitiesError !== null
  ) {
    return (
      <WorkspaceState
        title="Не удалось получить возможности сервера"
        message={capabilitiesError}
        error
      />
    );
  }

  if (
    capabilities === null
  ) {
    return (
      <WorkspaceState
        title="Проверяем рабочее пространство"
        message="Получаем доступные функции от сервера…"
      />
    );
  }

  if (
    section === "patients"
  ) {
    if (
      !capabilities
      .patients
      .available
    ) {
      return (
        <WorkspaceState
          title="Пациенты недоступны"
          message={
            capabilities
            .patients
            .reason
            ?? "Набор данных пациентов недоступен."
          }
        />
      );
    }

    return (
      <>
        <PatientToolbar
          patients={patients}
          selectedPatientId={
            selectedPatientId
          }
          patient={patient}
          patientsLoading={
            patientsLoading
          }
          patientLoading={
            patientLoading
          }
          error={
            patientError
          }
          onSelectPatient={
            onSelectPatient
          }
          onOpenViewer={
            onOpenViewer
          }
        />

        <PatientMetrics
          patient={patient}
        />

        <PatientDetails
          patient={patient}
          hasTwin={
            selectedPatientHasTwin
          }
        />

        <TimelinePanel
          patient={patient}
        />
      </>
    );
  }

  if (
    selectedPatientId === null
  ) {
    return (
      <WorkspaceState
        title="Сначала выберите пациента"
        message={
          "Разделы «Цифровой двойник» и «МРТ» работают для конкретного пациента. "
          + "Выберите пациента в разделе «Пациенты»."
        }
      />
    );
  }

  if (patientLoading) {
    return (
      <WorkspaceState
        title={
          `Загрузка пациента ${selectedPatientId}`
        }
        message="Читаем продольные данные пациента…"
      />
    );
  }

  if (
    patientError !== null
  ) {
    return (
      <WorkspaceState
        title="Данные пациента недоступны"
        message={patientError}
        error
      />
    );
  }

  if (patient === null) {
    return (
      <WorkspaceState
        title="Данные пациента недоступны"
        message="Не удалось загрузить данные выбранного пациента."
      />
    );
  }

  if (
    section === "digital_twin"
  ) {
    if (
      !capabilities
      .digital_twin
      .available
    ) {
      return (
        <WorkspaceState
          title="Цифровой двойник недоступен"
          message={
            capabilities
            .digital_twin
            .reason
            ?? "Цифровой двойник недоступен."
          }
        />
      );
    }

    if (
      twinPatientsError !== null
    ) {
      return (
        <WorkspaceState
          title="Цифровой двойник недоступен"
          message={twinPatientsError}
          error
        />
      );
    }

    if (
      selectedPatientHasTwin
      === null
    ) {
      return (
        <WorkspaceState
          title="Проверяем цифровой двойник"
          message="Проверяем наличие зафиксированного прогноза V2 для пациента…"
        />
      );
    }

    if (
      !selectedPatientHasTwin
    ) {
      return (
        <WorkspaceState
          title="Зафиксированный прогноз отсутствует"
          message={
            `Пациент ${patient.patient_id} не входит в sealed V2 cohort и не имеет доступной оценки прогноза.`
          }
        />
      );
    }

    return (
      <>
        <PatientContextBar
          patient={patient}
          onChangePatient={
            onChangePatient
          }
        />

        <DigitalTwinPanel
          patient={patient}
        />
      </>
    );
  }

  if (
    section === "viewer"
  ) {
    if (
      !capabilities
      .viewer
      .available
    ) {
      return (
        <WorkspaceState
          title="МРТ недоступно"
          message={
            capabilities
            .viewer
            .reason
            ?? "Просмотр МРТ недоступен."
          }
        />
      );
    }

    return (
      <>
        <PatientContextBar
          patient={patient}
          onChangePatient={
            onChangePatient
          }
        />

        <MedicalViewerPanel
          patient={patient}
        />
      </>
    );
  }

  if (
    !capabilities
    .anatomy
    .available
  ) {
    return (
      <WorkspaceState
        title="Анатомический анализ недоступен"
        message={
          capabilities
          .anatomy
          .reason
          ?? "Анатомический анализ недоступен."
        }
      />
    );
  }

  return (
    <>
      <PatientContextBar
        patient={patient}
        onChangePatient={
          onChangePatient
        }
      />

      <div
        className="experimental-banner"
      >
        <strong>
          Экспериментальная исследовательская функция
        </strong>

        <span>
          Предупреждения на основе атласа не валидированы для клинического использования.
        </span>
      </div>

      <MedicalViewerPanel
        patient={patient}
        showAnatomy
      />
    </>
  );
}


type WorkspaceStateProps = {
  title: string;
  message: string;
  error?: boolean;
};


function WorkspaceState({
  title,
  message,
  error = false,
}: WorkspaceStateProps) {
  return (
    <section
      className={
        error
          ? (
            "workspace-state "
            + "error"
          )
          : "workspace-state"
      }
    >
      <strong>
        {title}
      </strong>

      <span>
        {message}
      </span>
    </section>
  );
}


export default WorkbenchContent;
