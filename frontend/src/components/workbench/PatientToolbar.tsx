import {
  Play,
} from "lucide-react";

import type {
  PatientListItem,
  PatientSummary,
} from "../../api/types";

import {
  formatDay,
} from "./formatters";


type PatientToolbarProps = {
  patients: PatientListItem[];

  selectedPatientId: number | null;
  patient: PatientSummary | null;

  patientsLoading: boolean;
  patientLoading: boolean;

  error: string | null;

  onSelectPatient: (
    patientId: number | null,
  ) => void;

  onOpenViewer: () => void;
};


function PatientToolbar({
  patients,
  selectedPatientId,
  patient,
  patientsLoading,
  patientLoading,
  error,
  onSelectPatient,
  onOpenViewer,
}: PatientToolbarProps) {
  const title = patientLoading
    ? "Loading patient…"
    : patient
      ? `Patient ${patient.patient_id}`
      : "No patient selected";

  const status = error
    ? "Data error"
    : patient
      ? `${patient.timepoint_count} timepoints`
      : patientsLoading
        ? "Loading dataset"
        : `${patients.length} patients available`;

  return (
    <section className="patient-toolbar">
      <div>
        <div className="section-eyebrow">
          Active patient
        </div>

        <div className="patient-row">
          <h2>{title}</h2>

          <span className="patient-status">
            {status}
          </span>
        </div>

        <p>
          {error
            ? error
            : patient
              ? patientDescription(
                  patient,
                )
              : (
                "Select a longitudinal "
                + "CFB-GBM patient to inspect "
                + "MRI, tumor segmentation "
                + "and digital twin predictions."
              )}
        </p>
      </div>

      <div className="patient-actions">
        <select
          className="secondary-button patient-select"
          aria-label="Select patient"
          disabled={
            patientsLoading
            || patients.length === 0
          }
          value={
            selectedPatientId
            ?? ""
          }
          onChange={(event) => {
            const value =
              event.target.value;

            onSelectPatient(
              value
                ? Number(value)
                : null,
            );
          }}
        >
          <option value="">
            {patientsLoading
              ? "Loading patients…"
              : "Select patient"}
          </option>

          {patients.map(
            (patientItem) => (
              <option
                key={
                  patientItem.patient_id
                }
                value={
                  patientItem.patient_id
                }
              >
                {patientItem.label}
              </option>
            ),
          )}
        </select>

        <button
          type="button"
          className="primary-button"
          disabled={
            patient === null
            || patientLoading
          }
          onClick={onOpenViewer}
        >
          <Play size={16} />
          Open viewer
        </button>
      </div>
    </section>
  );
}


function patientDescription(
  patient: PatientSummary,
): string {
  const intervals: string[] = [];

  if (patient.dt01_days !== null) {
    intervals.push(
      `t0→t1 ${formatDay(
        patient.dt01_days,
      )}`,
    );
  }

  if (patient.dt12_days !== null) {
    intervals.push(
      `t1→t2 ${formatDay(
        patient.dt12_days,
      )}`,
    );
  }

  const treatment = (
    patient.treatment.reconstructable
      ? "RT schedule reconstructable"
      : patient.treatment.has_record
        ? "RT metadata incomplete"
        : "RT metadata unavailable"
  );

  const intervalText =
    intervals.length > 0
      ? intervals.join(" · ")
      : "Longitudinal intervals unavailable";

  return `${intervalText} · ${treatment}`;
}


export default PatientToolbar;
