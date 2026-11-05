import type {
  PatientSummary,
} from "../../api/types";

import type {
  TwinCohort,
  TwinForecastReliability,
  TwinMethodMetrics,
  TwinPatientEvaluation,
} from "../../api/twin";


type TwinOverviewTabProps = {
  patient:
    PatientSummary;

  evaluation:
    TwinPatientEvaluation;

  cohort:
    TwinCohort;

  reliability:
    TwinForecastReliability | null;

  reliabilityError:
    string | null;
};


function TwinOverviewTab({
  patient,
  evaluation,
  cohort,
  reliability,
  reliabilityError,
}: TwinOverviewTabProps) {
  const diceDelta = (
    evaluation.twin.dice
    - evaluation.persistence.dice
  );

  const outcomeText =
    Math.abs(diceDelta) < 0.001
      ? (
        "По Dice цифровой двойник практически не отличается от простого baseline «без изменений»."
      )
      : diceDelta > 0
        ? (
          "Цифровой двойник лучше совпадает с реальной опухолью на t2, чем baseline «без изменений»: преимущество по Dice "
          + diceDelta.toFixed(3)
          + "."
        )
        : (
          "Baseline «без изменений» лучше совпадает с реальной опухолью на t2: его преимущество по Dice "
          + Math.abs(
            diceDelta
          ).toFixed(3)
          + "."
        );

  return (
    <div
      className="twin-tab-stack"
    >
      <section
        className="twin-explanation-card"
      >
        <div>
          <span>
            Что прогнозируется?
          </span>

          <strong>
            Распространение опухоли от t1 к t2
          </strong>
        </div>

        <p>
          Параметры модели калибруются по данным до момента прогноза. Реальная сегментация t2 не используется при построении прогноза: она открывается только после фиксации результата и служит для независимой оценки.
        </p>
      </section>

      <ReliabilityCard
        reliability={
          reliability
        }
        error={
          reliabilityError
        }
      />

      <section
        className="twin-patient-metric-grid"
      >
        <Metric
          title="Совпадение (Dice)"
          value={
            evaluation.twin.dice
            .toFixed(3)
          }
          help="Насколько предсказанная и реальная области опухоли перекрываются. 1.0 означает полное совпадение. Больше — лучше."
        />

        <Metric
          title="Ошибка объёма"
          value={
            (
              evaluation.twin
              .relative_volume_error
              * 100
            ).toFixed(1)
            + "%"
          }
          help="Насколько объём прогноза отличается от реального объёма опухоли на t2. Меньше — лучше."
        />

        <Metric
          title="Ошибка границы (HD95)"
          value={
            evaluation.twin
            .hd95_mm === null
              ? "—"
              : (
                evaluation.twin
                .hd95_mm
                .toFixed(1)
                + " мм"
              )
          }
          help="Расхождение поверхностей опухоли без учёта небольшого числа крайних точек. Меньше — лучше."
        />

        <Metric
          title="Смещение центра"
          value={
            evaluation.twin
            .centroid_distance_mm
            === null
              ? "—"
              : (
                evaluation.twin
                .centroid_distance_mm
                .toFixed(1)
                + " мм"
              )
          }
          help="Расстояние между центрами предсказанной и реальной областей опухоли. Меньше — лучше."
        />
      </section>

      <section
        className="twin-readable-summary"
      >
        <strong>
          Краткая интерпретация
        </strong>

        <p>
          {outcomeText}
        </p>

        <span>
          Средний Dice цифрового двойника по текущему cohort:
          {" "}
          {
            cohort.twin.mean_dice
            ?.toFixed(3)
            ?? "—"
          }
        </span>
      </section>

      <section
        className="twin-method-card"
      >
        <div
          className="twin-panel-heading"
        >
          <div>
            <strong>
              Сравнение методов
            </strong>

            <span>
              Все методы оцениваются по одной и той же отложенной реальной сегментации t2
            </span>
          </div>
        </div>

        <table
          className="twin-method-table"
        >
          <thead>
            <tr>
              <th>
                Метод
              </th>

              <th>
                Dice
              </th>

              <th>
                Ошибка объёма
              </th>

              <th>
                HD95
              </th>
            </tr>
          </thead>

          <tbody>
            <MethodRow
              name="Цифровой двойник"
              metrics={
                evaluation.twin
              }
              emphasis
            />

            <MethodRow
              name="Без изменений"
              metrics={
                evaluation.persistence
              }
            />

            <MethodRow
              name="Прогноз по объёму"
              metrics={
                evaluation.volume_baseline
              }
            />
          </tbody>
        </table>
      </section>

      <section
        className="twin-protocol-strip"
      >
        <div>
          <strong>
            t0
          </strong>

          <span>
            исходное наблюдение
          </span>
        </div>

        <b>
          калибровка
        </b>

        <div>
          <strong>
            t1
          </strong>

          <span>
            последнее наблюдение и старт прогноза
          </span>
        </div>

        <b>
          прогноз фиксируется
        </b>

        <div>
          <strong>
            t2
          </strong>

          <span>
            реальная отложенная цель для оценки
          </span>
        </div>
      </section>

      <div
        className="twin-context-note"
      >
        Пациент {patient.patient_id}
        {" · "}
        {patient.timepoint_count} наблюдения
        {" · "}
        {
          patient.treatment
          .reconstructable
            ? "схема лучевой терапии восстановлена"
            : "данные о лучевой терапии не позволяют полностью восстановить схему"
        }
      </div>
    </div>
  );
}


