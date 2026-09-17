import {
  useEffect,
  useState,
} from "react";

import "./App.css";
import "./ux-russian.css";

import {
  fetchHealth,
  fetchPatient,
  fetchPatients,
} from "./api/client";

import type {
  HealthResponse,
  PatientListItem,
  PatientSummary,
} from "./api/types";

import {
  fetchCapabilities,
} from "./api/capabilities";

import type {
  Capabilities,
} from "./api/capabilities";

import {
  fetchTwinPatients,
} from "./api/twin";

import Sidebar from "./components/layout/Sidebar";

import {
  sectionLabel,
} from "./components/layout/navigation";

import type {
  WorkbenchSection,
} from "./components/layout/navigation";

import Topbar from "./components/layout/Topbar";

import WorkbenchContent from "./components/workbench/WorkbenchContent";


type PatientRequestState =
  | {
      patientId: number;
      status: "success";
      patient: PatientSummary;
    }
  | {
      patientId: number;
      status: "error";
      error: string;
    };


function App() {
  const [
    activeSection,
    setActiveSection,
  ] = useState<
    WorkbenchSection
  >(
    "patients",
  );

  const [
    health,
    setHealth,
  ] = useState<
    HealthResponse | null
  >(null);

  const [
    backendError,
    setBackendError,
  ] = useState(
    false,
  );

  const [
    capabilities,
    setCapabilities,
  ] = useState<
    Capabilities | null
  >(null);

  const [
    capabilitiesError,
    setCapabilitiesError,
  ] = useState<
    string | null
  >(null);

  const [
    patients,
    setPatients,
  ] = useState<
    PatientListItem[]
  >([]);

  const [
    patientsLoading,
    setPatientsLoading,
  ] = useState(
    true,
  );

  const [
    patientsError,
    setPatientsError,
  ] = useState<
    string | null
  >(null);

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
    PatientRequestState | null
  >(null);

  const [
    twinPatientIds,
    setTwinPatientIds,
  ] = useState<
    number[] | null
  >(null);

  const [
    twinPatientsError,
    setTwinPatientsError,
  ] = useState<
    string | null
  >(null);

  useEffect(() => {
    fetchHealth()
      .then((data) => {
        setHealth(data);
        setBackendError(false);
      })
      .catch(() => {
        setBackendError(true);
      });

    fetchCapabilities()
      .then((data) => {
        setCapabilities(data);
        setCapabilitiesError(null);
      })
      .catch(
        (error: unknown) => {
          setCapabilitiesError(
            error instanceof Error
              ? error.message
              : "Не удалось получить возможности сервера",
          );
        },
      );

    fetchPatients()
      .then((data) => {
        setPatients(
          data.patients,
        );

        setPatientsError(
          null,
        );
      })
      .catch(
        (error: unknown) => {
          setPatientsError(
            error instanceof Error
              ? error.message
              : "Не удалось загрузить список пациентов",
          );
        },
      )
      .finally(() => {
        setPatientsLoading(
          false,
        );
      });
  }, []);

  useEffect(() => {
    if (
      capabilities
      ?.digital_twin
      .available
      !== true
    ) {
      return;
    }

    let cancelled = false;

    fetchTwinPatients()
      .then((data) => {
        if (cancelled) {
          return;
        }

        setTwinPatientIds(
          data.patients.map(
            (item) =>
              item.patient_id,
          ),
        );

        setTwinPatientsError(
          null,
        );
      })
      .catch(
        (error: unknown) => {
          if (cancelled) {
            return;
          }

          setTwinPatientsError(
            error instanceof Error
              ? error.message
              : "Не удалось загрузить список пациентов с цифровым двойником",
          );
        },
      );

    return () => {
      cancelled = true;
    };
  }, [
    capabilities
    ?.digital_twin
    .available,
  ]);

  useEffect(() => {
    if (
      selectedPatientId === null
    ) {
      return;
    }

    let cancelled = false;

    fetchPatient(
      selectedPatientId,
    )
      .then((data) => {
        if (cancelled) {
          return;
        }

        setPatientRequest({
          patientId:
            selectedPatientId,
          status: "success",
          patient: data,
        });
      })
      .catch(
        (error: unknown) => {
          if (cancelled) {
            return;
          }

          setPatientRequest({
            patientId:
              selectedPatientId,
            status: "error",
            error:
              error instanceof Error
                ? error.message
                : "Не удалось загрузить данные пациента",
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
      patientRequest?.patientId
      === selectedPatientId
    )
      ? patientRequest
      : null;

  const patient =
    selectedPatientRequest?.status
    === "success"
      ? selectedPatientRequest.patient
      : null;

  const patientLoading =
    selectedPatientId !== null
    && selectedPatientRequest
    === null;

  const patientError =
    selectedPatientRequest?.status
    === "error"
      ? selectedPatientRequest.error
      : null;

  const selectedPatientHasTwin:
    boolean | null =
      selectedPatientId === null
        ? false
        : twinPatientIds === null
          ? null
          : twinPatientIds.includes(
            selectedPatientId,
          );

  function selectPatient(
    patientId: number | null,
  ) {
    setPatientRequest(
      null,
    );

    setSelectedPatientId(
      patientId,
    );
  }

  return (
    <div
      className="app-shell"
    >
      <Sidebar
        activeSection={
          activeSection
        }
        onNavigate={
          setActiveSection
        }
        health={health}
        backendError={
          backendError
        }
        capabilities={
          capabilities
        }
        capabilitiesError={
          capabilitiesError
        }
        selectedPatientId={
          selectedPatientId
        }
        selectedPatientHasTwin={
          selectedPatientHasTwin
        }
        twinPatientsError={
          twinPatientsError
        }
      />

      <main
        className="workspace"
      >
        <Topbar
          pageTitle={
            sectionLabel(
              activeSection,
            )
          }
        />

        <div
          className="workspace-content"
        >
          <WorkbenchContent
            section={
              activeSection
            }
            capabilities={
              capabilities
            }
            capabilitiesError={
              capabilitiesError
            }
            patients={patients}
            selectedPatientId={
              selectedPatientId
            }
            selectedPatientHasTwin={
              selectedPatientHasTwin
            }
            twinPatientsError={
              twinPatientsError
            }
            patient={patient}
            patientsLoading={
              patientsLoading
            }
            patientLoading={
              patientLoading
            }
            patientError={
              patientsError
              ?? patientError
            }
            onSelectPatient={
              selectPatient
            }
            onChangePatient={() =>
              setActiveSection(
                "patients",
              )
            }
            onOpenViewer={() =>
              setActiveSection(
                "viewer",
              )
            }
          />
        </div>
      </main>
    </div>
  );
}


export default App;
