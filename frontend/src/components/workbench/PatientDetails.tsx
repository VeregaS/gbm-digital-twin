import {
  Activity,
  CalendarDays,
  CircleCheck,
  CircleHelp,
  Radiation,
} from "lucide-react";

import type {
  PatientSummary,
} from "../../api/types";


type PatientDetailsProps = {
  patient:
    PatientSummary | null;

  hasTwin:
    boolean | null;
};


function PatientDetails({
  patient,
  hasTwin,
}: PatientDetailsProps) {
  if (patient === null) {
    return null;
  }

  return (
    <section
      className="patient-details-grid"
    >
      <article
        className="patient-detail-panel"
      >
        <div
          className="patient-detail-heading"
        >
          <CalendarDays
            size={17}
          />

          <div>
            <strong>
              Данные наблюдений
            </strong>

            <span>
              Доступность МРТ, GTV и дозы по времени
            </span>
          </div>
        </div>

        <div
          className="patient-timepoint-detail-grid"
        >
          {patient.timepoints.map(
            (timepoint) => (
              <div
                key={
                  timepoint.name
                }
                className="patient-timepoint-detail"
              >
                <div
                  className="patient-timepoint-detail-title"
                >
                  <strong>
                    {
                      timepoint
                      .name
                      .toUpperCase()
                    }
                  </strong>

                  <span>
                    {timepoint.days_from_baseline === null
                      ? "День неизвестен"
                      : (
                        `День ${timepoint.days_from_baseline.toFixed(0)}`
                      )}
                  </span>
                </div>

                <DataStatus
                  label="Сегментация GTV"
                  value={
                    availabilityText(
                      timepoint.gtv_available,
                    )
                  }
                  available={
                    timepoint.gtv_available
                  }
                />

                <DataStatus
                  label="Тип GTV"
                  value={
                    timepoint.gtv_type
                    ?? "не указан"
                  }
                  available={
                    timepoint.gtv_type
                    !== null
                  }
                />

                <DataStatus
                  label="RTDOSE"
                  value={
                    availabilityText(
                      timepoint.rtdose_available,
                    )
                  }
                  available={
                    timepoint.rtdose_available
                  }
                />
              </div>
            ),
          )}
        </div>
      </article>

      <article
        className="patient-detail-panel"
      >
        <div
          className="patient-detail-heading"
        >
          <Radiation
            size={17}
          />

          <div>
            <strong>
              Лечение
            </strong>

            <span>
              Доступные метаданные лучевой терапии
            </span>
          </div>
        </div>

        <dl
          className="patient-treatment-list"
        >
          <DetailRow
            label="Запись о лечении"
            value={
              patient.treatment.has_record
                ? "есть"
                : "нет"
            }
          />

          <DetailRow
            label="Начало лучевой терапии"
            value={
              patient.treatment.rt_start_day
              === null
                ? "неизвестно"
                : (
                  `день ${patient.treatment.rt_start_day.toFixed(0)}`
                )
            }
          />

          <DetailRow
            label="Фаза начала RT"
            value={
              phaseLabel(
                patient.treatment.rt_start_phase,
              )
            }
          />

          <DetailRow
            label="Суммарная доза"
            value={
              patient.treatment.dose_gy
              === null
                ? "неизвестно"
                : (
                  `${patient.treatment.dose_gy.toFixed(1)} Гр`
                )
            }
          />

          <DetailRow
            label="Количество фракций"
            value={
              patient.treatment.fractions
              === null
                ? "неизвестно"
                : String(
                  patient.treatment.fractions,
                )
            }
          />

          <DetailRow
            label="RT началась к t1"
            value={
              booleanLabel(
                patient.treatment.rt_started_by_t1,
              )
            }
          />

          <DetailRow
            label="RT началась к t2"
            value={
              booleanLabel(
                patient.treatment.rt_started_by_t2,
              )
            }
          />

          <DetailRow
            label="Схема реконструируема"
            value={
              patient.treatment.reconstructable
                ? "да"
                : "нет"
            }
            emphasis={
              patient.treatment.reconstructable
            }
          />
        </dl>
      </article>

      <article
        className="patient-detail-panel patient-protocol-panel"
      >
        <div
          className="patient-detail-heading"
        >
          <Activity
            size={17}
          />

          <div>
            <strong>
              Протокол цифрового двойника
            </strong>

            <span>
              Какие интервалы используются моделью
            </span>
          </div>
        </div>

        <div
          className="patient-protocol-flow"
        >
          <ProtocolStep
            title="t0 → t1"
            value={
              patient.dt01_days === null
                ? "—"
                : (
                  `${patient.dt01_days.toFixed(0)} дней`
                )
            }
            description="Калибровка параметров модели"
          />

          <div
            className="patient-protocol-arrow"
          >
            →
          </div>

          <ProtocolStep
            title="t1 → t2"
            value={
              patient.dt12_days === null
                ? "—"
                : (
                  `${patient.dt12_days.toFixed(0)} дней`
                )
            }
            description="Горизонт зафиксированного прогноза"
          />
        </div>

        <div
          className={
            hasTwin === true
              ? (
                "patient-twin-status available"
              )
              : "patient-twin-status"
          }
        >
          {hasTwin === true ? (
            <CircleCheck
              size={16}
            />
          ) : (
            <CircleHelp
              size={16}
            />
          )}

          <div>
            <strong>
              {hasTwin === true
                ? "Зафиксированный прогноз V2 доступен"
                : hasTwin === false
                  ? "Зафиксированного прогноза V2 нет"
                  : "Проверяем наличие прогноза V2"}
            </strong>

            <span>
              {hasTwin === true
                ? (
                  "Можно открыть раздел «Цифровой двойник» и сравнить прогноз с t2."
                )
                : (
                  "Наличие прогноза зависит от включения пациента в sealed cohort."
                )}
            </span>
          </div>
        </div>
      </article>
    </section>
  );
}


