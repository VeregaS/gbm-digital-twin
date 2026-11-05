# GBM Digital Twin — MVP Protocol V2

Status: **Frozen development protocol**

Dataset: **CFB-GBM Version 4**

Project scope: **research prototype**

This document defines the scientific and engineering contract for the
minimal viable patient-specific glioblastoma digital twin.

The purpose of this protocol is to prevent data leakage, post-hoc tuning,
silent changes in evaluation methodology, and accidental expansion of the
project scope before the core longitudinal forecasting problem has been
evaluated.

---

## 1. Research objective

The MVP tests whether a patient-specific mechanistic model calibrated from
longitudinal MRI can forecast future glioblastoma extent better than simple
baselines.

For one patient, the canonical temporal sequence is:

```text
t0
 |
 | calibration interval
 v
t1
 |
 | forecast interval
 v
t2
```

The model may use information available up to and including `t1` to produce
a forecast for the time of `t2`.

The actual `t2` tumour observation is held out until the prediction artifact
has been frozen.

The MVP is a research system.

It is not:

* a clinical decision-support system;
* a treatment recommendation system;
* a diagnostic system;
* a surgical planning system;
* a validated medical device.

---

## 2. Canonical MVP workflow

The canonical patient workflow is:

```text
CFB-GBM metadata
        |
        v
patient eligibility
        |
        v
prepare t0
        |
        v
prepare t1
        |
        v
calibrate D and rho on t0 -> t1
        |
        v
assimilate observed t1 state
        |
        v
predict t1 -> target day
        |
        v
SEALED PREDICTION ARTIFACT
        |
        | only after sealing
        v
load observed t2
        |
        v
held-out evaluation
        |
        v
compare Digital Twin with baselines
```

`t2` imaging must not enter the prediction workflow before the prediction
artifact is sealed.

---

## 3. Dataset

The development dataset is:

```text
CFB-GBM
Version: 4
TCIA
```

The machine-readable dataset contract is stored in:

```text
configs/datasets/cfb_gbm_v4.yaml
```

The local dataset must pass:

```powershell
python scripts/audit_cfb_dataset.py `
  --metadata-root "<metadata-root>" `
  --patients-root "<patients-root>"
```

Dataset metadata and prepared patient data have different roles.

The dataset manifest describes the complete source dataset.

Experiment configurations select the subset of patients that must be
materialized locally for a particular experiment.

Therefore, unselected CFB-GBM prediction candidates do not need to exist
under the local prepared `patients/` directory.

---

## 4. Development cohort

The current development cohort is defined by:

```text
configs/experiments/mini_cohort.yaml
```

The initial mini-cohort contains:

```text
8
18
25
42
65
99
108
112
214
251
```

This cohort is a development cohort, not an external validation cohort.

Patients may later be excluded from a specific treatment-aware experiment
when required treatment information cannot be reconstructed reliably.

An exclusion must always have an explicit reason.

Examples:

```text
treatment_schedule_unavailable
missing_required_timepoint
missing_required_modality
invalid_geometry
missing_gtv
missing_brain_mask
```

An unavailable treatment schedule must not silently be interpreted as
absence of treatment.

---

## 5. Scientific model

The core tumour model is a reaction-diffusion model:

$$
\frac{\partial c}{\partial t}
=
\nabla \cdot (D \nabla c)
+
\rho c(1-c)
$$

where:

* $c(x,t)$ is the latent tumour cell-density field;
* $D$ is the effective isotropic diffusion coefficient;
* $\rho$ is the proliferation rate.

For MVP V2:

```text
D: isotropic
D: spatially homogeneous
rho: spatially homogeneous
boundary: no-flux
domain: brain-constrained
```

The MVP must not add additional biological complexity before the deterministic
benchmark has been evaluated.

In particular, the following are outside the MVP:

```text
DTI-derived anisotropic diffusion
white/grey matter-specific diffusion
biomechanical mass effect
PET-derived tumour state
radiomics-driven parameters
deep-learning tumour dynamics
Bayesian parameter inference
```

---

## 6. Latent tumour state

Observed GTV masks are not treated as a perfect representation of the
continuous tumour cell-density field.

The current V2 model constructs a continuous latent state from the observed
GTV using a signed-distance based transition.

Frozen V2 latent-state width:

```text
4.0 mm
```

This value must not be tuned using held-out `t2`.

---

## 7. Observation model

The continuous prediction field is converted into an observable tumour mask
using a fixed threshold.

Frozen V2 observation threshold:

```text
0.5
```

