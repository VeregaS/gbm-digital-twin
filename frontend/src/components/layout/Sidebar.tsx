import {
  Brain,
} from "lucide-react";

import type {
  HealthResponse,
} from "../../api/types";

import {
  navigation,
} from "./navigation";
import type {
  NavigationId,
} from "./navigation";


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


export default Sidebar;
