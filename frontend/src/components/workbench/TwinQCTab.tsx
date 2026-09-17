import {
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";

import type {
  TwinMaskQC,
  TwinPatientQC,
} from "../../api/twin";


type TwinQCTabProps = {
  qc:
    TwinPatientQC | null;

  error:
    string | null;
};


function TwinQCTab({
  qc,
  error,
}: TwinQCTabProps) {
  if (
    error !== null
  ) {
    return (
      <div
        className={
          "twin-tab-state error"
        }
      >
        QC unavailable:
        {" "}
        {error}
      </div>
    );
  }

  if (qc === null) {
    return (
      <div
        className={
          "twin-tab-state"
        }
      >
        Loading technical QC…
      </div>
    );
  }

  return (
    <div
      className={
        "twin-tab-stack"
      }
    >
      <section
        className={
          qc.warnings.length === 0
            ? (
              "twin-qc-status "
              + "clear"
            )
            : (
              "twin-qc-status "
              + "warning"
            )
        }
      >
        {qc.warnings.length === 0 ? (
          <CheckCircle2
            size={20}
          />
        ) : (
          <AlertTriangle
            size={20}
          />
        )}

        <div>
          <strong>
            {qc.warnings.length === 0
              ? (
                "No automated "
                + "geometry warnings"
              )
              : (
                `${qc.warnings.length} `
                + "automated QC "
                + "warning(s)"
              )}
          </strong>

          <span>
            These checks describe
            masks and geometry only.
            They are not clinical
            quality assessments.
          </span>
        </div>
      </section>

      {qc.warnings.length > 0 && (
        <section
          className={
            "twin-qc-warning-list"
          }
        >
          {qc.warnings.map(
            (warning) => (
              <article
                key={
                  warning.code
                }
              >
                <AlertTriangle
                  size={16}
                />

                <div>
                  <strong>
                    {
                      warning.code
                      .replaceAll(
                        "_",
                        " ",
                      )
                    }
                  </strong>

                  <span>
                    {
                      warning.message
                    }
                  </span>
                </div>
              </article>
            ),
          )}
        </section>
      )}

      <section
        className={
          "twin-qc-grid"
        }
      >
        <MaskCard
          title="Observed t2"
          qc={qc.observed}
        />

        <MaskCard
          title="Digital Twin"
          qc={qc.twin}
        />

        <MaskCard
          title="Persistence"
          qc={qc.persistence}
        />

        <MaskCard
          title="Volume baseline"
          qc={
            qc.volume_baseline
          }
        />
      </section>
    </div>
  );
}


type MaskCardProps = {
  title: string;
  qc: TwinMaskQC;
};


function MaskCard({
  title,
  qc,
}: MaskCardProps) {
  return (
    <article
      className={
        "twin-qc-card"
      }
    >
      <header>
        <strong>
          {title}
        </strong>

        <span>
          {qc.volume_cm3
          .toFixed(2)}
          {" cm³"}
        </span>
      </header>

      <dl>
        <div>
          <dt>
            Components
          </dt>

          <dd>
            {qc.component_count}
          </dd>
        </div>

        <div>
          <dt>
            Largest component
          </dt>

          <dd>
            {
              qc
              .largest_component_fraction
              === null
                ? "—"
                : (
                  (
                    qc
                    .largest_component_fraction
                    * 100
                  ).toFixed(1)
                  + "%"
                )
            }
          </dd>
        </div>

        <div>
          <dt>
            Outside brain
          </dt>

          <dd>
            {
              qc
              .outside_brain_fraction
              === null
                ? "—"
                : (
                  (
                    qc
                    .outside_brain_fraction
                    * 100
                  ).toFixed(2)
                  + "%"
                )
            }
          </dd>
        </div>

        <div>
          <dt>
            Centroid in brain
          </dt>

          <dd>
            {
              qc
              .centroid_inside_brain
              === null
                ? "—"
                : qc
                  .centroid_inside_brain
                    ? "Yes"
                    : "No"
            }
          </dd>
        </div>
      </dl>
    </article>
  );
}


export default TwinQCTab;