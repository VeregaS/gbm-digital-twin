import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import {
  Box,
  Columns3,
  Layers3,
  SplitSquareVertical,
} from "lucide-react";

import {
  twinCompareSliceUrl,
  twinSliceUrl,
} from "../../api/twin";

import type {
  TwinComparisonMode,
  TwinPatientEvaluation,
  TwinPredictionMethod,
} from "../../api/twin";

import type {
  ViewerPlane,
  ViewerVolumeMetadata,
} from "../../api/types";

import TwinThreeDViewer from "./TwinThreeDViewer";


type CompareMode =
  | "side_by_side"
  | TwinComparisonMode
  | "3d";


type TwinCompareTabProps = {
  patientId: number;

  evaluation:
    TwinPatientEvaluation;

  viewer:
    ViewerVolumeMetadata;
};


type LoadedPair = {
  key: string;
  observedUrl: string;
  predictionUrl: string;
};


type PairRequestState =
  | {
      status: "success";
      pair: LoadedPair;
    }
  | {
      status: "error";
      key: string;
      error: string;
    };


const methods: {
  value: TwinPredictionMethod;
  label: string;
}[] = [
  {
    value: "twin",
    label: "Цифровой двойник",
  },
  {
    value: "persistence",
    label: "Без изменений",
  },
  {
    value: "volume_baseline",
    label: "Прогноз по объёму",
  },
];


const planes:
  ViewerPlane[] = [
    "axial",
    "coronal",
    "sagittal",
  ];


