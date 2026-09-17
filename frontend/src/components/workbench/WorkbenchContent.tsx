import type {
  Capabilities,
  FeatureCapability,
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
import PatientMetrics from "./PatientMetrics";
import PatientToolbar from "./PatientToolbar";
import TimelinePanel from "./TimelinePanel";


type WorkbenchContentProps = {
  section: WorkbenchSection;

  capabilities: Capabilities | null;
  capabilitiesError: string | null;

  patients: PatientListItem[];
  selectedPatientId: number | null;
  patient: PatientSummary | null;

  patientsLoading: boolean;
  patientLoading: boolean;
  patientError: string | null;

  onSelectPatient: (
    patientId: number | null,
  ) => void;

  onOpenViewer: () => void;
};


function WorkbenchContent({
  section,
  capabilities,
  capabilitiesError,
  patients,
  selectedPatientId,
  patient,
  patientsLoading,
  patientLoading,
  patientError,
  onSelectPatient,
  onOpenViewer,
}: WorkbenchContentProps) {
  if (
    capabilitiesError !== null
  ) {
    return (
      <WorkspaceState
        title="Capabilities unavailable"
        message={capabilitiesError}
        error
      />
    );
  }

  if (capabilities === null) {
    return (
      <WorkspaceState
        title="Checking workspace"
        message={
          "Reading available features "
          + "from the backend…"
        }
      />
    );
  }

  const capability = (
    sectionCapability(
      capabilities,
      section,
    )
  );

  if (!capability.available) {
    return (
      <WorkspaceState
        title="Workspace unavailable"
        message={
          capability.reason
          ?? (
            "This feature "
            + "is not configured."
          )
        }
      />
    );
  }

  if (
    section === "digital_twin"
  ) {
    return (
      <DigitalTwinPanel />
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
        error={patientError}
        onSelectPatient={
          onSelectPatient
        }
        onOpenViewer={
          section === "patients"
            ? onOpenViewer
            : undefined
        }
      />

      {section === "patients" ? (
        <>
          <PatientMetrics
            patient={patient}
          />

          <TimelinePanel
            patient={patient}
          />
        </>
      ) : (
        <>
          {section === "anatomy" && (
            <div
              className={
                "experimental-banner"
              }
            >
              <strong>
                Experimental research feature
              </strong>

              <span>
                Atlas-derived warnings are
                not validated for clinical use.
              </span>
            </div>
          )}

          <MedicalViewerPanel
            patient={patient}
            showAnatomy={
              section === "anatomy"
            }
          />
        </>
      )}
    </>
  );
}


function sectionCapability(
  capabilities: Capabilities,
  section: WorkbenchSection,
): FeatureCapability {
  if (
    section === "patients"
  ) {
    return capabilities.patients;
  }

  if (
    section === "digital_twin"
  ) {
    return (
      capabilities.digital_twin
    );
  }

  if (
    section === "viewer"
  ) {
    return capabilities.viewer;
  }

  return capabilities.anatomy;
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
          ? "workspace-state error"
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