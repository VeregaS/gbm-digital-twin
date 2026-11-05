import type {
  PatientSummary,
} from "../../api/types";

import {
  formatNumber,
} from "./formatters";


type TimelinePanelProps = {
  patient: PatientSummary | null;
};


function TimelinePanel({
  patient,
}: TimelinePanelProps) {
  const t0 = getTimepointDay(
    patient,
    "t0",
  );

  const t1 = getTimepointDay(
    patient,
    "t1",
  );

  const t2 = getTimepointDay(
    patient,
    "t2",
  );

  const rt = (
    patient?.treatment.rt_start_day
    ?? null
  );

  return (
    <section className="panel timeline-panel">
      <div className="panel-heading compact">
        <div>
          <div className="section-eyebrow">
            Продольный протокол
          </div>

          <h3>Хронология пациента</h3>
        </div>
      </div>

      <div className="timeline">
        <div className="timeline-track" />

        <TimelineStep
          title="t0"
          description={
            t0 === null
              ? "Исходное наблюдение"
              : `День ${formatNumber(t0)}`
          }
          variant="observation"
        />

        <TimelineStep
          title="Лучевая терапия"
          description={
            rt === null
              ? "Начало неизвестно"
              : `День ${formatNumber(rt)}`
          }
          variant="treatment"
        />

        <TimelineStep
          title="t1"
          description={
            t1 === null
              ? "Конец калибровки"
              : `День ${formatNumber(t1)}`
          }
          variant="observation"
        />

        <TimelineStep
          title="t2"
          description={
            t2 === null
              ? "Отложенная цель"
              : `День ${formatNumber(t2)}`
          }
          variant="evaluation"
        />
      </div>
    </section>
  );
}


type TimelineStepProps = {
  title: string;
  description: string;

  variant:
    | "observation"
    | "treatment"
    | "evaluation";
};


function TimelineStep({
  title,
  description,
  variant,
}: TimelineStepProps) {
  return (
    <div className="timeline-step">
      <div
        className={
          `timeline-node ${variant}`
        }
      />

      <strong>{title}</strong>
      <span>{description}</span>
    </div>
  );
}


function getTimepointDay(
  patient: PatientSummary | null,
  name: string,
): number | null {
  if (patient === null) {
    return null;
  }

  const timepoint =
    patient.timepoints.find(
      (item) => item.name === name,
    );

  return (
    timepoint?.days_from_baseline
    ?? null
  );
}


export default TimelinePanel;
