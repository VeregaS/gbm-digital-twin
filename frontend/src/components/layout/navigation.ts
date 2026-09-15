import {
  Activity,
  Brain,
  FlaskConical,
  ScanLine,
  Stethoscope,
  Wrench,
} from "lucide-react";


export type NavigationId =
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


export const navigation: NavigationItem[] = [
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


export function navigationLabel(
  navigationId: NavigationId,
): string {
  return (
    navigation.find(
      (item) =>
        item.id === navigationId,
    )?.label
    ?? navigation[0].label
  );
}
