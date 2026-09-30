import {
  BrainCircuit,
  CircleAlert,
  CircleCheck,
  Info,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";

import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  fetchTwinAnatomicalImpact,
  prepareTwinAnatomicalImpact,
} from "../../api/twin";

import type {
  TwinAnatomicalChange,
  TwinAnatomicalImpact,
  TwinAnatomicalRegionImpact,
} from "../../api/twin";


type TwinAnatomyTabProps = {
  patientId: number;
};


type RequestState =
  | {
      patientId: number;
      status: "preparing";
    }
  | {
      patientId: number;
      status: "success";
      report: TwinAnatomicalImpact;
    }
  | {
      patientId: number;
      status: "error";
      error: string;
    };


function needsPreparation(
  report: TwinAnatomicalImpact,
): boolean {
  return (
    !report.configured
    && report.status_message.includes(
      "not prepared yet",
    )
  );
}


function delay(
  milliseconds: number,
): Promise<void> {
  return new Promise(
    (resolve) => {
      window.setTimeout(
        resolve,
        milliseconds,
      );
    },
  );
}


function TwinAnatomyTab({
  patientId,
}: TwinAnatomyTabProps) {
  const [
    request,
    setRequest,
  ] = useState<
    RequestState | null
  >(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        let report =
          await fetchTwinAnatomicalImpact(
            patientId,
          );

        if (
          !cancelled
          && needsPreparation(
            report
          )
        ) {
          setRequest({
            patientId,
            status: "preparing",
          });

          await prepareTwinAnatomicalImpact(
            patientId,
          );

          for (
            let attempt = 0;
            attempt < 180;
            attempt += 1
          ) {
            if (cancelled) {
              return;
            }

            await delay(
              2000,
            );

            report =
              await fetchTwinAnatomicalImpact(
                patientId,
              );

            if (
              !needsPreparation(
                report
              )
            ) {
              break;
            }
          }
        }

        if (!cancelled) {
          setRequest({
            patientId,
            status: "success",
            report,
          });
        }
      } catch (
        requestError: unknown
      ) {
        if (cancelled) {
          return;
        }

        setRequest({
          patientId,
          status: "error",
          error:
            requestError
              instanceof Error
                ? requestError.message
                : (
                  "Не удалось загрузить "
                  + "анатомический прогноз"
                ),
        });
      }
    };

    void load();

    return () => {
      cancelled = true;
    };
  }, [
    patientId,
  ]);

  const currentRequest =
    request?.patientId
    === patientId
      ? request
      : null;

  if (
    currentRequest === null
  ) {
    return (
      <section
        className="twin-tab-state"
      >
        Загружаем функциональные области…
      </section>
    );
  }

  if (
    currentRequest.status
    === "preparing"
  ) {
    return (
      <section
        className="twin-tab-state"
      >
        Подготавливаем atlas preview и регистрацию t1. Интерфейс остаётся доступным; результат появится автоматически.
      </section>
    );
  }

  if (
    currentRequest.status
    === "error"
  ) {
    return (
      <section
        className="twin-tab-state error"
      >
        {currentRequest.error}
      </section>
    );
  }

  const report =
    currentRequest.report;

  if (!report.configured) {
    return (
      <div
        className="twin-tab-stack"
      >
        <section
          className="twin-anatomy-unavailable"
        >
          <Info
            size={19}
          />

          <div>
            <strong>
              Функциональный анализ пока недоступен
            </strong>

            <p>
              {report.status_message}
            </p>

            <span>
              Automatic-QC preview разрешён только для исследовательского отображения. Регистрации с QC fail или вручную отклонённые регистрации не используются.
            </span>
          </div>
        </section>

        <ResearchDisclaimer
          text={
            report.disclaimer
          }
        />
      </div>
    );
  }

  return (
    <ConfiguredImpact
      report={report}
    />
  );
}


