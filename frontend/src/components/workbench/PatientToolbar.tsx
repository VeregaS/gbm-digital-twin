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

  onOpenViewer?: () => void;
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
    ? "Загрузка пациента…"
    : patient
      ? `Пациент ${patient.patient_id}`
      : "Пациент не выбран";

  const status = error
    ? "Ошибка данных"
    : patient
      ? `${patient.timepoint_count} временные точки`
      : patientsLoading
        ? "Загрузка набора данных"
        : `${patients.length} пациентов доступно`;

  return (
    <section className="patient-toolbar">
      <div>
        <div className="section-eyebrow">
          Выбранный пациент
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
                "Выберите пациента CFB-GBM, "
                + "чтобы изучить динамику МРТ, "
                + "сегментацию опухоли, лечение "
                + "и прогноз цифрового двойника."
              )}
        </p>
      </div>

      <div className="patient-actions">
        <select
          className="secondary-button patient-select"
          aria-label="Выбор пациента"
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
              ? "Загрузка пациентов…"
              : "Выберите пациента"}
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

        {onOpenViewer && (
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
            Открыть МРТ
          </button>
        )}
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
      ? "схема лучевой терапии восстановлена"
      : patient.treatment.has_record
        ? "данные о лучевой терапии неполные"
        : "данные о лучевой терапии отсутствуют"
  );

  const intervalText =
    intervals.length > 0
      ? intervals.join(" · ")
      : "интервалы наблюдения недоступны";

  return `${intervalText} · ${treatment}`;
}


export default PatientToolbar;
