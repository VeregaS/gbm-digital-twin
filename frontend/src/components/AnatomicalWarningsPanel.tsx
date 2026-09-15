import {
  AlertTriangle,
  BrainCircuit,
  CircleAlert,
  Info,
} from "lucide-react";

import {
  useEffect,
  useState,
} from "react";

import {
  fetchAnatomicalRisk,
} from "../api/client";

import type {
  AnatomicalRiskReport,
  AnatomicalWarning,
} from "../api/types";


type AnatomicalWarningsPanelProps = {
  patientId: number;
  timepointName: string;
};


type AnatomicalRiskRequestState =
  | {
      patientId: number;
      timepointName: string;
      status: "success";
      report: AnatomicalRiskReport;
    }
  | {
      patientId: number;
      timepointName: string;
      status: "error";
      error: string;
    };


function AnatomicalWarningsPanel({
  patientId,
  timepointName,
}: AnatomicalWarningsPanelProps) {
  const [
    request,
    setRequest,
  ] = useState<
    AnatomicalRiskRequestState | null
  >(null);


  useEffect(() => {
    let cancelled = false;

    fetchAnatomicalRisk(
      patientId,
      timepointName,
    )
      .then(
        (result) => {
          if (!cancelled) {
            setRequest({
              patientId,
              timepointName,
              status: "success",
              report: result,
            });
          }
        },
      )
      .catch(
        (
          requestError:
            unknown,
        ) => {
          if (cancelled) {
            return;
          }

          setRequest({
            patientId,
            timepointName,
            status: "error",
            error:
              requestError
                instanceof Error
                ? requestError.message
                : (
                  "Failed to load "
                  + "anatomical analysis"
                ),
          });
        },
      );

    return () => {
      cancelled = true;
    };
  }, [
    patientId,
    timepointName,
  ]);


  const currentRequest =
    request?.patientId === patientId
    && request.timepointName
      === timepointName
      ? request
      : null;

  const report =
    currentRequest?.status
    === "success"
      ? currentRequest.report
      : null;

  const error =
    currentRequest?.status
    === "error"
      ? currentRequest.error
      : null;

  const loading =
    currentRequest === null;


  return (
    <aside className="anatomy-panel">
      <div className="anatomy-panel-header">
        <div className="anatomy-panel-icon">
          <BrainCircuit
            size={16}
          />
        </div>

        <div>
          <span>
            Anatomical intelligence
          </span>

          <strong>
            Functional proximity
          </strong>
        </div>
      </div>


      {loading ? (
        <div className="anatomy-panel-state">
          Loading atlas analysis…
        </div>
      ) : error ? (
        <div className="anatomy-panel-state error">
          {error}
        </div>
      ) : report === null ? (
        <div className="anatomy-panel-state">
          No analysis available.
        </div>
      ) : !report.configured ? (
        <AtlasNotConfigured
          report={report}
        />
      ) : (
        <ConfiguredReport
          report={report}
        />
      )}
    </aside>
  );
}


function AtlasNotConfigured({
  report,
}: {
  report: AnatomicalRiskReport;
}) {
  return (
    <>
      <div className="atlas-unavailable">
        <Info
          size={16}
        />

        <div>
          <strong>
            Atlas analysis not configured
          </strong>

          <span>
            {
              report
                .status_message
            }
          </span>
        </div>
      </div>

      <div className="anatomy-disclaimer">
        {
          report.disclaimer
        }
      </div>
    </>
  );
}


function ConfiguredReport({
  report,
}: {
  report: AnatomicalRiskReport;
}) {
  if (
    report.warnings.length
    === 0
  ) {
    return (
      <>
        <div className="anatomy-clear">
          <BrainCircuit
            size={18}
          />

          <div>
            <strong>
              No configured atlas warnings
            </strong>

            <span>
              No overlap or proximity
              warning was triggered for
              the selected atlas regions.
            </span>
          </div>
        </div>

        <ReportFooter
          report={report}
        />
      </>
    );
  }

  return (
    <>
      <div className="anatomy-summary">
        <div>
          <span>
            High
          </span>

          <strong className="risk-high-text">
            {
              report.high_count
            }
          </strong>
        </div>

        <div>
          <span>
            Moderate
          </span>

          <strong className="risk-moderate-text">
            {
              report
                .moderate_count
            }
          </strong>
        </div>

        <div>
          <span>
            Atlas
          </span>

          <strong>
            {
              report.atlas_name
              ?? "Unknown"
            }
          </strong>
        </div>
      </div>


      <div className="anatomy-warning-list">
        {
          report.warnings.map(
            (warning) => (
              <WarningCard
                key={
                  `${warning.region_label}`
                  + `-${warning.severity}`
                }
                warning={
                  warning
                }
              />
            ),
          )
        }
      </div>


      <ReportFooter
        report={report}
      />
    </>
  );
}


function WarningCard({
  warning,
}: {
  warning: AnatomicalWarning;
}) {
  const high =
    warning.severity
    === "high";

  return (
    <article
      className={
        high
          ? (
            "anatomy-warning "
            + "high"
          )
          : (
            "anatomy-warning "
            + "moderate"
          )
      }
    >
      <div className="warning-icon">
        {high ? (
          <CircleAlert
            size={16}
          />
        ) : (
          <AlertTriangle
            size={16}
          />
        )}
      </div>

      <div className="warning-body">
        <div className="warning-title">
          <strong>
            {
              warning
                .region_name
            }
          </strong>

          <span>
            {
              warning.category
            }
          </span>
        </div>

        <p>
          {
            warning.message
          }
        </p>

        {
          warning
            .functional_note
          && (
            <p className="functional-note">
              {
                warning
                  .functional_note
              }
            </p>
          )
        }


        <div className="warning-metrics">
          {
            warning
              .observed_overlap_cm3
            > 0
            && (
              <span>
                GTV overlap{" "}
                <strong>
                  {
                    warning
                      .observed_overlap_cm3
                      .toFixed(2)
                  }
                  {" cm³"}
                </strong>
              </span>
            )
          }

          {
            warning
              .latent_overlap_cm3
            > 0
            && (
              <span>
                Latent overlap{" "}
                <strong>
                  {
                    warning
                      .latent_overlap_cm3
                      .toFixed(2)
                  }
                  {" cm³"}
                </strong>
              </span>
            )
          }

          {
            warning
              .min_observed_distance_mm
            !== null
            && (
              <span>
                Distance{" "}
                <strong>
                  {
                    warning
                      .min_observed_distance_mm
                      .toFixed(1)
                  }
                  {" mm"}
                </strong>
              </span>
            )
          }
        </div>
      </div>
    </article>
  );
}


function ReportFooter({
  report,
}: {
  report: AnatomicalRiskReport;
}) {
  return (
    <div className="anatomy-disclaimer">
      <strong>
        Research-only
      </strong>

      <span>
        {report.disclaimer}
      </span>

      <span>
        Latent display threshold:{" "}
        {
          report
            .latent_level
            .toFixed(2)
        }
        {" · "}
        proximity rule:{" "}
        {
          report
            .proximity_threshold_mm
            .toFixed(1)
        }
        {" mm"}
      </span>
    </div>
  );
}


export default AnatomicalWarningsPanel;
