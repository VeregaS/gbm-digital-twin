import type {
  PatientSummary,
} from "../../api/types";


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
        label="Diffusion"
        value="—"
        unit="D · mm²/day"
      />

      <MetricCard
        label="Proliferation"
        value="—"
        unit="ρ · 1/day"
      />

      <MetricCard
        label="Effective RT response"
        value="0.010"
        unit="α · 1/Gy"
        accent
      />
    </section>
  );
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