function TwinCompareTab({
  patientId,
  evaluation,
  viewer,
}: TwinCompareTabProps) {
  const [
    method,
    setMethod,
  ] = useState<
    TwinPredictionMethod
  >(
    "twin",
  );

  const [
    mode,
    setMode,
  ] = useState<
    CompareMode
  >(
    "side_by_side",
  );

  const [
    plane,
    setPlane,
  ] = useState<
    ViewerPlane
  >(
    "axial",
  );

  const defaultPlane =
    viewer.planes.find(
      (item) =>
        item.name === plane,
    );

  const [
    sliceIndex,
    setSliceIndex,
  ] = useState(
    defaultPlane
    ?.default_index
    ?? 0,
  );

  const [
    pairRequest,
    setPairRequest,
  ] = useState<
    PairRequestState | null
  >(null);

  const pairUrlsRef =
    useRef<
      LoadedPair | null
    >(null);

  const planeMetadata =
    viewer.planes.find(
      (item) =>
        item.name === plane,
    )
    ?? null;

  const metrics =
    evaluation[method];

  const observedUrl =
    twinSliceUrl(
      patientId,
      "observed",
      plane,
      sliceIndex,
    );

  const predictionUrl =
    twinSliceUrl(
      patientId,
      method,
      plane,
      sliceIndex,
    );

  const pairKey =
    `${patientId}:${method}:${plane}:${sliceIndex}`;

  const comparisonUrl =
    mode === "overlay"
    || mode === "difference"
      ? twinCompareSliceUrl(
        patientId,
        method,
        mode,
        plane,
        sliceIndex,
      )
      : null;

  useEffect(() => {
    if (
      mode !== "side_by_side"
    ) {
      return;
    }

    const controller =
      new AbortController();

    Promise.all([
      fetchImageObjectUrl(
        observedUrl,
        controller.signal,
      ),
      fetchImageObjectUrl(
        predictionUrl,
        controller.signal,
      ),
    ])
      .then(
        ([
          nextObservedUrl,
          nextPredictionUrl,
        ]) => {
          if (
            controller.signal.aborted
          ) {
            URL.revokeObjectURL(
              nextObservedUrl,
            );

            URL.revokeObjectURL(
              nextPredictionUrl,
            );

            return;
          }

          const previous =
            pairUrlsRef.current;

          const nextPair: LoadedPair = {
            key: pairKey,
            observedUrl:
              nextObservedUrl,
            predictionUrl:
              nextPredictionUrl,
          };

          pairUrlsRef.current =
            nextPair;

          setPairRequest({
            status: "success",
            pair: nextPair,
          });

          if (previous !== null) {
            URL.revokeObjectURL(
              previous.observedUrl,
            );

            URL.revokeObjectURL(
              previous.predictionUrl,
            );
          }
        },
      )
      .catch(
        (requestError: unknown) => {
          if (
            controller.signal.aborted
          ) {
            return;
          }

          setPairRequest({
            status: "error",
            key: pairKey,
            error:
              requestError
              instanceof Error
                ? requestError.message
                : "Не удалось загрузить пару снимков",
          });
        },
      );

    return () => {
      controller.abort();
    };
  }, [
    mode,
    observedUrl,
    predictionUrl,
    pairKey,
  ]);

  useEffect(() => {
    return () => {
      const pair =
        pairUrlsRef.current;

      if (pair !== null) {
        URL.revokeObjectURL(
          pair.observedUrl,
        );

        URL.revokeObjectURL(
          pair.predictionUrl,
        );
      }
    };
  }, []);

  const displayedPair =
    pairRequest?.status
    === "success"
      ? pairRequest.pair
      : pairUrlsRef.current;

  const pairLoading =
    mode === "side_by_side"
    && displayedPair?.key
    !== pairKey;

  const pairError =
    pairRequest?.status
    === "error"
    && pairRequest.key
    === pairKey
      ? pairRequest.error
      : null;

  const methodLabel =
    methods.find(
      (item) =>
        item.value === method,
    )?.label
    ?? method;

  function changePlane(
    nextPlane: ViewerPlane,
  ) {
    setPlane(
      nextPlane,
    );

    const metadata =
      viewer.planes.find(
        (item) =>
          item.name
          === nextPlane,
      );

    setSliceIndex(
      metadata
      ?.default_index
      ?? 0,
    );
  }

  return (
    <div
      className="twin-tab-stack"
    >
      <section
        className="twin-compare-toolbar"
      >
        <div>
          <span>
            Метод прогноза
          </span>

          <div
            className="twin-chip-row"
          >
            {methods.map(
              (item) => (
                <button
                  key={item.value}
                  type="button"
                  className={
                    method
                    === item.value
                      ? "twin-chip active"
                      : "twin-chip"
                  }
                  onClick={() =>
                    setMethod(
                      item.value,
                    )
                  }
                >
                  {item.label}
                </button>
              ),
            )}
          </div>
        </div>

        <div>
          <span>
            Режим сравнения
          </span>

          <div
            className="twin-chip-row"
          >
            <ModeButton
              active={
                mode
                === "side_by_side"
              }
              label="Рядом"
              icon={Columns3}
              onClick={() =>
                setMode(
                  "side_by_side",
                )
              }
            />

            <ModeButton
              active={
                mode === "overlay"
              }
              label="Наложение"
              icon={Layers3}
              onClick={() =>
                setMode(
                  "overlay",
                )
              }
            />

            <ModeButton
              active={
                mode
                === "difference"
              }
              label="Ошибки"
              icon={
                SplitSquareVertical
              }
              onClick={() =>
                setMode(
                  "difference",
                )
              }
            />

            <ModeButton
              active={
                mode === "3d"
              }
              label="3D"
              icon={Box}
              onClick={() =>
                setMode(
                  "3d",
                )
              }
            />
          </div>
        </div>
      </section>

      <section
        className="twin-selected-method"
      >
        <MetricSummary
          label="Совпадение (Dice)"
          value={
            metrics.dice
            .toFixed(3)
          }
          hint="больше — лучше"
        />

        <MetricSummary
          label="Ошибка объёма"
          value={
            (
              metrics
              .relative_volume_error
              * 100
            ).toFixed(1)
            + "%"
          }
          hint="меньше — лучше"
        />

        <MetricSummary
          label="Ошибка границы (HD95)"
          value={
            metrics.hd95_mm
            === null
              ? "—"
              : (
                metrics.hd95_mm
                .toFixed(1)
                + " мм"
              )
          }
          hint="меньше — лучше"
        />
      </section>

      {mode !== "3d" && (
        <>
          <div
            className="twin-plane-toolbar"
          >
            {planes.map(
              (item) => (
                <button
                  key={item}
                  type="button"
                  className={
                    plane === item
                      ? "twin-chip active"
                      : "twin-chip"
                  }
                  onClick={() =>
                    changePlane(
                      item,
                    )
                  }
                >
                  {planeLabel(item)}
                </button>
              ),
            )}
          </div>

          {mode
          === "side_by_side" ? (
            <div
              className="twin-side-by-side-wrap"
            >
              <div
                className="twin-side-by-side"
              >
                <ComparisonImage
                  title="Реальная опухоль на t2"
                  subtitle="Отложенная сегментация, не использованная при прогнозе"
                  src={
                    displayedPair
                    ?.observedUrl
                    ?? null
                  }
                />

                <ComparisonImage
                  title={methodLabel}
                  subtitle="Зафиксированный прогноз состояния опухоли на t2"
                  src={
                    displayedPair
                    ?.predictionUrl
                    ?? null
                  }
                />
              </div>

              {(pairLoading
              || pairError !== null) && (
                <div
                  className={
                    pairError === null
                      ? "twin-pair-status"
                      : "twin-pair-status error"
                  }
                >
                  {pairError
                    ?? (
                      `Загружаем срез ${sliceIndex} синхронно для обеих панелей…`
                    )}
                </div>
              )}
            </div>
          ) : (
            <div
              className="twin-comparison-single"
            >
              {comparisonUrl
              !== null && (
                <img
                  src={comparisonUrl}
                  alt={
                    `${mode} ${method}`
                  }
                />
              )}

              {mode === "overlay" ? (
                <div
                  className="twin-compare-legend"
                >
                  <Legend
                    color="#ef5350"
                    label="Только реальная опухоль"
                  />

                  <Legend
                    color="#3b82f6"
                    label="Только прогноз"
                  />

                  <Legend
                    color="#a855f7"
                    label="Перекрытие"
                  />
                </div>
              ) : (
                <div
                  className="twin-compare-legend"
                >
                  <Legend
                    color="#10b981"
                    label="Верное совпадение"
                  />

                  <Legend
                    color="#3b82f6"
                    label="Ложноположительная область"
                  />

                  <Legend
                    color="#ef4444"
                    label="Пропущенная опухоль"
                  />
                </div>
              )}
            </div>
          )}

          {planeMetadata !== null && (
            <div
              className="twin-slider-row"
            >
              <span>
                0
              </span>

              <input
                type="range"
                min={0}
                max={
                  planeMetadata
                  .max_index
                }
                value={sliceIndex}
                aria-label="Номер среза"
                onChange={
                  (event) =>
                    setSliceIndex(
                      Number(
                        event
                        .target
                        .value,
                      ),
                    )
                }
              />

              <span>
                {
                  planeMetadata
                  .max_index
                }
              </span>

              <strong>
                срез {sliceIndex}
              </strong>
            </div>
          )}
        </>
      )}

      {mode === "3d" && (
        <div
          className="twin-3d-frame"
        >
          <TwinThreeDViewer
            patientId={patientId}
          />
        </div>
      )}
    </div>
  );
}


