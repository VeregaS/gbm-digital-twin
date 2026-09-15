import {
  Activity,
  Brain,
  CircleDot,
  FlaskConical,
  LayoutDashboard,
  Play,
  ScanLine,
  Settings2,
  Stethoscope,
  Wrench,
} from "lucide-react";
import {
  useEffect,
  useMemo,
  useState,
} from "react";

import "./App.css";
import MedicalViewerPanel from "./components/MedicalViewerPanel";

import {
  fetchHealth,
  fetchPatient,
  fetchPatients,
} from "./api/client";

import type {
  HealthResponse,
  PatientListItem,
  PatientSummary,
  PatientTreatment,
} from "./api/types";

type NavigationId =
  | "patients"
  | "viewer"
  | "twin"
  | "runs"
  | "tools"
  | "research";

type NavigationItem = {
  id: NavigationId;
  label: string;
  icon: typeof Brain;
};

const navigation: NavigationItem[] = [
  {
    id: "patients",
    label: "Patients",
    icon: Stethoscope,
  },
  {
    id: "viewer",
    label: "Viewer",
    icon: ScanLine,
  },
  {
    id: "twin",
    label: "Digital Twin",
    icon: Brain,
  },
  {
    id: "runs",
    label: "Runs",
    icon: Activity,
  },
  {
    id: "tools",
    label: "Tools",
    icon: Wrench,
  },
  {
    id: "research",
    label: "Research",
    icon: FlaskConical,
  },
];

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
    patient,
    setPatient,
  ] = useState<PatientSummary | null>(
    null,
  );

  const [
    patientLoading,
    setPatientLoading,
  ] = useState(false);

  const [
    patientError,
    setPatientError,
  ] = useState<string | null>(
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
      setPatient(null);
      setPatientError(null);
      return;
    }

    let cancelled = false;

    setPatientLoading(true);
    setPatientError(null);

    fetchPatient(selectedPatientId)
      .then((data) => {
        if (cancelled) {
          return;
        }

        setPatient(data);
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }

        setPatient(null);

        setPatientError(
          error instanceof Error
            ? error.message
            : "Failed to load patient",
        );
      })
      .finally(() => {
        if (!cancelled) {
          setPatientLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [selectedPatientId]);

  const currentNavigation = useMemo(
    () =>
      navigation.find(
        (item) =>
          item.id === activePage,
      ) ?? navigation[0],
    [activePage],
  );

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
            currentNavigation.label
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
              setSelectedPatientId
            }
            onOpenViewer={() =>
              setActivePage("viewer")
            }
          />

          <section className="summary-grid">
            <MetricCard
              label="Timepoints"
              value={
                patient
                  ? String(
                      patient.timepoint_count,
                    )
                  : "—"
              }
              unit="MRI studies"
            />

            <MetricCard
              label="Diffusion"
              value="—"
              unit="D · mm²/day"
            />

            <MetricCard
              label="Proliferation"
              value="—"
              unit="ρ · 1/day"
            />

            <MetricCard
              label="Effective RT response"
              value="0.010"
              unit="α · 1/Gy"
              accent
            />
          </section>

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

type SidebarProps = {
  activePage: NavigationId;

  onNavigate: (
    page: NavigationId,
  ) => void;

  health: HealthResponse | null;
  backendError: boolean;
};

function Sidebar({
  activePage,
  onNavigate,
  health,
  backendError,
}: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-icon">
          <Brain
            size={22}
            strokeWidth={1.9}
          />
        </div>

        <div>
          <div className="brand-name">
            GBM Twin
          </div>

          <div className="brand-description">
            Research Workbench
          </div>
        </div>
      </div>

      <div className="sidebar-section-label">
        Workspace
      </div>

      <nav className="sidebar-navigation">
        {navigation.map((item) => {
          const Icon = item.icon;

          const selected =
            activePage === item.id;

          return (
            <button
              key={item.id}
              type="button"
              className={
                selected
                  ? "navigation-button selected"
                  : "navigation-button"
              }
              onClick={() =>
                onNavigate(item.id)
              }
            >
              <Icon
                size={18}
                strokeWidth={1.8}
              />

              <span>
                {item.label}
              </span>
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="system-card">
          <div className="system-card-header">
            <span
              className={
                backendError
                  ? "connection-dot error"
                  : health
                    ? "connection-dot online"
                    : "connection-dot"
              }
            />

            <span className="system-card-title">
              Backend
            </span>
          </div>

          <div className="system-card-detail">
            {backendError
              ? "Connection unavailable"
              : health
                ? `Connected · v${health.version}`
                : "Connecting…"}
          </div>
        </div>
      </div>
    </aside>
  );
}

type TopbarProps = {
  pageTitle: string;
};

function Topbar({
  pageTitle,
}: TopbarProps) {
  return (
    <header className="topbar">
      <div>
        <div className="topbar-context">
          Digital Twin Workbench
        </div>

        <h1>{pageTitle}</h1>
      </div>

      <div className="topbar-actions">
        <div className="model-pill">
          <CircleDot size={15} />
          <span>
            V2 · Latent PIRT
          </span>
        </div>

        <button
          type="button"
          className="icon-button"
          aria-label="Settings"
        >
          <Settings2 size={18} />
        </button>
      </div>
    </header>
  );
}

type PatientToolbarProps = {
  patients: PatientListItem[];

  selectedPatientId: number | null;
  patient: PatientSummary | null;

  patientsLoading: boolean;
  patientLoading: boolean;

  error: string | null;

  onSelectPatient: (
    patientId: number | null,
  ) => void;

  onOpenViewer: () => void;
};

function PatientToolbar({
  patients,
  selectedPatientId,
  patient,
  patientsLoading,
  patientLoading,
  error,
  onSelectPatient,
  onOpenViewer,
}: PatientToolbarProps) {
  const title = patientLoading
    ? "Loading patient…"
    : patient
      ? `Patient ${patient.patient_id}`
      : "No patient selected";

  const status = error
    ? "Data error"
    : patient
      ? `${patient.timepoint_count} timepoints`
      : patientsLoading
        ? "Loading dataset"
        : `${patients.length} patients available`;

  return (
    <section className="patient-toolbar">
      <div>
        <div className="section-eyebrow">
          Active patient
        </div>

        <div className="patient-row">
          <h2>{title}</h2>

          <span className="patient-status">
            {status}
          </span>
        </div>

        <p>
          {error
            ? error
            : patient
              ? patientDescription(
                  patient,
                )
              : (
                "Select a longitudinal "
                + "CFB-GBM patient to inspect "
                + "MRI, tumor segmentation "
                + "and digital twin predictions."
              )}
        </p>
      </div>

      <div className="patient-actions">
        <select
          className="secondary-button patient-select"
          aria-label="Select patient"
          disabled={
            patientsLoading
            || patients.length === 0
          }
          value={
            selectedPatientId
            ?? ""
          }
          onChange={(event) => {
            const value =
              event.target.value;

            onSelectPatient(
              value
                ? Number(value)
                : null,
            );
          }}
        >
          <option value="">
            {patientsLoading
              ? "Loading patients…"
              : "Select patient"}
          </option>

          {patients.map(
            (patientItem) => (
              <option
                key={
                  patientItem.patient_id
                }
                value={
                  patientItem.patient_id
                }
              >
                {patientItem.label}
              </option>
            ),
          )}
        </select>

        <button
          type="button"
          className="primary-button"
          disabled={
            patient === null
            || patientLoading
          }
          onClick={onOpenViewer}
        >
          <Play size={16} />
          Open viewer
        </button>
      </div>
    </section>
  );
}

function patientDescription(
  patient: PatientSummary,
): string {
  const intervals: string[] = [];

  if (patient.dt01_days !== null) {
    intervals.push(
      `t0→t1 ${formatDay(
        patient.dt01_days,
      )}`,
    );
  }

  if (patient.dt12_days !== null) {
    intervals.push(
      `t1→t2 ${formatDay(
        patient.dt12_days,
      )}`,
    );
  }

  const treatment = (
    patient.treatment.reconstructable
      ? "RT schedule reconstructable"
      : patient.treatment.has_record
        ? "RT metadata incomplete"
        : "RT metadata unavailable"
  );

  const intervalText =
    intervals.length > 0
      ? intervals.join(" · ")
      : "Longitudinal intervals unavailable";

  return `${intervalText} · ${treatment}`;
}

type MetricCardProps = {
  label: string;
  value: string;
  unit: string;
  accent?: boolean;
};

function MetricCard({
  label,
  value,
  unit,
  accent = false,
}: MetricCardProps) {
  return (
    <article
      className={
        accent
          ? (
            "metric-card "
            + "metric-card-accent"
          )
          : "metric-card"
      }
    >
      <span className="metric-card-label">
        {label}
      </span>

      <strong>{value}</strong>

      <span className="metric-card-unit">
        {unit}
      </span>
    </article>
  );
}

type TwinPanelProps = {
  treatment: PatientTreatment | null;
};

function TwinPanel({
  treatment,
}: TwinPanelProps) {
  return (
    <section className="panel twin-panel">
      <div className="panel-heading compact">
        <div>
          <div className="section-eyebrow">
            Model
          </div>

          <h3>Digital Twin</h3>
        </div>

        <span className="model-status">
          V2
        </span>
      </div>

      <div className="parameter-list">
        <ParameterRow
          label="Tumor state"
          value="Continuous latent"
        />

        <ParameterRow
          label="Growth model"
          value="Reaction–diffusion"
        />

        <ParameterRow
          label="RT model"
          value="PIRT"
        />

        <ParameterRow
          label="Effective α"
          value="0.01 /Gy"
        />

        <ParameterRow
          label="α / β"
          value="10 Gy"
        />

        <ParameterRow
          label="Latent width"
          value="4 mm"
        />

        <ParameterRow
          label="Observation threshold"
          value="0.5"
        />

        <ParameterRow
          label="Soft temperature"
          value="0.05"
        />

        <ParameterRow
          label="RT dose"
          value={
            treatment?.dose_gy
            !== null
            && treatment?.dose_gy
            !== undefined
              ? (
                `${treatment.dose_gy} Gy`
              )
              : "—"
          }
        />

        <ParameterRow
          label="RT fractions"
          value={
            treatment?.fractions
            !== null
            && treatment?.fractions
            !== undefined
              ? String(
                  treatment.fractions,
                )
              : "—"
          }
        />
      </div>

      <div className="protocol-note">
        <strong>
          Evaluation protocol
        </strong>

        <p>
          Parameters are calibrated on
          t0 → t1 only. Held-out t2 is
          reserved for final evaluation and
          must not influence model selection.
        </p>
      </div>
    </section>
  );
}

type ParameterRowProps = {
  label: string;
  value: string;
};

function ParameterRow({
  label,
  value,
}: ParameterRowProps) {
  return (
    <div className="parameter-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

type TimelinePanelProps = {
  patient: PatientSummary | null;
};

function TimelinePanel({
  patient,
}: TimelinePanelProps) {
  const t0 = getTimepointDay(
    patient,
    "t0",
  );

  const t1 = getTimepointDay(
    patient,
    "t1",
  );

  const t2 = getTimepointDay(
    patient,
    "t2",
  );

  const rt = (
    patient?.treatment.rt_start_day
    ?? null
  );

  return (
    <section className="panel timeline-panel">
      <div className="panel-heading compact">
        <div>
          <div className="section-eyebrow">
            Longitudinal protocol
          </div>

          <h3>Patient timeline</h3>
        </div>
      </div>

      <div className="timeline">
        <div className="timeline-track" />

        <TimelineStep
          title="t0"
          description={
            t0 === null
              ? "Baseline"
              : `Day ${formatNumber(t0)}`
          }
          variant="observation"
        />

        <TimelineStep
          title="RT"
          description={
            rt === null
              ? "Unknown"
              : `Day ${formatNumber(rt)}`
          }
          variant="treatment"
        />

        <TimelineStep
          title="t1"
          description={
            t1 === null
              ? "Calibration target"
              : `Day ${formatNumber(t1)}`
          }
          variant="observation"
        />

        <TimelineStep
          title="Twin"
          description="Forecast"
          variant="prediction"
        />

        <TimelineStep
          title="t2"
          description={
            t2 === null
              ? "Held-out"
              : `Day ${formatNumber(t2)}`
          }
          variant="evaluation"
        />
      </div>
    </section>
  );
}

type TimelineStepProps = {
  title: string;
  description: string;

  variant:
    | "observation"
    | "treatment"
    | "prediction"
    | "evaluation";
};

function TimelineStep({
  title,
  description,
  variant,
}: TimelineStepProps) {
  return (
    <div className="timeline-step">
      <div
        className={
          `timeline-node ${variant}`
        }
      />

      <strong>{title}</strong>
      <span>{description}</span>
    </div>
  );
}

function RunPanel() {
  return (
    <section className="panel run-panel">
      <div className="panel-heading compact">
        <div>
          <div className="section-eyebrow">
            Runtime
          </div>

          <h3>Latest run</h3>
        </div>
      </div>

      <div className="empty-run">
        <LayoutDashboard
          size={26}
          strokeWidth={1.5}
        />

        <div>
          <strong>
            No runs available
          </strong>

          <span>
            Calibration and prediction runs
            will appear here.
          </span>
        </div>
      </div>
    </section>
  );
}

function getTimepointDay(
  patient: PatientSummary | null,
  name: string,
): number | null {
  if (patient === null) {
    return null;
  }

  const timepoint =
    patient.timepoints.find(
      (item) => item.name === name,
    );

  return (
    timepoint?.days_from_baseline
    ?? null
  );
}

function formatNumber(
  value: number,
): string {
  if (Number.isInteger(value)) {
    return String(value);
  }

  return value.toFixed(1);
}

function formatDay(
  value: number,
): string {
  return `${formatNumber(value)} d`;
}

export default App;