During calibration, a differentiable soft objective may be used to reduce
hard-threshold plateaus.

Frozen V2 soft calibration temperature:

```text
0.05
```

Final held-out evaluation uses hard binary masks.

Neither the observation threshold nor the soft temperature may be changed
based on `t2` results for V2.

---

## 8. Calibration

Patient-specific model parameters are calibrated using only:

```text
t0 -> t1
```

The primary calibrated parameters are:

```text
D
rho
```

The calibration objective may use:

```text
tumour overlap
tumour volume agreement
```

Current frozen volume-loss weight:

```text
0.5
```

Calibration must not use:

```text
t2 MRI
t2 GTV
t2 Dice
t2 volume error
t2 spatial error
```

Good calibration performance does not imply good forecast performance.

Calibration quality and forecast quality must therefore be reported
separately.

---

## 9. Calibration search

V2 uses grid-based calibration with local adaptive refinement.

The refinement algorithm may expand beyond the initial grid when the best
parameter lies on a search boundary.

However, refinement must remain finite and auditable.

Future workflow-level diagnostics should report whether the final optimum is
still located at a search boundary.

The intended diagnostic fields are:

```text
diffusion_at_boundary
proliferation_at_boundary
diffusion_bracketed
proliferation_bracketed
identifiable
```

These diagnostics are protocol requirements for the canonical cohort
evaluation, even if they are not yet fully implemented.

---

## 10. Treatment model

Because CFB-GBM longitudinal intervals may overlap radiotherapy, V2 retains
a treatment-aware model.

Radiotherapy survival follows the linear-quadratic model:

$$
S =
\exp(-\alpha d - \beta d^2)
$$

The tumour-state update for one fraction is:

$$
c
\leftarrow
c -
(1-S)c(1-c)
$$

followed by clipping to the valid tumour-state interval.

Frozen V2 treatment parameters:

```text
effective alpha: 0.01 / Gy
alpha/beta ratio: 10 Gy
```

These values must not be tuned using `t2`.

The current CFB treatment representation has important limitations:

* exact fraction dates may be unavailable;
* fraction schedules may need reconstruction;
* radiotherapy is represented spatially homogeneously;
* available RTDOSE maps are not part of MVP V2;
* chemotherapy exposure is not reliably represented;
* absence of reconstructable treatment metadata does not imply absence of
  treatment.

The MVP must not claim that radiotherapy is the only biological intervention
affecting tumour evolution.

---

## 11. Assimilation at t1

After calibrating on `t0 -> t1`, the state used for forward prediction is
re-initialized from the actual observed `t1` tumour.

Canonical V2 assimilation rule:

```text
replace_with_observed_t1_latent_state
```

Therefore:

```text
calibration:
t0 -> t1

prediction initial condition:
observed t1

forecast:
t1 -> target day
```

The forecast does not simply continue the simulated calibration trajectory.

---

## 12. Anti-leakage rule

The fundamental MVP rule is:

> `t2` observations must not influence model construction or prediction.

Before prediction sealing, the system may know:

```text
patient ID
t0 data
t1 data
treatment metadata allowed by the protocol
target timepoint name
target day
prediction horizon
```

Before prediction sealing, the system must not access:

```text
t2 T1Gd
t2 GTV
t2 tumour volume
t2 Dice
t2 spatial metrics
```

The prediction API should therefore accept a prediction target description,
not a prepared `t2` imaging object.

Conceptually:

```text
PredictionTarget
    timepoint_name
    target_day
```

is allowed.

A complete prepared `t2` patient study is not allowed in the prediction
phase.

---

## 13. Frozen prediction artifact

A prediction must be serialized before `t2` evaluation.

The current prediction artifact contains:

```text
prediction_field.npy
prediction_mask.npy
persistence_mask.npy
volume_baseline_mask.npy
manifest
```

The artifact must be:

```text
sealed
immutable
checksummed
self-describing
```

The evaluator must reject:

```text
modified arrays
modified manifests
invalid checksums
invalid geometry
wrong patient
wrong target timepoint
wrong target day
incompatible protocol version
```

A frozen artifact must not be overwritten in place.

Any model change after revealing `t2` requires a new protocol/model version.

---

## 14. Required provenance

Before canonical cohort evaluation, the frozen artifact must contain enough
provenance to reconstruct exactly what generated it.

Required provenance includes:

```text
protocol version
model version
dataset name
dataset version
dataset DOI
patient ID
prediction horizon
D
rho
solver dt
latent width
observation threshold
soft calibration temperature
treatment parameters
assimilation rule
input geometry
Git commit SHA
configuration checksum
input-data checksums where practical
artifact creation timestamp
```

