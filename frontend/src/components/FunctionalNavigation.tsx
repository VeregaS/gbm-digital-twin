import {
  Brain,
  Images,
  Users,
} from "lucide-react";


export type WorkbenchSection =
  | "patients"
  | "viewer"
  | "anatomy";


type Props = {
  active: WorkbenchSection;

  anatomyAvailable: boolean;

  anatomyReason:
    string | null;

  onChange: (
    section: WorkbenchSection,
  ) => void;
};


function FunctionalNavigation({
  active,
  anatomyAvailable,
  anatomyReason,
  onChange,
}: Props) {
  return (
    <nav
      className="functional-nav"
      aria-label="Workbench"
    >
      <button
        type="button"
        className={
          active === "patients"
            ? "functional-nav-item active"
            : "functional-nav-item"
        }
        onClick={() =>
          onChange("patients")
        }
      >
        <Users size={16} />

        <span>
          Patients
        </span>
      </button>

      <button
        type="button"
        className={
          active === "viewer"
            ? "functional-nav-item active"
            : "functional-nav-item"
        }
        onClick={() =>
          onChange("viewer")
        }
      >
        <Images size={16} />

        <span>
          Imaging
        </span>
      </button>

      <button
        type="button"
        disabled={
          !anatomyAvailable
        }
        title={
          anatomyAvailable
            ? "Anatomical risk analysis"
            : (
              anatomyReason
              ?? "Atlas setup required"
            )
        }
        className={
          active === "anatomy"
            ? "functional-nav-item active"
            : "functional-nav-item"
        }
        onClick={() =>
          onChange("anatomy")
        }
      >
        <Brain size={16} />

        <span>
          Anatomy
        </span>

        {!anatomyAvailable && (
          <small>
            Setup required
          </small>
        )}
      </button>
    </nav>
  );
}


export default FunctionalNavigation;