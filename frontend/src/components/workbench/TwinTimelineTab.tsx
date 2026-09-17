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
                  : (
                    "Unable to load "
                    + "timepoint"
                  ),
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
                : (
                  "Unable to load "
                  + "patient timeline"
                ),
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
        className={
          "twin-tab-state"
        }
      >
        Loading t0 / t1 / t2…
      </div>
    );
  }

  if (
    currentRequest.status
    === "error"
  ) {
    return (
      <div
        className={
          "twin-tab-state error"
        }
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
            Longitudinal story
          </span>

          <strong>
            Observe → calibrate →
            assimilate → forecast
          </strong>
        </div>

        <p>
          t0 and t1 describe the
          tumour before the held-out
          forecast target. The sealed
          Twin forecast starts from
          t1 and is evaluated only
          after observed t2 is revealed.
        </p>
      </section>

      <div
        className={
          "twin-temporal-grid"
        }
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
        className={
          "twin-time-intervals"
        }
      >
        <div>
          <span>
            Calibration interval
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
                  + " days"
                )
            }
          </strong>

          <small>
            t0 → t1
          </small>
        </div>

        <div>
          <span>
            Held-out horizon
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
                  + " days"
                )
            }
          </strong>

          <small>
            t1 → t2
          </small>
        </div>

        <div>
          <span>
            Radiotherapy start
          </span>

          <strong>
            {
              patient.treatment
              .rt_start_day
              === null
                ? "Unknown"
                : (
                  "Day "
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
                ? "schedule reconstructable"
                : "metadata incomplete"
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
      ? "Baseline observation"
      : item.timepoint.name === "t1"
        ? (
          "Assimilation / "
          + "forecast start"
        )
        : (
          "Held-out truth"
        );

  return (
    <article
      className={
        "twin-timepoint-card"
      }
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
              ? "Day —"
              : (
                "Day "
                + item
                .timepoint
                .days_from_baseline
                .toFixed(0)
              )
          }
        </b>
      </header>

      <div
        className={
          "twin-timepoint-image"
        }
      >
        {imageUrl !== null ? (
          <img
            src={imageUrl}
            alt={
              `${item.timepoint.name} `
              + "MRI with GTV"
            }
          />
        ) : (
          <span>
            {item.error
              ?? (
                "Image unavailable"
              )}
          </span>
        )}
      </div>

      <footer>
        <span>
          GTV volume
        </span>

        <strong>
          {metadata === null
            ? "—"
            : (
              metadata
              .gtv_volume_cm3
              .toFixed(2)
              + " cm³"
            )}
        </strong>
      </footer>

      {item.timepoint.name
      === "t2" && (
        <div
          className={
            "twin-heldout-note"
          }
        >
          Not used before
          prediction sealing
        </div>
      )}
    </article>
  );
}


export default TwinTimelineTab;