type DataStatusProps = {
  label: string;
  value: string;
  available:
    boolean | null;
};


function DataStatus({
  label,
  value,
  available,
}: DataStatusProps) {
  return (
    <div
      className="patient-data-status"
    >
      <span>
        {label}
      </span>

      <strong
        className={
          available === true
            ? "available"
            : available === false
              ? "unavailable"
              : undefined
        }
      >
        {value}
      </strong>
    </div>
  );
}


type DetailRowProps = {
  label: string;
  value: string;
  emphasis?: boolean;
};


function DetailRow({
  label,
  value,
  emphasis = false,
}: DetailRowProps) {
  return (
    <div>
      <dt>
        {label}
      </dt>

      <dd
        className={
          emphasis
            ? "emphasis"
            : undefined
        }
      >
        {value}
      </dd>
    </div>
  );
}


type ProtocolStepProps = {
  title: string;
  value: string;
  description: string;
};


function ProtocolStep({
  title,
  value,
  description,
}: ProtocolStepProps) {
  return (
    <div
      className="patient-protocol-step"
    >
      <span>
        {title}
      </span>

      <strong>
        {value}
      </strong>

      <small>
        {description}
      </small>
    </div>
  );
}


function availabilityText(
  value: boolean | null,
): string {
  if (value === true) {
    return "есть";
  }

  if (value === false) {
    return "нет";
  }

  return "неизвестно";
}


function booleanLabel(
  value: boolean | null,
): string {
  if (value === true) {
    return "да";
  }

  if (value === false) {
    return "нет";
  }

  return "неизвестно";
}


function phaseLabel(
  phase: string,
): string {
  switch (
    phase.trim().toLowerCase()
  ) {
    case "before_t0":
      return "до t0";
    case "t0_t1":
      return "между t0 и t1";
    case "t1_t2":
      return "между t1 и t2";
    case "after_t2":
      return "после t2";
    default:
      return "неизвестно";
  }
}


export default PatientDetails;
