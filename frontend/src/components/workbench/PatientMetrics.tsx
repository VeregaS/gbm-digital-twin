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
        label="Временные точки"
        value={
          patient
            ? String(
                patient.timepoint_count,
              )
            : "—"
        }
        unit="МРТ-наблюдения"
      />

      <MetricCard
        label="Интервал калибровки"
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
        label="Горизонт прогноза"
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
        label="Лучевая терапия"
        value={
          treatmentSummary(
            patient,
          )
        }
        unit="клинические метаданные"
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
      `${treatment.dose_gy} Гр`
      + ` · ${treatment.fractions} фр.`
    );
  }

  return treatment.has_record
    ? "Неполные данные"
    : "Нет данных";
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
