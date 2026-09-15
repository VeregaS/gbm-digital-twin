import {
  useEffect,
  useState,
} from "react";

import "./App.css";

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

import MedicalViewerPanel from "./components/MedicalViewerPanel";
import Sidebar from "./components/layout/Sidebar";
import {
  navigationLabel,
} from "./components/layout/navigation";
import type {
  NavigationId,
} from "./components/layout/navigation";
import Topbar from "./components/layout/Topbar";
import PatientMetrics from "./components/workbench/PatientMetrics";
import PatientToolbar from "./components/workbench/PatientToolbar";
import RunPanel from "./components/workbench/RunPanel";
import TimelinePanel from "./components/workbench/TimelinePanel";
import TwinPanel from "./components/workbench/TwinPanel";


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
    activePage,
    setActivePage,
  ] = useState<NavigationId>(
    "patients",
  );

  const [
    health,
    setHealth,
  ] = useState<HealthResponse | null>(
    null,
  );

  const [
    backendError,
    setBackendError,
  ] = useState(false);

  const [
    patients,
    setPatients,
  ] = useState<PatientListItem[]>([]);

  const [
    patientsLoading,
    setPatientsLoading,
  ] = useState(true);

  const [
    patientsError,
    setPatientsError,
  ] = useState<string | null>(
    null,
  );

  const [
    selectedPatientId,
    setSelectedPatientId,
  ] = useState<number | null>(
    null,
  );

  const [
    patientRequest,
    setPatientRequest,
  ] = useState<PatientRequestState | null>(
    null,
  );

  useEffect(() => {
    fetchHealth()
      .then((data) => {
        setHealth(data);
        setBackendError(false);
      })
      .catch(() => {
        setBackendError(true);
      });

    fetchPatients()
      .then((data) => {
        setPatients(data.patients);
        setPatientsError(null);
      })
      .catch((error: unknown) => {
        setPatientsError(
          error instanceof Error
            ? error.message
            : "Failed to load patients",
        );
      })
      .finally(() => {
        setPatientsLoading(false);
      });
  }, []);

  useEffect(() => {
    if (selectedPatientId === null) {
      return;
    }

    let cancelled = false;

    fetchPatient(selectedPatientId)
      .then((data) => {
        if (cancelled) {
          return;
        }

        setPatientRequest({
          patientId: selectedPatientId,
          status: "success",
          patient: data,
        });
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }

        setPatientRequest({
          patientId: selectedPatientId,
          status: "error",
          error:
            error instanceof Error
              ? error.message
              : "Failed to load patient",
        });
      });

    return () => {
      cancelled = true;
    };
  }, [selectedPatientId]);

  const selectedPatientRequest =
    selectedPatientId !== null
    && patientRequest?.patientId
      === selectedPatientId
      ? patientRequest
      : null;

  const patient =
    selectedPatientRequest?.status
    === "success"
      ? selectedPatientRequest.patient
      : null;

  const patientLoading =
    selectedPatientId !== null
    && selectedPatientRequest === null;

  const patientError =
    selectedPatientRequest?.status
    === "error"
      ? selectedPatientRequest.error
      : null;

  function selectPatient(
    patientId: number | null,
  ) {
    setPatientRequest(null);
    setSelectedPatientId(patientId);
  }

  return (
    <div className="app-shell">
      <Sidebar
        activePage={activePage}
        onNavigate={setActivePage}
        health={health}
        backendError={backendError}
      />

      <main className="workspace">
        <Topbar
          pageTitle={
            navigationLabel(
              activePage,
            )
          }
        />

        <div className="workspace-content">
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
              patientsError
              ?? patientError
            }
            onSelectPatient={
              selectPatient
            }
            onOpenViewer={() =>
              setActivePage("viewer")
            }
          />

          <PatientMetrics
            patient={patient}
          />

          <section className="main-grid">
            <MedicalViewerPanel
              patient={patient}
            />

            <TwinPanel
              treatment={
                patient?.treatment
                ?? null
              }
            />
          </section>

          <section className="lower-grid">
            <TimelinePanel
              patient={patient}
            />

            <RunPanel />
          </section>
        </div>
      </main>
    </div>
  );
}


export default App;
