export type WorkbenchSection =
  | "patients"
  | "digital_twin"
  | "viewer"
  | "anatomy";


const sectionLabels: Record<
  WorkbenchSection,
  string
> = {
  patients: "Пациенты",
  digital_twin: "Цифровой двойник",
  viewer: "МРТ и визуализация",
  anatomy: (
    "Анатомия · эксперимент"
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
