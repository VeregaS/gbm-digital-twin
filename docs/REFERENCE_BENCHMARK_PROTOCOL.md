# Published Reference Benchmark

## Why this stage exists

Stage 9 improved the exposed development cohort relative to the exact Stage 8
control, especially in regression cases, but it did not beat persistence and
its selected damaged-state half-life ran into the predefined 120-day ceiling.

Before adding another latent state, the project now benchmarks its predictive
pipeline against a published open research implementation:

**TumorTwin** by the Oncology Modeling Group.

Upstream repository:

`https://github.com/OncologyModelingGroup/TumorTwin`

Pinned upstream commit:

`bedf90a6d47ba48cf5cdb25901967d84730061d1`

TumorTwin is not vendored into this repository. Its upstream project uses a UT
Austin research license and prohibits commercial use without permission. The
benchmark installs the pinned package into a separate local virtual
environment.

## What is compared

The benchmark uses the same 24 already exposed Stage 9 development patients.

For every patient it uses the same:

- CFB t0/t1/t2 geometry;
- brain mask;
- MRI-to-density observation map currently used by this project;
- treatment schedule;
- LQ alpha and alpha/beta ratio from the sealed Stage 8 model;
- target t2;
- persistence baseline;
- Dice, relative-volume error, HD95, and centroid-distance metrics.

Two TumorTwin modes are evaluated.

### TumorTwin frozen-kinetics

Uses the patient-specific D and rho already frozen in the sealed Stage 8/9
artifacts.

This isolates differences caused by:

- the published TumorTwin reaction-diffusion implementation;
- its RK4 / torchdiffeq integration;
- its direct LQ radiotherapy survival update.

It does not ask whether TumorTwin has a better inverse problem.

### TumorTwin LM calibration

Re-estimates D and rho from t0 -> t1 using the upstream TumorTwin
Levenberg-Marquardt implementation, then assimilates the observed t1 density
and predicts t2.

The t2 outcome is not passed to the optimizer.

This mode tests whether the published inverse-problem implementation improves
over this project's grid/refinement calibration.

## Important limitation

The first benchmark is deliberately apples-to-apples with the data that are
already materialized locally.

It does **not** yet reproduce the full HGG TumorTwin tutorial because that
workflow relies on ADC-derived cellularity and enhancing/non-enhancing MRI
regions.

The benchmark therefore records:

`adc_cellularity_used = false`.

This distinction is mandatory when interpreting the result. A poor result from
the reference benchmark would not mean that the full published mpMRI workflow
is poor; it would mean that its solver/calibration machinery did not solve the
current GTV-derived observation problem better.

## Isolated installation

From repository root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\reference\bootstrap_tumortwin.ps1
```

This creates:

```text
.reference\tumortwin-venv\
```

and installs exactly the pinned upstream commit.

The main project virtual environment is not modified. This is necessary because
the upstream package pins older numerical dependencies than the current project.

## Local multimodal MRI audit

Before deciding whether to reproduce the full ADC/FLAIR workflow, inventory
what is actually present locally:

```powershell
python scripts\twin\audit_mpmri_availability.py `
  --repo-root . `
  --data-audit-root results\cohort\stage8-data-audit-v1 `
  --output-dir results\cohort\mpmri-availability-v1
```

The audit reads filenames only. It does not load NIfTI image contents and does
not reveal a new validation target.

Outputs:

- `mpmri_availability.json`;
- `mpmri_availability.csv`.

The main counts of interest are:

- longitudinal T1Gd;
- longitudinal FLAIR;
- longitudinal ADC;
- longitudinal T1Gd + FLAIR;
- longitudinal T1Gd + ADC.

## Reference benchmark execution

After the isolated environment has been installed:

```powershell
python scripts\twin\benchmark_reference_models.py `
  --repo-root . `
  --stage8-selection-root results\cohort\stage8-model-selection-v1 `
  --stage9-selection-root results\cohort\stage9-delayed-selection-v2 `
  --tumortwin-python .reference\tumortwin-venv\Scripts\python.exe `
  --cache-root results\cache\reference-tumortwin-v1 `
  --output-dir results\cohort\reference-benchmark-v1
```

By default this runs both frozen-kinetics and LM-calibrated modes.

For a faster first smoke benchmark:

```powershell
python scripts\twin\benchmark_reference_models.py `
  --repo-root . `
  --stage9-selection-root results\cohort\stage9-delayed-selection-v2 `
  --frozen-only `
  --output-dir results\cohort\reference-benchmark-frozen-v1
```

## Decision tree after the benchmark

### Published solver wins with frozen D/rho

Then the numerical/treatment implementation is a major source of error. Do not
continue Stage 10 until the solver discrepancy is understood.

### Published LM calibration wins while frozen mode does not

Then the main bottleneck is the inverse problem / parameter estimation. The next
development stage should focus on differentiable or least-squares calibration
and uncertainty rather than adding biology.

### Neither reference mode beats the current Stage 9 model

Then the dominant bottleneck is more likely the observation/data model.
Priority moves to the multimodal MRI branch, especially ADC-derived
cellularity and T1Gd/FLAIR compartment information where locally available.

### Reference and Stage 9 are both below persistence

Do not interpret this as failure of all digital-twin approaches. It means the
current CFB observation protocol does not yet provide enough information for
these model variants to beat a strong short-horizon persistence baseline.

## Leakage rule

This benchmark is development-only.

It must not consume:

- Stage 9 reserve patients;
- untouched CFB holdout;
- Burdenko external-validation outcomes.

A new reserve cohort is opened only after the reference benchmark identifies
which modeling layer should be changed and that change is frozen.
