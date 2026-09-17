import {
  Activity,
  Brain,
  Images,
  Users,
} from "lucide-react";

import type {
  Capabilities,
  FeatureCapability,
} from "../api/capabilities";

import type {
  WorkbenchSection,
} from "./layout/navigation";


type FunctionalNavigationProps = {
  active: WorkbenchSection;
  capabilities: Capabilities | null;
  capabilitiesError: string | null;

  onChange: (
    section: WorkbenchSection,
  ) => void;
};


function FunctionalNavigation({
  active,
  capabilities,
  capabilitiesError,
  onChange,
}: FunctionalNavigationProps) {
  const fallbackReason =
    capabilitiesError
    ?? "Checking backend availability…";

  return (
    <nav
      className="functional-nav"
      aria-label="Workbench"
    >
      <NavigationButton
        section="patients"
        label="Patients"
        icon={Users}
        active={active}
        capability={
          capabilities?.patients
          ?? null
        }
        fallbackReason={fallbackReason}
        onChange={onChange}
      />

      <NavigationButton
        section="digital_twin"
        label="Digital Twin"
        icon={Activity}
        active={active}
        capability={
          capabilities?.digital_twin
          ?? null
        }
        fallbackReason={fallbackReason}
        onChange={onChange}
      />

      <NavigationButton
        section="viewer"
        label="Imaging"
        icon={Images}
        active={active}
        capability={
          capabilities?.viewer
          ?? null
        }
        fallbackReason={fallbackReason}
        onChange={onChange}
      />

      <NavigationButton
        section="anatomy"
        label="Anatomy"
        badge="Experimental"
        icon={Brain}
        active={active}
        capability={
          capabilities?.anatomy
          ?? null
        }
        fallbackReason={fallbackReason}
        onChange={onChange}
      />
    </nav>
  );
}


type NavigationButtonProps = {
  section: WorkbenchSection;
  label: string;
  badge?: string;
  icon: typeof Brain;

  active: WorkbenchSection;
  capability:
    FeatureCapability | null;
  fallbackReason: string;

  onChange: (
    section: WorkbenchSection,
  ) => void;
};


function NavigationButton({
  section,
  label,
  badge,
  icon: Icon,
  active,
  capability,
  fallbackReason,
  onChange,
}: NavigationButtonProps) {
  const available =
    capability?.available
    ?? false;

  const reason =
    capability?.reason
    ?? fallbackReason;

  return (
    <button
      type="button"
      disabled={!available}
      title={
        available
          ? label
          : reason
      }
      className={
        active === section
          ? (
            "functional-nav-item "
            + "active"
          )
          : "functional-nav-item"
      }
      onClick={() =>
        onChange(section)
      }
    >
      <Icon size={16} />

      <span>
        {label}
      </span>

      {badge && (
        <small>
          {badge}
        </small>
      )}
    </button>
  );
}


export default FunctionalNavigation;