Absolute local Windows paths must not be used as scientific provenance.

---

## 15. Baselines

The digital twin must never be evaluated without simple baselines.

Two mandatory MVP baselines are:

### Persistence baseline

Assume that the observed `t1` tumour remains unchanged until `t2`.

Conceptually:

```text
prediction(t2) = observed GTV(t1)
```

### Volume extrapolation baseline

Construct a simple prediction using longitudinal tumour-volume change without
the mechanistic spatial model.

The purpose of this baseline is to test whether the mechanistic digital twin
provides information beyond simple volumetric continuation.

---

## 16. Held-out metrics

The canonical V2 evaluation must report at least four complementary metrics.

### Dice coefficient

Measures segmentation overlap.

### Relative volume error

Measures tumour-size error.

### HD95

95th percentile Hausdorff distance in millimetres.

Measures boundary disagreement while being less sensitive to isolated
outliers than maximum Hausdorff distance.

### Centroid distance

Euclidean distance between predicted and observed tumour centroids in
millimetres.

Measures spatial displacement error.

No single metric is sufficient to determine forecast quality.

---

## 17. Canonical cohort evaluation

The final CFB development-cohort evaluation must use a two-phase procedure.

### Phase A — freeze

For every eligible patient:

```text
load allowed t0/t1 data
calibrate
assimilate t1
predict to target day
create baselines
seal artifact
```

`t2` GTV must not be loaded during this phase.

All eligible patient predictions should be frozen before Phase B begins.

### Phase B — reveal

Only after Phase A is complete:

```text
load observed t2
evaluate sealed twin prediction
evaluate persistence
evaluate volume baseline
write patient result
```

This cohort-wide freeze-before-reveal rule prevents results from early
patients from influencing the model used for later patients.

---

## 18. Canonical cohort outputs

The canonical cohort workflow should produce:

```text
eligibility.csv
cohort_results.csv
cohort_summary.json
protocol_manifest.json
```

Per-patient results should include at least:

```text
patient_id
eligibility
exclusion_reason

D
rho

calibration_score
calibration_volume_error

prediction_dice
prediction_relative_volume_error
prediction_hd95_mm
prediction_centroid_distance_mm

persistence_dice
persistence_relative_volume_error
persistence_hd95_mm
persistence_centroid_distance_mm

volume_baseline_dice
volume_baseline_relative_volume_error
volume_baseline_hd95_mm
volume_baseline_centroid_distance_mm
```

The summary should include:

```text
number included
number excluded
exclusion reasons

mean
median
interquartile range

Twin minus baseline differences

wins
ties
losses
```

All eligible patients must be reported.

Patients must not be removed because their predictions are poor.

---

## 19. Interpretation of results

The MVP is considered scientifically complete when the protocol has been
executed correctly and reproducibly.

Success of the software does not require the digital twin to outperform
persistence.

Possible valid outcomes include:

```text
Twin > persistence
Twin ~= persistence
Twin < persistence
```

A negative result is still a valid research result.

If V2 performs poorly after held-out `t2` is revealed, V2 must remain frozen.

Subsequent model changes become:

```text
V3
```

They must not silently modify V2.

---

## 20. API scope

The MVP API is read-only with respect to scientific simulation.

Scientific computation is performed offline.

Canonical architecture:

```text
CLI / research workflow
        |
        v
sealed artifacts
        |
        v
FastAPI
        |
        v
frontend
```

The minimal MVP must not introduce:

```text
background worker queues
job scheduling
simulation cancellation
run orchestration API
distributed execution
generic research workspace
```

The future PatientTwin API should read already-created artifacts.

Conceptual endpoint:

```text
GET /api/patients/{patient_id}/twin
```

It should expose:

```text
patient ID
eligibility
workflow state
protocol version

D
rho
calibration metrics

prediction horizon
sealed status

Twin metrics
persistence metrics
volume-baseline metrics

warnings
```

Scientific model logic must not be duplicated in API route handlers.

---

## 21. Frontend scope

The frontend consumes the API only.

The minimal Digital Twin UI should show:

```text
patient
timeline
t0
t1
prediction horizon
t2

D
rho

protocol version
sealed status

observed MRI
observed GTV
predicted GTV
persistence baseline

evaluation metrics
research warnings
```

The UI must not hardcode scientific values.

The UI must not display fabricated confidence scores.

The UI must not make treatment recommendations.

The UI must not imply clinical validation.

---

## 22. Viewer and solver separation