function ReliabilityCard({
  reliability,
  error,
}: {
  reliability:
    TwinForecastReliability | null;
  error: string | null;
}) {
  if (reliability === null) {
    return (
      <section
        className="twin-reliability-card unavailable"
      >
        <div>
          <span>
            Pre-t2 quality gate
          </span>

          <strong>
            Недоступен
          </strong>
        </div>

        <p>
          {error
            ?? "Не удалось получить техническую оценку надёжности прогноза."}
        </p>
      </section>
    );
  }

  return (
    <section
      className={
        "twin-reliability-card "
        + reliability.status
      }
    >
      <div
        className="twin-reliability-header"
      >
        <div>
          <span>
            Pre-t2 quality gate
          </span>

          <strong>
            {
              reliabilityStatusLabel(
                reliability.status,
              )
            }
          </strong>
        </div>

        <div
          className="twin-reliability-model"
        >
          <b>
            {reliability.model_version}
          </b>

          <span>
            {reliability.protocol_version}
          </span>
        </div>
      </div>

      <div
        className="twin-reliability-facts"
      >
        <span>
          D/ρ идентифицируемы:{" "}
          <strong>
            {
              reliability
              .calibration_identifiable
                ? "да"
                : "нет"
            }
          </strong>
        </span>

        <span>
          D на границе:{" "}
          <strong>
            {
              reliability
              .diffusion_at_boundary
                ? "да"
                : "нет"
            }
          </strong>
        </span>

        <span>
          ρ на границе:{" "}
          <strong>
            {
              reliability
              .proliferation_at_boundary
                ? "да"
                : "нет"
            }
          </strong>
        </span>

        <span>
          Горизонт:{" "}
          <strong>
            {
              reliability
              .forecast_horizon_days
              .toFixed(0)
            } дн.
          </strong>
        </span>
      </div>

      {reliability.factors.length > 0 ? (
        <div
          className="twin-reliability-factors"
        >
          {reliability.factors.map(
            (factor) => (
              <div
                key={
                  factor.code
                }
              >
                <strong>
                  {
                    reliabilityFactorLabel(
                      factor.code,
                    )
                  }
                </strong>

                <span>
                  {
                    reliabilityFactorMessage(
                      factor.code,
                      factor.message,
                    )
                  }
                </span>
              </div>
            ),
          )}
        </div>
      ) : (
        <p>
          Известных технических флагов, доступных до раскрытия t2, не обнаружено.
        </p>
      )}

      <small>
        Это не вероятность правильности и не клиническая уверенность. Статус не использует реальную опухоль на t2.
      </small>
    </section>
  );
}


function reliabilityStatusLabel(
  status:
    TwinForecastReliability[
      "status"
    ],
): string {
  switch (status) {
    case "nominal":
      return "Без известных технических флагов";
    case "caution":
      return "Есть технические оговорки";
    case "limited":
      return "Надёжность ограничена";
  }
}


function reliabilityFactorLabel(
  code: string,
): string {
  switch (code) {
    case "calibration_non_identifiable":
      return "Калибровка неидентифицируема";
    case "diffusion_at_boundary":
      return "D на границе поиска";
    case "proliferation_at_boundary":
      return "ρ на границе поиска";
    case "prediction_empty":
      return "Пустой прогноз";
    case "prediction_outside_t1_brain":
      return "Прогноз выходит за t1 brain mask";
    case "prediction_fragmented":
      return "Фрагментированный прогноз";
    case "dirty_source_tree":
      return "Dirty provenance";
    default:
      return code.replaceAll(
        "_",
        " ",
      );
  }
}


function reliabilityFactorMessage(
  code: string,
  fallback: string,
): string {
  switch (code) {
    case "calibration_non_identifiable":
      return "По данным t0→t1 параметры D и ρ не были однозначно заключены внутри исследованной области параметров.";
    case "diffusion_at_boundary":
      return "Выбранный коэффициент диффузии находится на границе исследованной сетки.";
    case "proliferation_at_boundary":
      return "Выбранная скорость пролиферации находится на границе исследованной сетки.";
    case "prediction_empty":
      return "Зафиксированный прогноз не содержит положительных опухолевых вокселей.";
    case "prediction_outside_t1_brain":
      return "Часть зафиксированного прогноза лежит вне brain mask, доступной на t1.";
    case "prediction_fragmented":
      return "Прогноз состоит из нескольких пространственно разделённых компонент.";
    case "dirty_source_tree":
      return "Прогноз был зафиксирован из рабочего дерева с незакоммиченными изменениями.";
    default:
      return fallback;
  }
}


type MetricProps = {
  title: string;
  value: string;
  help: string;
};


function Metric({
  title,
  value,
  help,
}: MetricProps) {
  return (
    <article
      className="twin-explained-metric"
    >
      <span>
        {title}
      </span>

      <strong>
        {value}
      </strong>

      <p>
        {help}
      </p>
    </article>
  );
}


type MethodRowProps = {
  name: string;

  metrics:
    TwinMethodMetrics;

  emphasis?: boolean;
};


function MethodRow({
  name,
  metrics,
  emphasis = false,
}: MethodRowProps) {
  return (
    <tr
      className={
        emphasis
          ? "emphasis"
          : undefined
      }
    >
      <td>
        {name}
      </td>

      <td>
        {
          metrics.dice
          .toFixed(3)
        }
      </td>

      <td>
        {
          (
            metrics
            .relative_volume_error
            * 100
          ).toFixed(1)
        }
        %
      </td>

      <td>
        {
          metrics.hd95_mm
          === null
            ? "—"
            : (
              metrics.hd95_mm
              .toFixed(1)
              + " мм"
            )
        }
      </td>
    </tr>
  );
}


export default TwinOverviewTab;