function ConfiguredImpact({
  report,
}: {
  report: TwinAnatomicalImpact;
}) {
  const newChanges =
    useMemo(
      () =>
        report.changes.filter(
          (item) =>
            item.status
            === "new",
        ),
      [
        report.changes,
      ],
    );

  const persistentChanges =
    useMemo(
      () =>
        report.changes.filter(
          (item) =>
            item.status
            === "persistent",
        ),
      [
        report.changes,
      ],
    );

  return (
    <div
      className="twin-tab-stack"
    >
      <section
        className="twin-anatomy-heading"
      >
        <div
          className="twin-anatomy-heading-main"
        >
          <div
            className="twin-anatomy-icon"
          >
            <BrainCircuit
              size={20}
            />
          </div>

          <div>
            <span>
              Population atlas · research only
            </span>

            <strong>
              Функциональные области: сейчас и по прогнозу
            </strong>

            <p>
              Сравнение наблюдаемой опухоли на {report.current_timepoint.toUpperCase()} с зафиксированным прогнозом на {report.forecast_timepoint.toUpperCase()} выполняется в одном и том же пространстве принятого t1-атласа.
            </p>
          </div>
        </div>

        <div
          className="twin-anatomy-registration"
        >
          <ShieldCheck
            size={17}
          />

          <div>
            <strong>
              {
                report.registration.verified
                  ? "Регистрация проверена"
                  : "Предварительная регистрация"
              }
            </strong>

            <span>
              {report.registration.decision ?? "—"}
              {" · QC "}
              {report.registration.automatic_qc_status ?? "—"}
            </span>
          </div>
        </div>
      </section>

      {!report.registration.verified && (
        <section
          className="twin-anatomy-unavailable"
        >
          <Info
            size={19}
          />

          <div>
            <strong>
              Автоматический atlas preview
            </strong>

            <p>
              Регистрация прошла автоматический QC и используется только для исследовательского предпросмотра.
            </p>

            <span>
              До ручного review этот результат не считается verified anatomical registration.
            </span>
          </div>
        </section>
      )}

      <section
        className="twin-anatomy-summary-grid"
      >
        <SummaryCard
          label="Сейчас"
          value={
            report.current.length
          }
          detail={
            report.current_timepoint.toUpperCase()
            + " · области с пересечением или близостью"
          }
        />

        <SummaryCard
          label="Прогноз"
          value={
            report.forecast.length
          }
          detail={
            report.forecast_timepoint.toUpperCase()
            + " · atlas-defined области"
          }
        />

        <SummaryCard
          label="Новые по прогнозу"
          value={
            newChanges.length
          }
          detail="Не отмечались на t1, но появляются в frozen forecast"
          emphasis={
            newChanges.length > 0
          }
        />

        <SummaryCard
          label="Сохраняются"
          value={
            persistentChanges.length
          }
          detail="Отмечены и сейчас, и в прогнозируемой области"
        />
      </section>

      {newChanges.length > 0 && (
        <section
          className="twin-anatomy-new-risk"
        >
          <div
            className="twin-anatomy-section-title"
          >
            <TriangleAlert
              size={17}
            />

            <div>
              <strong>
                Новые области в прогнозе
              </strong>

              <span>
                Это пространственное пересечение с population atlas, а не прогноз неврологического дефицита.
              </span>
            </div>
          </div>

          <div
            className="twin-anatomy-change-list"
          >
            {newChanges.map(
              (change) => (
                <ChangeCard
                  key={
                    change.region_label
                  }
                  change={change}
                />
              ),
            )}
          </div>
        </section>
      )}

      <section
        className="twin-anatomy-columns"
      >
        <ImpactColumn
          title="Сейчас"
          subtitle={
            "Наблюдаемая опухоль · "
            + report.current_timepoint.toUpperCase()
          }
          items={
            report.current
          }
          emptyText="На выбранных atlas-defined областях предупреждений для текущего состояния нет."
          forecast={false}
        />

        <ImpactColumn
          title="Прогноз"
          subtitle={
            "Frozen twin · "
            + report.forecast_timepoint.toUpperCase()
          }
          items={
            report.forecast
          }
          emptyText="В frozen forecast выбранные atlas-defined области не достигают заданного порога предупреждения."
          forecast
        />
      </section>

      <section
        className="twin-anatomy-method-note"
      >
        <CircleCheck
          size={16}
        />

        <div>
          <strong>
            Контроль утечки
          </strong>

          <span>
            Для прогнозной колонки используется prediction field зафиксированного цифрового двойника. Реальная анатомия опухоли на t2 в этом анализе не используется.
          </span>
        </div>
      </section>

      <ResearchDisclaimer
        text={
          report.disclaimer
        }
      />
    </div>
  );
}


function SummaryCard({
  label,
  value,
  detail,
  emphasis = false,
}: {
  label: string;
  value: number;
  detail: string;
  emphasis?: boolean;
}) {
  return (
    <article
      className={
        emphasis
          ? (
            "twin-anatomy-summary-card "
            + "emphasis"
          )
          : "twin-anatomy-summary-card"
      }
    >
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

      <small>
        {detail}
      </small>
    </article>
  );
}


