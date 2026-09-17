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
        title={
          "Capabilities unavailable"
        }
        message={
          capabilitiesError
        }
        error
      />
    );
  }

  if (
    capabilities === null
  ) {
    return (
      <WorkspaceState
        title={
          "Checking workspace"
        }
        message={
          "Reading available "
          + "features from backend…"
        }
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
          title={
            "Patients unavailable"
          }
          message={
            capabilities
            .patients
            .reason
            ?? (
              "Patient dataset "
              + "is unavailable."
            )
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
        title={
          "Select a patient first"
        }
        message={
          "Digital Twin and Imaging "
          + "are patient-specific. "
          + "Choose a patient on "
          + "the Patients page."
        }
      />
    );
  }

  if (patientLoading) {
    return (
      <WorkspaceState
        title={
          `Loading Patient `
          + `${selectedPatientId}`
        }
        message={
          "Reading longitudinal "
          + "patient data…"
        }
      />
    );
  }

  if (
    patientError !== null
  ) {
    return (
      <WorkspaceState
        title={
          "Patient unavailable"
        }
        message={
          patientError
        }
        error
      />
    );
  }

  if (patient === null) {
    return (
      <WorkspaceState
        title={
          "Patient unavailable"
        }
        message={
          "Patient data could "
          + "not be loaded."
        }
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
          title={
            "Digital Twin unavailable"
          }
          message={
            capabilities
            .digital_twin
            .reason
            ?? (
              "Digital Twin "
              + "is unavailable."
            )
          }
        />
      );
    }

    if (
      twinPatientsError !== null
    ) {
      return (
        <WorkspaceState
          title={
            "Digital Twin unavailable"
          }
          message={
            twinPatientsError
          }
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
          title={
            "Checking Digital Twin"
          }
          message={
            "Checking whether this "
            + "patient has a sealed "
            + "V2 prediction…"
          }
        />
      );
    }

    if (
      !selectedPatientHasTwin
    ) {
      return (
        <WorkspaceState
          title={
            "No sealed prediction"
          }
          message={
            `Patient ${
              patient.patient_id
            } is not present in `
            + "the sealed V2 "
            + "evaluation cohort."
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
          title={
            "Imaging unavailable"
          }
          message={
            capabilities
            .viewer
            .reason
            ?? (
              "Imaging is "
              + "unavailable."
            )
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
        title={
          "Anatomy unavailable"
        }
        message={
          capabilities
          .anatomy
          .reason
          ?? (
            "Anatomy is "
            + "unavailable."
          )
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
        className={
          "experimental-banner"
        }
      >
        <strong>
          Experimental research feature
        </strong>

        <span>
          Atlas-derived warnings
          are not validated for
          clinical use.
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