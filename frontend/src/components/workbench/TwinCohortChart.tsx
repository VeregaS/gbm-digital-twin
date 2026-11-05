import type {
  TwinPatientEvaluation,
} from "../../api/twin";


type TwinCohortChartProps = {
  patients:
    TwinPatientEvaluation[];
};


type SeriesKey =
  | "twin"
  | "persistence"
  | "volume_baseline";


type SeriesDefinition = {
  key: SeriesKey;
  label: string;
  className: string;
};


const series: SeriesDefinition[] = [
  {
    key: "twin",
    label: "Twin",
    className: "twin-chart-series-twin",
  },
  {
    key: "persistence",
    label: "Persistence",
    className: (
      "twin-chart-series-persistence"
    ),
  },
  {
    key: "volume_baseline",
    label: "Volume baseline",
    className: (
      "twin-chart-series-volume"
    ),
  },
];


const width = 900;
const height = 280;

const paddingLeft = 48;
const paddingRight = 20;
const paddingTop = 18;
const paddingBottom = 38;

const plotWidth =
  width
  - paddingLeft
  - paddingRight;

const plotHeight =
  height
  - paddingTop
  - paddingBottom;


function clampDice(
  value: number,
): number {
  return Math.min(
    1,
    Math.max(
      0,
      value,
    ),
  );
}


function TwinCohortChart({
  patients,
}: TwinCohortChartProps) {
  const ordered = [
    ...patients,
  ].sort(
    (
      first,
      second,
    ) =>
      first.patient_id
      - second.patient_id,
  );

  if (ordered.length === 0) {
    return (
      <div
        className={
          "twin-chart-empty"
        }
      >
        No cohort metrics available.
      </div>
    );
  }

  function xFor(
    index: number,
  ): number {
    if (ordered.length === 1) {
      return (
        paddingLeft
        + plotWidth / 2
      );
    }

    return (
      paddingLeft
      + (
        index
        / (
          ordered.length - 1
        )
      ) * plotWidth
    );
  }

  function yFor(
    dice: number,
  ): number {
    return (
      paddingTop
      + (
        1
        - clampDice(dice)
      ) * plotHeight
    );
  }

  const gridValues = [
    0,
    0.25,
    0.5,
    0.75,
    1,
  ];

  return (
    <div
      className={
        "twin-chart-wrapper"
      }
    >
      <div
        className={
          "twin-chart-legend"
        }
      >
        {series.map(
          (item) => (
            <span
              key={item.key}
            >
              <i
                className={
                  item.className
                }
              />

              {item.label}
            </span>
          ),
        )}
      </div>

      <svg
        className={
          "twin-chart-svg"
        }
        viewBox={
          `0 0 ${width} ${height}`
        }
        role="img"
        aria-label={
          "Per-patient Dice "
          + "comparison"
        }
      >
        {gridValues.map(
          (value) => {
            const y =
              yFor(value);

            return (
              <g
                key={value}
              >
                <line
                  className={
                    "twin-chart-grid"
                  }
                  x1={
                    paddingLeft
                  }
                  x2={
                    width
                    - paddingRight
                  }
                  y1={y}
                  y2={y}
                />

                <text
                  className={
                    "twin-chart-axis"
                  }
                  x={
                    paddingLeft - 8
                  }
                  y={y + 4}
                  textAnchor="end"
                >
                  {value.toFixed(2)}
                </text>
              </g>
            );
          },
        )}

        {series.map(
          (item) => {
            const points =
              ordered.map(
                (
                  patient,
                  index,
                ) => (
                  `${xFor(index)},`
                  + `${yFor(
                    patient[
                      item.key
                    ].dice,
                  )}`
                ),
              )
              .join(" ");

            return (
              <g
                key={item.key}
                className={
                  item.className
                }
              >
                <polyline
                  className={
                    "twin-chart-line"
                  }
                  points={points}
                />

                {ordered.map(
                  (
                    patient,
                    index,
                  ) => (
                    <circle
                      key={
                        patient
                        .patient_id
                      }
                      className={
                        "twin-chart-point"
                      }
                      cx={
                        xFor(index)
                      }
                      cy={
                        yFor(
                          patient[
                            item.key
                          ].dice,
                        )
                      }
                      r={3.3}
                    >
                      <title>
                        {
                          `Patient ${
                            patient
                            .patient_id
                          }: ${
                            item.label
                          } Dice ${
                            patient[
                              item.key
                            ].dice
                            .toFixed(3)
                          }`
                        }
                      </title>
                    </circle>
                  ),
                )}
              </g>
            );
          },
        )}

        <text
          className={
            "twin-chart-axis"
          }
          x={paddingLeft}
          y={
            height - 8
          }
        >
          Patient
          {" "}
          {
            ordered[0]
            ?.patient_id
          }
        </text>

        <text
          className={
            "twin-chart-axis"
          }
          x={
            width
            - paddingRight
          }
          y={
            height - 8
          }
          textAnchor="end"
        >
          Patient
          {" "}
          {
            ordered[
              ordered.length - 1
            ]?.patient_id
          }
        </text>
      </svg>
    </div>
  );
}


export default TwinCohortChart;