function ImpactColumn({
  title,
  subtitle,
  items,
  emptyText,
  forecast,
}: {
  title: string;
  subtitle: string;
  items:
    TwinAnatomicalRegionImpact[];
  emptyText: string;
  forecast: boolean;
}) {
  return (
    <section
      className="twin-anatomy-column"
    >
      <header>
        <div>
          <strong>
            {title}
          </strong>

          <span>
            {subtitle}
          </span>
        </div>

        <b>
          {items.length}
        </b>
      </header>

      {items.length === 0 ? (
        <div
          className="twin-anatomy-empty"
        >
          {emptyText}
        </div>
      ) : (
        <div
          className="twin-anatomy-impact-list"
        >
          {items.map(
            (item) => (
              <ImpactCard
                key={
                  item.region_label
                }
                item={item}
                forecast={
                  forecast
                }
              />
            ),
          )}
        </div>
      )}
    </section>
  );
}


function ImpactCard({
  item,
  forecast,
}: {
  item:
    TwinAnatomicalRegionImpact;
  forecast: boolean;
}) {
  const high =
    item.severity === "high";

  return (
    <article
      className={
        high
          ? (
            "twin-anatomy-impact "
            + "high"
          )
          : (
            "twin-anatomy-impact "
            + "moderate"
          )
      }
    >
      <div
        className="twin-anatomy-impact-icon"
      >
        {high ? (
          <CircleAlert
            size={15}
          />
        ) : (
          <TriangleAlert
            size={15}
          />
        )}
      </div>

      <div
        className="twin-anatomy-impact-body"
      >
        <div
          className="twin-anatomy-impact-title"
        >
          <div>
            <strong>
              {item.region_name}
            </strong>

            <span>
              {categoryLabel(
                item.category
              )}
              {item.laterality
                ? (
                  " · "
                  + lateralityLabel(
                    item.laterality
                  )
                )
                : ""}
            </span>
          </div>

          <b>
            {high
              ? "пересечение"
              : "близость"}
          </b>
        </div>

        {item.functional_note && (
          <p>
            {item.functional_note}
          </p>
        )}

        <div
          className="twin-anatomy-metrics"
        >
          {item.mask_overlap_cm3 > 0 && (
            <span>
              {forecast
                ? "Прогнозируемое пересечение"
                : "GTV пересечение"}
              {" "}
              <strong>
                {item.mask_overlap_cm3.toFixed(2)} см³
              </strong>
            </span>
          )}

          {item.density_overlap_cm3 > 0 && (
            <span>
              Область density ≥ threshold{" "}
              <strong>
                {item.density_overlap_cm3.toFixed(2)} см³
              </strong>
            </span>
          )}

          {item.min_distance_mm !== null && (
            <span>
              Мин. расстояние{" "}
              <strong>
                {item.min_distance_mm.toFixed(1)} мм
              </strong>
            </span>
          )}
        </div>
      </div>
    </article>
  );
}


function ChangeCard({
  change,
}: {
  change: TwinAnatomicalChange;
}) {
  return (
    <article>
      <BrainCircuit
        size={15}
      />

      <div>
        <strong>
          {change.region_name}
        </strong>

        <span>
          {categoryLabel(
            change.category
          )}
          {change.laterality
            ? (
              " · "
              + lateralityLabel(
                change.laterality
              )
            )
            : ""}
        </span>
      </div>
    </article>
  );
}


function ResearchDisclaimer({
  text,
}: {
  text: string;
}) {
  return (
    <section
      className="twin-anatomy-disclaimer"
    >
      <Info
        size={16}
      />

      <div>
        <strong>
          Исследовательская интерпретация
        </strong>

        <span>
          {text}
        </span>
      </div>
    </section>
  );
}


function categoryLabel(
  category: string,
): string {
  switch (
    category
      .trim()
      .toLowerCase()
  ) {
    case "language":
      return "Речь и язык";
    case "motor":
      return "Двигательная функция";
    case "somatosensory":
      return "Соматосенсорная функция";
    case "visual":
      return "Зрение";
    case "memory":
      return "Память";
    case "critical_subcortical":
    case "subcortical":
      return "Подкорковые структуры";
    default:
      return category;
  }
}


function lateralityLabel(
  value: string,
): string {
  switch (
    value
      .trim()
      .toLowerCase()
  ) {
    case "left":
      return "слева";
    case "right":
      return "справа";
    case "bilateral":
      return "двусторонняя";
    default:
      return value;
  }
}


export default TwinAnatomyTab;
