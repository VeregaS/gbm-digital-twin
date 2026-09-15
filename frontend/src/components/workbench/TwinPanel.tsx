import type {
  PatientTreatment,
} from "../../api/types";


type TwinPanelProps = {
  treatment: PatientTreatment | null;
};


function TwinPanel({
  treatment,
}: TwinPanelProps) {
  return (
    <section className="panel twin-panel">
      <div className="panel-heading compact">
        <div>
          <div className="section-eyebrow">
            Model
          </div>

          <h3>Digital Twin</h3>
        </div>

        <span className="model-status">
          V2
        </span>
      </div>

      <div className="parameter-list">
        <ParameterRow
          label="Tumor state"
          value="Continuous latent"
        />

        <ParameterRow
          label="Growth model"
          value="Reaction–diffusion"
        />

        <ParameterRow
          label="RT model"
          value="PIRT"
        />

        <ParameterRow
          label="Effective α"
          value="0.01 /Gy"
        />

        <ParameterRow
          label="α / β"
          value="10 Gy"
        />

        <ParameterRow
          label="Latent width"
          value="4 mm"
        />

        <ParameterRow
          label="Observation threshold"
          value="0.5"
        />

        <ParameterRow
          label="Soft temperature"
          value="0.05"
        />

        <ParameterRow
          label="RT dose"
          value={
            treatment?.dose_gy
            !== null
            && treatment?.dose_gy
            !== undefined
              ? (
                `${treatment.dose_gy} Gy`
              )
              : "—"
          }
        />

        <ParameterRow
          label="RT fractions"
          value={
            treatment?.fractions
            !== null
            && treatment?.fractions
            !== undefined
              ? String(
                  treatment.fractions,
                )
              : "—"
          }
        />
      </div>

      <div className="protocol-note">
        <strong>
          Evaluation protocol
        </strong>

        <p>
          Parameters are calibrated on
          t0 → t1 only. Held-out t2 is
          reserved for final evaluation and
          must not influence model selection.
        </p>
      </div>
    </section>
  );
}


type ParameterRowProps = {
  label: string;
  value: string;
};


function ParameterRow({
  label,
  value,
}: ParameterRowProps) {
  return (
    <div className="parameter-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}


export default TwinPanel;