type MetricSummaryProps = {
  label: string;
  value: string;
  hint: string;
};


function MetricSummary({
  label,
  value,
  hint,
}: MetricSummaryProps) {
  return (
    <div>
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

      <small>
        {hint}
      </small>
    </div>
  );
}


type ComparisonImageProps = {
  title: string;
  subtitle: string;
  src: string | null;
};


function ComparisonImage({
  title,
  subtitle,
  src,
}: ComparisonImageProps) {
  return (
    <article
      className="twin-compare-image-card"
    >
      <header>
        <strong>
          {title}
        </strong>

        <span>
          {subtitle}
        </span>
      </header>

      <div>
        {src === null ? (
          <span
            className="twin-image-placeholder"
          >
            Загружаем снимок…
          </span>
        ) : (
          <img
            src={src}
            alt={title}
            draggable={false}
          />
        )}
      </div>
    </article>
  );
}


type ModeButtonProps = {
  active: boolean;
  label: string;

  icon:
    typeof Box;

  onClick:
    () => void;
};


function ModeButton({
  active,
  label,
  icon: Icon,
  onClick,
}: ModeButtonProps) {
  return (
    <button
      type="button"
      className={
        active
          ? "twin-chip active"
          : "twin-chip"
      }
      onClick={onClick}
    >
      <Icon
        size={13}
      />

      {label}
    </button>
  );
}


type LegendProps = {
  color: string;
  label: string;
};


function Legend({
  color,
  label,
}: LegendProps) {
  return (
    <span>
      <i
        style={{
          backgroundColor:
            color,
        }}
      />

      {label}
    </span>
  );
}


function planeLabel(
  plane: ViewerPlane,
): string {
  switch (plane) {
    case "axial":
      return "Аксиальная";
    case "coronal":
      return "Корональная";
    case "sagittal":
      return "Сагиттальная";
  }
}


async function fetchImageObjectUrl(
  url: string,
  signal: AbortSignal,
): Promise<string> {
  const response = await fetch(
    url,
    {
      signal,
      cache: "force-cache",
    },
  );

  if (!response.ok) {
    throw new Error(
      `Не удалось загрузить снимок: HTTP ${response.status}`,
    );
  }

  const blob = await response.blob();

  return URL.createObjectURL(
    blob,
  );
}


export default TwinCompareTab;
