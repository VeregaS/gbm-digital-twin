import type {
  PatientSummary,
} from "../../api/types";

import type {
  TwinCohort,
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
};


function TwinOverviewTab({
  patient,
  evaluation,
  cohort,
}: TwinOverviewTabProps) {
  const diceDelta = (
    evaluation.twin.dice
    - evaluation.persistence.dice
  );

  const outcomeText =
    Math.abs(diceDelta) < 1e-12
      ? (
        "Twin and persistence "
        + "have equal Dice."
      )
      : diceDelta > 0
        ? (
          "Twin overlaps observed t2 "
          + "more than persistence by "
          + diceDelta.toFixed(3)
          + " Dice."
        )
        : (
          "Persistence overlaps observed "
          + "t2 more than Twin by "
          + Math.abs(
            diceDelta
          ).toFixed(3)
          + " Dice."
        );

  return (
    <div
      className={
        "twin-tab-stack"
      }
    >
      <section
        className={
          "twin-explanation-card"
        }
      >
        <div>
          <span>
            What was predicted?
          </span>

          <strong>
            t1 → t2 tumour extent
          </strong>
        </div>

        <p>
          The model was calibrated
          using observations before
          the forecast target.
          Observed t2 was held out
          until the prediction had
          been sealed.
        </p>
      </section>

      <section
        className={
          "twin-patient-metric-grid"
        }
      >
        <Metric
          title="Dice"
          value={
            evaluation.twin.dice
            .toFixed(3)
          }
          help={
            "Spatial overlap with "
            + "observed t2. "
            + "Higher is better."
          }
        />

        <Metric
          title="Volume error"
          value={
            (
              evaluation.twin
              .relative_volume_error
              * 100
            ).toFixed(1)
            + "%"
          }
          help={
            "Absolute tumour-volume "
            + "error relative to "
            + "observed t2. "
            + "Lower is better."
          }
        />

        <Metric
          title="HD95"
          value={
            evaluation.twin
            .hd95_mm === null
              ? "—"
              : (
                evaluation.twin
                .hd95_mm
                .toFixed(1)
                + " mm"
              )
          }
          help={
            "95th-percentile surface "
            + "distance. "
            + "Lower is better."
          }
        />

        <Metric
          title="Centroid distance"
          value={
            evaluation.twin
            .centroid_distance_mm
            === null
              ? "—"
              : (
                evaluation.twin
                .centroid_distance_mm
                .toFixed(1)
                + " mm"
              )
          }
          help={
            "Distance between predicted "
            + "and observed lesion "
            + "centres. Lower is better."
          }
        />
      </section>

      <section
        className={
          "twin-readable-summary"
        }
      >
        <strong>
          Result in plain language
        </strong>

        <p>
          {outcomeText}
        </p>

        <span>
          Cohort Twin mean Dice:
          {" "}
          {
            cohort.twin.mean_dice
            ?.toFixed(3)
            ?? "—"
          }
        </span>
      </section>

      <section
        className={
          "twin-method-card"
        }
      >
        <div
          className={
            "twin-panel-heading"
          }
        >
          <div>
            <strong>
              Methods
            </strong>

            <span>
              Same held-out observed
              t2 target
            </span>
          </div>
        </div>

        <table
          className={
            "twin-method-table"
          }
        >
          <thead>
            <tr>
              <th>
                Method
              </th>

              <th>
                Dice
              </th>

              <th>
                Volume error
              </th>

              <th>
                HD95
              </th>
            </tr>
          </thead>

          <tbody>
            <MethodRow
              name="Digital Twin"
              metrics={
                evaluation.twin
              }
              emphasis
            />

            <MethodRow
              name="Persistence"
              metrics={
                evaluation.persistence
              }
            />

            <MethodRow
              name="Volume baseline"
              metrics={
                evaluation
                .volume_baseline
              }
            />
          </tbody>
        </table>
      </section>

      <section
        className={
          "twin-protocol-strip"
        }
      >
        <div>
          <strong>
            t0
          </strong>

          <span>
            baseline observation
          </span>
        </div>

        <b>
          calibration
        </b>

        <div>
          <strong>
            t1
          </strong>

          <span>
            assimilation + forecast start
          </span>
        </div>

        <b>
          sealed prediction
        </b>

        <div>
          <strong>
            t2
          </strong>

          <span>
            held-out evaluation target
          </span>
        </div>
      </section>

      <div
        className={
          "twin-context-note"
        }
      >
        Patient
        {" "}
        {patient.patient_id}
        {" · "}
        {
          patient.timepoint_count
        }
        {" observations · "}
        {
          patient.treatment
          .reconstructable
            ? (
              "RT schedule "
              + "reconstructable"
            )
            : (
              "RT metadata "
              + "not reconstructable"
            )
        }
      </div>
    </div>
  );
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
      className={
        "twin-explained-metric"
      }
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
              + " mm"
            )
        }
      </td>
    </tr>
  );
}


export default TwinOverviewTab;