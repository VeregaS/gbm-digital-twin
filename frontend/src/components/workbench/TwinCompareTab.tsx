import {
  useState,
} from "react";

import {
  Columns3,
  Layers3,
  SplitSquareVertical,
  Box,
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


const methods: {
  value: TwinPredictionMethod;
  label: string;
}[] = [
  {
    value: "twin",
    label: "Digital Twin",
  },
  {
    value: "persistence",
    label: "Persistence",
  },
  {
    value: "volume_baseline",
    label: "Volume baseline",
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

  const planeMetadata =
    viewer.planes.find(
      (item) =>
        item.name === plane,
    )
    ?? null;

  const metrics =
    evaluation[method];

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

  return (
    <div
      className={
        "twin-tab-stack"
      }
    >
      <section
        className={
          "twin-compare-toolbar"
        }
      >
        <div>
          <span>
            Method
          </span>

          <div
            className={
              "twin-chip-row"
            }
          >
            {methods.map(
              (item) => (
                <button
                  key={
                    item.value
                  }
                  type="button"
                  className={
                    method
                    === item.value
                      ? (
                        "twin-chip "
                        + "active"
                      )
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
            View
          </span>

          <div
            className={
              "twin-chip-row"
            }
          >
            <ModeButton
              active={
                mode
                === "side_by_side"
              }
              label="Side by side"
              icon={
                Columns3
              }
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
              label="Overlay"
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
              label="Difference"
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
        className={
          "twin-selected-method"
        }
      >
        <div>
          <span>
            Dice
          </span>

          <strong>
            {
              metrics.dice
              .toFixed(3)
            }
          </strong>
        </div>

        <div>
          <span>
            Volume error
          </span>

          <strong>
            {
              (
                metrics
                .relative_volume_error
                * 100
              ).toFixed(1)
            }
            %
          </strong>
        </div>

        <div>
          <span>
            HD95
          </span>

          <strong>
            {
              metrics.hd95_mm
              === null
                ? "—"
                : (
                  metrics.hd95_mm
                  .toFixed(1)
                  + " mm"
                )
            }
          </strong>
        </div>
      </section>

      {mode !== "3d" && (
        <>
          <div
            className={
              "twin-plane-toolbar"
            }
          >
            {planes.map(
              (item) => (
                <button
                  key={item}
                  type="button"
                  className={
                    plane === item
                      ? (
                        "twin-chip "
                        + "active"
                      )
                      : "twin-chip"
                  }
                  onClick={() =>
                    changePlane(
                      item,
                    )
                  }
                >
                  {item}
                </button>
              ),
            )}
          </div>

          {mode
          === "side_by_side" ? (
            <div
              className={
                "twin-side-by-side"
              }
            >
              <ComparisonImage
                title="Observed t2"
                subtitle="Held-out ground truth"
                src={observedUrl}
              />

              <ComparisonImage
                title={
                  methods.find(
                    (item) =>
                      item.value
                      === method,
                  )?.label
                  ?? method
                }
                subtitle={
                  "Sealed prediction "
                  + "for t2"
                }
                src={predictionUrl}
              />
            </div>
          ) : (
            <div
              className={
                "twin-comparison-single"
              }
            >
              {comparisonUrl
              !== null && (
                <img
                  src={
                    comparisonUrl
                  }
                  alt={
                    `${mode} `
                    + `${method}`
                  }
                />
              )}

              {mode === "overlay" ? (
                <div
                  className={
                    "twin-compare-legend"
                  }
                >
                  <Legend
                    color="#ef5350"
                    label={
                      "Observed only"
                    }
                  />

                  <Legend
                    color="#3b82f6"
                    label={
                      "Prediction only"
                    }
                  />

                  <Legend
                    color="#a855f7"
                    label="Overlap"
                  />
                </div>
              ) : (
                <div
                  className={
                    "twin-compare-legend"
                  }
                >
                  <Legend
                    color="#10b981"
                    label={
                      "Correct overlap"
                    }
                  />

                  <Legend
                    color="#3b82f6"
                    label={
                      "False positive"
                    }
                  />

                  <Legend
                    color="#ef4444"
                    label={
                      "False negative"
                    }
                  />
                </div>
              )}
            </div>
          )}

          {planeMetadata !== null && (
            <div
              className={
                "twin-slider-row"
              }
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
                value={
                  sliceIndex
                }
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
                slice
                {" "}
                {sliceIndex}
              </strong>
            </div>
          )}
        </>
      )}

      {mode === "3d" && (
        <div
          className={
            "twin-3d-frame"
          }
        >
          <TwinThreeDViewer
            patientId={
              patientId
            }
          />
        </div>
      )}
    </div>
  );
}


type ComparisonImageProps = {
  title: string;
  subtitle: string;
  src: string;
};


function ComparisonImage({
  title,
  subtitle,
  src,
}: ComparisonImageProps) {
  return (
    <article
      className={
        "twin-compare-image-card"
      }
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
        <img
          src={src}
          alt={title}
        />
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
          ? (
            "twin-chip "
            + "active"
          )
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


export default TwinCompareTab;