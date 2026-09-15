export type WorkbenchSection =
  | "patients"
  | "viewer"
  | "anatomy";


const sectionLabels: Record<
  WorkbenchSection,
  string
> = {
  patients: "Patients",
  viewer: "Imaging",
  anatomy: "Anatomy · Experimental",
};


export function sectionLabel(
  section: WorkbenchSection,
): string {
  return sectionLabels[
    section
  ];
}
