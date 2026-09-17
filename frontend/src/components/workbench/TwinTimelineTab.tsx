import {
  useEffect,
  useState,
} from "react";

import {
  fetchViewerMetadata,
  viewerSliceUrl,
} from "../../api/client";

import type {
  PatientSummary,
  PatientTimepoint,
  ViewerVolumeMetadata,
} from "../../api/types";


type TimelineItem = {
  timepoint:
    PatientTimepoint;

  metadata:
    ViewerVolumeMetadata | null;

  error:
    string | null;
};


type TimelineRequest =
  | {
      patientId: number;
      status: "success";
      items: TimelineItem[];
    }
  | {
      patientId: number;
      status: "error";
      error: string;
    };


type TwinTimelineTabProps = {
  patient:
    PatientSummary;
};


function TwinTimelineTab({
  patient,
}: TwinTimelineTabProps) {
  const [
    request,
    setRequest,
  ] = useState<
    TimelineRequest | null
  >(null);

  useEffect(() => {
    let cancelled = false;

    Promise.all(
      patient.timepoints.map(
        async (
          timepoint,
        ): Promise<TimelineItem> => {
          try {
            const metadata =
              await fetchViewerMetadata(
                patient.patient_id,
                timepoint.name,
              );

            return {
              timepoint,
              metadata,
              error: null,
            };

          } catch (
            requestError:
              unknown
          ) {
            return {
              timepoint,
              metadata: null,
              error:
                requestError
                instanceof Error
                  ? requestError.message
                  : "Не удалось загрузить временную точку",
            };
          }
        },
      ),
    )
      .then((items) => {
        if (cancelled) {
          return;
        }

        setRequest({
          patientId:
            patient.patient_id,
          status: "success",
          items,
        });
      })
      .catch(
        (requestError: unknown) => {
          if (cancelled) {
            return;
          }

          setRequest({
            patientId:
              patient.patient_id,
            status: "error",
            error:
              requestError
              instanceof Error
                ? requestError.message
                : "Не удалось загрузить динамику пациента",
          });
        },
      );

    return () => {
      cancelled = true;
    };
  }, [
    patient,
  ]);

  const currentRequest =
    request?.patientId
    === patient.patient_id
      ? request
      : null;

  if (
    currentRequest === null
  ) {
    return (
      <div
        className="twin-tab-state"
      >
        Загружаем t0 / t1 / t2…
      </div>
    );
  }

  if (
    currentRequest.status
    === "error"
  ) {
    return (
      <div
        className="twin-tab-state error"
      >
        {currentRequest.error}
      </div>
    );
  }

  const items = [
    ...currentRequest.items,
  ].sort(
    (first, second) =>
      (
        first.timepoint
        .days_from_baseline
        ?? 0
      )
      - (
        second.timepoint
        .days_from_baseline
        ?? 0
      ),
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
            Динамика опухоли
          </span>

          <strong>
            Наблюдение → калибровка → ассимиляция → прогноз
          </strong>
        </div>

        <p>
          t0 и t1 доступны модели до прогнозирования. На t1 фактическое наблюдение используется как новое исходное состояние цифрового двойника. После этого строится прогноз t2. Реальная t2 открывается только после фиксации прогноза.
        </p>
      </section>

      <div
        className="twin-temporal-grid"
      >
        {items.map(
          (item) => (
            <TimepointCard
              key={
                item
                .timepoint
                .name
              }
              patientId={
                patient.patient_id
              }
              item={item}
            />
          ),
        )}
      </div>

      <section
        className="twin-time-intervals"
      >
        <div>
          <span>
            Интервал калибровки
          </span>

          <strong>
            {
              patient.dt01_days
              === null
                ? "—"
                : (
                  patient
                  .dt01_days
                  .toFixed(0)
                  + " дней"
                )
            }
          </strong>

          <small>
            t0 → t1
          </small>
        </div>

        <div>
          <span>
            Горизонт прогноза
          </span>

          <strong>
            {
              patient.dt12_days
              === null
                ? "—"
                : (
                  patient
                  .dt12_days
                  .toFixed(0)
                  + " дней"
                )
            }
          </strong>

          <small>
            t1 → t2
          </small>
        </div>

        <div>
          <span>
            Начало лучевой терапии
          </span>

          <strong>
            {
              patient.treatment
              .rt_start_day
              === null
                ? "Неизвестно"
                : (
                  "День "
                  + patient
                  .treatment
                  .rt_start_day
                  .toFixed(0)
                )
            }
          </strong>

          <small>
            {
              patient.treatment
              .reconstructable
                ? "схема лечения восстановлена"
                : "метаданные лечения неполные"
            }
          </small>
        </div>
      </section>
    </div>
  );
}


type TimepointCardProps = {
  patientId: number;
  item: TimelineItem;
};


function TimepointCard({
  patientId,
  item,
}: TimepointCardProps) {
  const metadata =
    item.metadata;

  const axial =
    metadata?.planes.find(
      (plane) =>
        plane.name
        === "axial",
    );

  const imageUrl =
    metadata !== null
    && axial !== undefined
      ? viewerSliceUrl(
        patientId,
        item.timepoint.name,
        "axial",
        axial.default_index,
        true,
      )
      : null;

  const role =
    item.timepoint.name === "t0"
      ? "Исходное наблюдение"
      : item.timepoint.name === "t1"
        ? "Последнее наблюдение / старт прогноза"
        : "Реальная отложенная цель";

  return (
    <article
      className="twin-timepoint-card"
    >
      <header>
        <div>
          <strong>
            {
              item
              .timepoint
              .name
              .toUpperCase()
            }
          </strong>

          <span>
            {role}
          </span>
        </div>

        <b>
          {
            item.timepoint
            .days_from_baseline
            === null
              ? "День —"
              : (
                "День "
                + item
                .timepoint
                .days_from_baseline
                .toFixed(0)
              )
          }
        </b>
      </header>

      <div
        className="twin-timepoint-image"
      >
        {imageUrl !== null ? (
          <img
            src={imageUrl}
            alt={
              `${item.timepoint.name} МРТ с сегментацией GTV`
            }
          />
        ) : (
          <span>
            {item.error
              ?? "Снимок недоступен"}
          </span>
        )}
      </div>

      <footer>
        <span>
          Объём GTV
        </span>

        <strong>
          {metadata === null
            ? "—"
            : (
              metadata
              .gtv_volume_cm3
              .toFixed(2)
              + " см³"
            )}
        </strong>
      </footer>

      {item.timepoint.name
      === "t2" && (
        <div
          className="twin-heldout-note"
        >
          Не использовалась до фиксации прогноза
        </div>
      )}
    </article>
  );
}


export default TwinTimelineTab;
