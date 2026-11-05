# Next accuracy cycle — MRI observation model gate

## Status

This protocol is **conditional**.

2026-10-05 checkpoint: the frozen Stage 10 candidate failed its separate
[reserve validation](STAGE10_VALIDATION_RESULT.md). The permitted current work
is [failure analysis without reserve tuning](STAGE10_RESERVE_FAILURE_ANALYSIS.md).
This does not automatically activate or change the conditional gate below;
a revised development cycle requires an explicitly defined protocol.

It may be activated only when the sealed Stage 10 artifact reports:

`decision = no_decoupled_candidate_advanced`.

If a Stage 10 decoupled candidate advances, this cycle remains paused until the
selected Stage 10 structure is frozen and its reserve-validation plan is
written.

The purpose of this gate is to prevent post-hoc expansion of the treatment
model after Stage 10.

## Scientific rationale

Stage 8/9 and Reference Fidelity v2 indicate that predictive error is not
explained simply by:

- solver replacement;
- tumor-centric ROI cropping;
- direct TumorTwin-style ADC-to-cellularity initialization.

The next development cycle therefore targets the **MRI observation layer**:
the mapping between latent tumor state and what is visible on MRI.

This is distinct from adding more reaction-diffusion or radiotherapy states.

## Frozen quantities

The first observation-model cycle must keep the following frozen:

- patient split;
- Stage 8 D/rho calibration protocol;
- selected treatment-model structure;
- radiobiology;
- t0/t1 calibration window;
- t2 reveal/evaluation procedure;
- persistence and volume baselines.

No reserve or untouched-holdout t2 may be used for observation-model tuning.

## Phase A — pre-t2 multimodal audit

Before fitting any new observation parameter, create a sealed development audit
using only inputs available by t1.

For every exposed development patient record:

- T1Gd availability at t0/t1;
- FLAIR availability at t0/t1;
- ADC availability at t0/t1;
- image geometry and affine compatibility;
- registration/resampling provenance;
- missingness pattern;
- usable brain-mask intersection;
- intensity-QC summary.

Do not load t2 ADC or t2 FLAIR for candidate construction.

## Phase B — observation representations

### T1Gd control

The exact frozen current observation model remains the control.

### FLAIR

Raw FLAIR intensity thresholding is prohibited.

A FLAIR branch may advance to modeling only when a defensible segmentation or
probabilistic observation source is available with explicit provenance and QC.

The representation must distinguish:

- enhancing T1Gd-visible tumor;
- non-enhancing / edema-associated signal;
- uncertainty in what part of FLAIR represents infiltrative tumor.

### ADC

The failed Reference Fidelity v2 transform

`abs((ADCW - ADC) / ADCW)`

must not be reused as a direct replacement for the latent tumor field.

ADC may be tested only as **additional information**, for example as a bounded
pre-t2 feature that modulates an observation prior or uncertainty estimate.
It must not introduce patient-specific parameters fitted against t2.

## Phase C — uncertainty before new complexity

Before adding another mechanistic state, expose uncertainty caused by
calibration non-identifiability.

The first uncertainty implementation should:

- retain multiple near-optimal D/rho solutions from t0→t1 calibration;
- forecast each member independently;
- report central prediction plus voxelwise/volume uncertainty;
- use no t2 information when constructing the ensemble.

This does not replace point-estimate evaluation; it adds calibration-aware
interpretability.

## Advancement rule

A new observation representation may advance only if, on the already exposed
development cohort:

1. catastrophic failures do not increase;
2. mean and median Dice improve against the frozen model or remain within a
   pre-specified negligible tolerance while HD95/RVE materially improve;
3. improvement is not driven by one or two outliers;
4. regression and growth subgroups do not show a material trade-off;
5. the representation has a defensible pre-t2 interpretation;
6. no threshold or mapping constant was selected using t2.

If these conditions are not met, retain the simpler observation model.

## Reserve gate

Reserve patients remain sealed until:

- Stage 10 decision is sealed;
- the observation representation is frozen;
- all global parameters and thresholds are fixed;
- the uncertainty construction is fixed;
- the reserve analysis script is reviewed and reproducible.

Only then may internal validation on new patients begin.
