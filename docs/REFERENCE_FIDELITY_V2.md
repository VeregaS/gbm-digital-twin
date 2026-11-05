# Reference Fidelity v2 — ROI and pre-t2 ADC diagnostic

## Motivation

Reference benchmark v1 showed that both the pinned TumorTwin solver with frozen
kinetics and the upstream LM calibration remained below the current Stage 9
model and below persistence on the same 24 exposed development patients.

That result was useful but not yet a high-fidelity reproduction of the
published HGG workflow because v1:

- used the project's GTV-derived density field;
- did not use ADC-derived cellularity;
- calibrated on the full prepared brain grid instead of a tumor-centric ROI.

Reference Fidelity v2 closes these two major methodological gaps before any new
latent treatment state is introduced.

## Leakage contract

This diagnostic uses only the same 24 patients whose t2 outcomes are already
development-exposed.

No reserve patient, untouched CFB holdout, or Burdenko target may be opened.

For every patient, all reference calculations are completed and cached before
that patient's t2 GTV is loaded for evaluation.

ADC is allowed only at t0 and t1. The workflow explicitly does not require or
load t2 ADC.

## Experiment A — ROI-cropped GTV observation

All 24 exposed Stage 9 patients are recalibrated with upstream TumorTwin LM.

The input observation remains the current GTV-derived latent-density field so
this experiment changes only the inverse-problem spatial support.

The crop is:

- union of t0 and t1 GTV;
- 10 voxels of padding by default;
- clipped to the prepared image bounds.

The exact padding is recorded in the artifact and can be overridden only as an
explicit diagnostic parameter.

## Experiment B — ADC-derived enhancing cellularity

The paired ADC experiment is run only for exposed Stage 9 patients with both
t0 and t1 ADC materialized locally.

Current expected local subset:

`25, 45, 65, 70, 76, 99, 112, 120, 214`

ADC is resampled directly to the already prepared T1Gd reference grid.

The cellularity transform mirrors the pinned TumorTwin implementation:

- determine the water-reference scale from ADC magnitude;
- within the enhancing GTV ROI use
  `abs((ADCW - ADC) / ADCW)`;
- clip to `[0, 1]`.

The code also implements TumorTwin's fixed non-enhancing density `0.16`, but
Reference Fidelity v2 does **not** use it because CFB currently provides raw
FLAIR rather than a verified non-enhancing tumor ROI.

Therefore this experiment must be described as:

**TumorTwin-style ADC-derived enhancing-cellularity diagnostic**

and not as a full reproduction of the Hormuth two-species HGG model.

## FLAIR rule

Raw FLAIR intensity is never converted into tumor cellularity by an invented
threshold.

FLAIR will be incorporated only after a defensible non-enhancing-region
segmentation or observation model is defined and tested.

## Calibration and solver

Both v2 experiments use the same pinned upstream TumorTwin commit as v1:

`bedf90a6d47ba48cf5cdb25901967d84730061d1`

Reference configuration remains:

- ReactionDiffusion3D;
- TorchDiffEq RK4;
- timestep <= 0.5 day;
- upstream Levenberg-Marquardt optimizer;
- D bounds `[0, 2]`;
- rho bounds `[0, 0.5]`;
- initial guess near `D=0.025`, `rho=0.05`;
- default 8 LM iterations;
- same reconstructed RT schedule and sealed Stage 8 radiobiology.

No t2 quantity participates in parameter fitting.

## Evaluation

The prediction is restored from the cropped ROI to the full prepared image
grid before evaluation.

For the GTV-derived mode the existing Stage 8 enhancing detection threshold is
kept, so the ROI experiment isolates cropping/calibration support. For the
ADC-derived cellularity mode, binary tumor volume is evaluated at the pinned
TumorTwin postprocessing default threshold `0.5`. This threshold is fixed
before the diagnostic and is not selected from t2.

Metrics remain exactly comparable to previous stages:

- Dice;
- relative volume error;
- HD95 mm;
- centroid distance mm;
- delta vs persistence;
- delta vs exact Stage 9 patient result.

The artifact reports three summaries:

- `tumortwin-lm-roi` on all 24;
- `tumortwin-lm-roi-adc-paired-subset` on the ADC-eligible subset;
- `tumortwin-adc-lm-roi` on the same paired subset.

The paired summaries are the primary evidence for whether the published-style
ADC observation pipeline adds useful information. Because the ADC and GTV
pipelines use their respective predeclared observation thresholds, this is a
pipeline-level comparison rather than a pure single-variable ablation.

## Decision rule

If ROI cropping materially improves the GTV reference result, the inverse
problem spatial support was a major fidelity issue and calibration should be
reworked before Stage 10.

If ADC improves the paired subset relative to ROI-GTV without increasing
catastrophic failures, priority moves to a richer MRI observation layer and
patient-specific image-informed state construction.

If neither ROI cropping nor ADC materially helps, the evidence for changing
the mechanistic treatment/state model becomes stronger and Stage 10 can be
reconsidered.

This is still development evidence. It cannot be called independent
validation.

## One-shot execution

After pulling the implementation:

    powershell -ExecutionPolicy Bypass -File scripts\reference\run_reference_fidelity_checkpoint.ps1 -SkipBootstrap

The script runs the targeted pytest suite, Ruff on the whole repository, the
pinned TumorTwin smoke test, and then Reference Fidelity v2.

Outputs:

- `results/cohort/reference-fidelity-v2/reference_fidelity.json`;
- `results/cohort/reference-fidelity-v2/reference_fidelity.sha256`;
- `results/cohort/reference-fidelity-v2/reference_fidelity.csv`.

The run is resumable through:

`results/cache/reference-fidelity-v2`
