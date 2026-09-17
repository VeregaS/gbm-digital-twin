import {
  ArrowLeft,
  UserRound,
} from "lucide-react";

import type {
  PatientSummary,
} from "../../api/types";


type PatientContextBarProps = {
  patient:
    PatientSummary;

  onChangePatient:
    () => void;
};


function PatientContextBar({
  patient,
  onChangePatient,
}: PatientContextBarProps) {
  return (
    <section
      className={
        "patient-context-bar"
      }
    >
      <div
        className={
          "patient-context-main"
        }
      >
        <div
          className={
            "patient-context-icon"
          }
        >
          <UserRound
            size={17}
          />
        </div>

        <div>
          <span>
            Active patient
          </span>

          <strong>
            Patient
            {" "}
            {patient.patient_id}
          </strong>
        </div>
      </div>

      <div
        className={
          "patient-context-timepoints"
        }
      >
        {patient.timepoints.map(
          (timepoint) => (
            <span
              key={
                timepoint.name
              }
            >
              {
                timepoint
                .name
                .toUpperCase()
              }

              {timepoint
              .days_from_baseline
              !== null && (
                <>
                  {" · day "}
                  {
                    timepoint
                    .days_from_baseline
                    .toFixed(0)
                  }
                </>
              )}
            </span>
          ),
        )}
      </div>

      <button
        type="button"
        className={
          "secondary-button"
        }
        onClick={
          onChangePatient
        }
      >
        <ArrowLeft
          size={14}
        />

        Change patient
      </button>
    </section>
  );
}


export default PatientContextBar;