import type {
  PatientSummary,
} from "../../api/types";

import {
  formatDay,
} from "./formatters";


type PatientMetricsProps = {
  patient: PatientSummary | null;
};


function PatientMetrics({
  patient,
}: PatientMetricsProps) {
  return (
    <section className="summary-grid">
      <MetricCard
        label="Timepoints"
        value={
          patient
            ? String(
                patient.timepoint_count,
              )
            : "—"
        }
        unit="MRI studies"
      />

      <MetricCard
        label="Calibration interval"
        value={
          patient?.dt01_days
          !== null
          && patient?.dt01_days
          !== undefined
            ? formatDay(
                patient.dt01_days,
              )
            : "—"
        }
        unit="t0 → t1"
      />

      <MetricCard
        label="Held-out horizon"
        value={
          patient?.dt12_days
          !== null
          && patient?.dt12_days
          !== undefined
            ? formatDay(
                patient.dt12_days,
              )
            : "—"
        }
        unit="t1 → t2"
      />

      <MetricCard
        label="Radiotherapy"
        value={
          treatmentSummary(
            patient,
          )
        }
        unit="clinical metadata"
      />
    </section>
  );
}


function treatmentSummary(
  patient: PatientSummary | null,
): string {
  if (patient === null) {
    return "—";
  }

  const treatment =
    patient.treatment;

  if (
    treatment.reconstructable
    && treatment.dose_gy !== null
    && treatment.fractions !== null
  ) {
    return (
      `${treatment.dose_gy} Gy`
      + ` · ${treatment.fractions} fx`
    );
  }

  return treatment.has_record
    ? "Incomplete"
    : "Unavailable";
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
          ? (
            "metric-card "
            + "metric-card-accent"
          )
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


export default PatientMetrics;
