export type WorkbenchSection =
  | "patients"
  | "digital_twin"
  | "viewer"
  | "anatomy";


const sectionLabels: Record<
  WorkbenchSection,
  string
> = {
  patients: "Patients",
  digital_twin: "Digital Twin",
  viewer: "Imaging",
  anatomy: (
    "Anatomy · Experimental"
  ),
};


export function sectionLabel(
  section: WorkbenchSection,
): string {
  return (
    sectionLabels[
      section
    ]
  );
}