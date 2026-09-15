import {
  Brain,
} from "lucide-react";

import type {
  HealthResponse,
} from "../../api/types";

import type {
  Capabilities,
} from "../../api/capabilities";

import FunctionalNavigation from "../FunctionalNavigation";

import type {
  WorkbenchSection,
} from "./navigation";


type SidebarProps = {
  activeSection: WorkbenchSection;

  onNavigate: (
    section: WorkbenchSection,
  ) => void;

  health: HealthResponse | null;
  backendError: boolean;

  capabilities: Capabilities | null;
  capabilitiesError: string | null;
};


function Sidebar({
  activeSection,
  onNavigate,
  health,
  backendError,
  capabilities,
  capabilitiesError,
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

      <FunctionalNavigation
        active={activeSection}
        capabilities={capabilities}
        capabilitiesError={
          capabilitiesError
        }
        onChange={onNavigate}
      />

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


export default Sidebar;
