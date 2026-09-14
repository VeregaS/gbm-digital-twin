import {
  Activity,
  Brain,
  ChevronDown,
  CircleDot,
  FlaskConical,
  LayoutDashboard,
  Play,
  ScanLine,
  Settings2,
  Stethoscope,
  Wrench,
} from "lucide-react";
import { useEffect, useState } from "react";

import "./App.css";

type HealthResponse = {
  status: string;
  service: string;
  version: string;
};

type NavigationItem = {
  id:
    | "patients"
    | "viewer"
    | "twin"
    | "runs"
    | "tools"
    | "research";
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
  const [activePage, setActivePage] =
    useState<NavigationItem["id"]>("patients");

  const [health, setHealth] =
    useState<HealthResponse | null>(null);

  const [backendError, setBackendError] =
    useState(false);

  useEffect(() => {
    fetch("/api/health")
      .then((response) => {
        if (!response.ok) {
          throw new Error(
            `HTTP ${response.status}`,
          );
        }

        return response.json();
      })
      .then((data: HealthResponse) => {
        setHealth(data);
        setBackendError(false);
      })
      .catch(() => {
        setBackendError(true);
      });
  }, []);

  const currentNavigation =
    navigation.find(
      (item) => item.id === activePage,
    ) ?? navigation[0];

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
          pageTitle={currentNavigation.label}
        />

        <div className="workspace-content">
          <PatientToolbar />

          <section className="summary-grid">
            <MetricCard
              label="Timepoints"
              value="—"
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
            <ViewerPanel />
            <TwinPanel />
          </section>

          <section className="lower-grid">
            <TimelinePanel />
            <RunPanel />
          </section>
        </div>
      </main>
    </div>
  );
}

type SidebarProps = {
  activePage: NavigationItem["id"];
  onNavigate: (
    page: NavigationItem["id"],
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
          <Brain size={22} strokeWidth={1.9} />
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
              <span>{item.label}</span>
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
          <span>V2 · Latent PIRT</span>
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

function PatientToolbar() {
  return (
    <section className="patient-toolbar">
      <div>
        <div className="section-eyebrow">
          Active patient
        </div>

        <div className="patient-row">
          <h2>No patient selected</h2>

          <span className="patient-status">
            Waiting for dataset
          </span>
        </div>

        <p>
          Select a longitudinal CFB-GBM
          patient to inspect MRI, tumor
          segmentation and digital twin
          predictions.
        </p>
      </div>

      <div className="patient-actions">
        <button
          type="button"
          className="secondary-button"
        >
          Select patient
          <ChevronDown size={16} />
        </button>

        <button
          type="button"
          className="primary-button"
          disabled
        >
          <Play size={16} />
          Open viewer
        </button>
      </div>
    </section>
  );
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
          ? "metric-card metric-card-accent"
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

function ViewerPanel() {
  return (
    <section className="panel viewer-panel">
      <div className="panel-heading">
        <div>
          <div className="section-eyebrow">
            Imaging
          </div>
          <h3>MRI Viewer</h3>
        </div>

        <div className="viewer-tabs">
          <button
            type="button"
            className="viewer-tab active"
          >
            3D
          </button>

          <button
            type="button"
            className="viewer-tab"
          >
            Axial
          </button>

          <button
            type="button"
            className="viewer-tab"
          >
            Coronal
          </button>

          <button
            type="button"
            className="viewer-tab"
          >
            Sagittal
          </button>
        </div>
      </div>

      <div className="viewer-stage">
        <div className="viewer-grid" />

        <div className="scan-placeholder">
          <Brain
            size={76}
            strokeWidth={1.15}
          />

          <div className="scan-placeholder-title">
            MRI volume
          </div>

          <div className="scan-placeholder-text">
            T1Gd, GTV and latent tumor
            density will be rendered here.
          </div>
        </div>

        <div className="viewer-legend">
          <LegendItem
            className="legend-dot observation"
            label="Observed GTV"
          />

          <LegendItem
            className="legend-dot prediction"
            label="Predicted tumor"
          />
        </div>
      </div>
    </section>
  );
}

type LegendItemProps = {
  className: string;
  label: string;
};

function LegendItem({
  className,
  label,
}: LegendItemProps) {
  return (
    <div className="legend-item">
      <span className={className} />
      <span>{label}</span>
    </div>
  );
}

function TwinPanel() {
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

function TimelinePanel() {
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
          description="Baseline"
          variant="observation"
        />

        <TimelineStep
          title="RT"
          description="Treatment"
          variant="treatment"
        />

        <TimelineStep
          title="t1"
          description="Calibration target"
          variant="observation"
        />

        <TimelineStep
          title="Twin"
          description="Forecast"
          variant="prediction"
        />

        <TimelineStep
          title="t2"
          description="Held-out"
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
        className={`timeline-node ${variant}`}
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

export default App;