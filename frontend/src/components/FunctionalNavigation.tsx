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
  active:
    WorkbenchSection;

  capabilities:
    Capabilities | null;

  capabilitiesError:
    string | null;

  selectedPatientId:
    number | null;

  selectedPatientHasTwin:
    boolean | null;

  twinPatientsError:
    string | null;

  onChange: (
    section: WorkbenchSection,
  ) => void;
};


function unavailable(
  reason: string,
): FeatureCapability {
  return {
    available: false,
    reason,
  };
}


function requirePatient(
  capability: FeatureCapability,
  selectedPatientId:
    number | null,
): FeatureCapability {
  if (!capability.available) {
    return capability;
  }

  if (
    selectedPatientId === null
  ) {
    return unavailable(
      "Сначала выберите пациента "
      + "в разделе «Пациенты».",
    );
  }

  return capability;
}


function resolveTwinCapability(
  capability: FeatureCapability,
  selectedPatientId:
    number | null,
  selectedPatientHasTwin:
    boolean | null,
  twinPatientsError:
    string | null,
): FeatureCapability {
  if (!capability.available) {
    return capability;
  }

  if (
    selectedPatientId === null
  ) {
    return unavailable(
      "Сначала выберите пациента "
      + "в разделе «Пациенты».",
    );
  }

  if (
    twinPatientsError !== null
  ) {
    return unavailable(
      twinPatientsError
    );
  }

  if (
    selectedPatientHasTwin
    === null
  ) {
    return unavailable(
      "Проверяем наличие "
      + "зафиксированного прогноза…",
    );
  }

  if (
    !selectedPatientHasTwin
  ) {
    return unavailable(
      `Для пациента ${selectedPatientId} `
      + "нет зафиксированного прогноза V2.",
    );
  }

  return capability;
}


function FunctionalNavigation({
  active,
  capabilities,
  capabilitiesError,
  selectedPatientId,
  selectedPatientHasTwin,
  twinPatientsError,
  onChange,
}: FunctionalNavigationProps) {
  const fallbackReason =
    capabilitiesError
    ?? (
      "Проверяем доступность "
      + "возможностей сервера…"
    );

  const patientBadge =
    selectedPatientId === null
      ? undefined
      : `P${selectedPatientId}`;

  const twinCapability =
    capabilities === null
      ? null
      : resolveTwinCapability(
        capabilities.digital_twin,
        selectedPatientId,
        selectedPatientHasTwin,
        twinPatientsError,
      );

  const imagingCapability =
    capabilities === null
      ? null
      : requirePatient(
        capabilities.viewer,
        selectedPatientId,
      );

  const anatomyCapability =
    capabilities === null
      ? null
      : requirePatient(
        capabilities.anatomy,
        selectedPatientId,
      );

  return (
    <nav
      className="functional-nav"
      aria-label="Разделы рабочей среды"
    >
      <NavigationButton
        section="patients"
        label="Пациенты"
        icon={Users}
        active={active}
        capability={
          capabilities?.patients
          ?? null
        }
        fallbackReason={
          fallbackReason
        }
        onChange={onChange}
      />

      <NavigationButton
        section="digital_twin"
        label="Цифровой двойник"
        badge={patientBadge}
        icon={Activity}
        active={active}
        capability={
          twinCapability
        }
        fallbackReason={
          fallbackReason
        }
        onChange={onChange}
      />

      <NavigationButton
        section="viewer"
        label="МРТ"
        badge={patientBadge}
        icon={Images}
        active={active}
        capability={
          imagingCapability
        }
        fallbackReason={
          fallbackReason
        }
        onChange={onChange}
      />

      <NavigationButton
        section="anatomy"
        label="Анатомия"
        badge="Эксперимент"
        icon={Brain}
        active={active}
        capability={
          anatomyCapability
        }
        fallbackReason={
          fallbackReason
        }
        onChange={onChange}
      />
    </nav>
  );
}


type NavigationButtonProps = {
  section:
    WorkbenchSection;

  label: string;
  badge?: string;

  icon:
    typeof Brain;

  active:
    WorkbenchSection;

  capability:
    FeatureCapability | null;

  fallbackReason:
    string;

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
      <Icon
        size={16}
      />

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