Scientific simulation resolution and visualization resolution are separate
concerns.

The solver may operate on a resampled scientific grid, for example:

```text
2 mm isotropic
```

The viewer may use native or higher-resolution imaging.

Prediction fields may be resampled for visualization.

Viewer resampling must never feed back into scientific evaluation or model
calibration.

---

## 23. Anatomy subsystem

The current anatomy subsystem is experimental.

It is not a dependency of the MVP digital-twin workflow.

Global registration overlap metrics alone are insufficient evidence of
correct anatomical alignment.

The following work is explicitly deferred:

```text
further ANTs/SyN optimization
anatomical risk scoring
functional region modelling
tractography
DTI
fMRI
surgical guidance
```

Anatomy work may continue only after the core forecasting MVP is complete or
when required by a clearly identified forecasting failure mode.

---

## 24. External validation

CFB-GBM is the development dataset.

It is not sufficient for external validation.

The planned external-validation dataset is the Burdenko cohort.

Burdenko must not be used to tune the frozen CFB V2 protocol before the
development evaluation is complete.

External validation belongs to a later project stage.

---

## 25. Deferred uncertainty modelling

Parameter uncertainty and predictive uncertainty are scientifically important.

However, Bayesian calibration, MCMC, posterior ensembles, and probabilistic
forecasting are not MVP requirements.

The architecture should permit future uncertainty output, for example:

```text
uncertainty: null
```

in the current implementation.

Uncertainty modelling should be introduced when the deterministic benchmark
shows that parameter non-identifiability or prediction variability is a
material limitation.

---

## 26. MVP completion criteria

The research MVP is complete when all of the following are true:

1. CFB-GBM release is explicitly pinned.
2. Dataset structure can be audited reproducibly.
3. Experiment eligibility is deterministic.
4. Every exclusion has an explicit reason.
5. `t2` imaging cannot enter prediction before sealing.
6. `D` and `rho` are calibrated using only `t0 -> t1`.
7. V2 hyperparameters remain frozen.
8. Calibration boundary diagnostics are available.
9. Prediction artifacts are immutable and checksummed.
10. Persistence baseline is evaluated.
11. Volume extrapolation baseline is evaluated.
12. Dice is reported.
13. Relative volume error is reported.
14. HD95 is reported.
15. Centroid distance is reported.
16. Canonical cohort evaluation uses freeze-all then reveal-all.
17. Scientific provenance includes dataset and Git revision.
18. PatientTwin API reads frozen artifacts without recomputing them.
19. Digital Twin UI displays only backend-derived scientific values.
20. Full Python tests pass.
21. Ruff passes.
22. Frontend lint passes.
23. Frontend production build passes.
24. A clean checkout can reproduce the documented workflow.
25. No clinical-performance claim is made from the MVP.
26. Experimental anatomy is not required by the core workflow.

---

## 27. Out of scope for V2 MVP

The following must not delay completion of the core MVP:

```text
DTI anisotropy
white/grey matter diffusion
tractography
fMRI
PET
radiomics
deep-learning dynamics
spatial RTDOSE modelling
chemotherapy response modelling
treatment optimization
RANO outcome prediction
Bayesian inference
MCMC
external Burdenko validation
clinical decision support
surgical planning
job queues
generic run management
advanced anatomy modelling
```

These features may become future protocol versions only when justified by
observed failure modes of the frozen MVP.

---

## 28. Versioning rule

This document defines:

```text
MVP Protocol V2
```

Once held-out `t2` cohort results have been inspected, scientific changes to
the following create a new protocol version:

```text
PDE formulation
calibration objective
D search strategy
rho search strategy
latent-state width
observation threshold
soft calibration temperature
treatment parameters
assimilation rule
prediction initialization
baseline definitions
eligibility criteria
evaluation metrics
```

Bug fixes that do not change scientific semantics may remain within V2, but
must be documented and covered by tests.

When uncertain whether a change alters scientific semantics, treat it as a
new protocol version.

---

## 29. Development order from this baseline

The implementation order after this document is frozen is:

```text
1. eligibility and PredictionTarget contracts
2. prediction provenance
3. calibration diagnostics
4. PatientTwin workflow
5. single-patient end-to-end execution
6. canonical cohort freeze-all workflow
7. held-out cohort evaluation
8. additional spatial metrics
9. PatientTwin read-only API
10. Digital Twin frontend
11. reproducibility pass
12. research MVP release
```

Work should proceed in this order unless a blocking defect is discovered.

The core scientific workflow takes priority over anatomy, frontend expansion,
and infrastructure features.
