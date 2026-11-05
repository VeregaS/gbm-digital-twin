# Stage 9 — delayed radiation-response digital twin

## Status

Stage 8 internal validation did not improve the selected model over persistence
on the first sealed 16-patient validation cohort. Stage 9 is therefore a new
development version. The Stage 8 validation patients are now development
patients for Stage 9, while the original untouched holdout remains sealed.

Stage 9 is a mechanistic ablation, not a post-hoc patient-specific rescue.
Patient-specific diffusion and proliferation parameters (D and rho) are frozen
at the values already produced by Stage 8. Only the global treatment-response
state model is changed.

## Motivation from the Stage 8 failure

The Stage 8 state contains tumor density plus a persistent proliferation
modifier. After the final RT fraction, the modifier can slow future growth but
cannot by itself represent a population that remains MRI-visible at t1 and is
then gradually removed after t1.

This is important for post-radiotherapy glioblastoma imaging. A decrease in
enhancing volume after RT does not imply that all of the corresponding tissue
was instantaneously removed at the time of irradiation.

The Stage 9 hypothesis is therefore:

> Part of the radiation-affected tumor burden remains temporarily visible after
> treatment as a damaged/non-proliferating compartment, and its delayed
> clearance can generate continued post-RT regression after the final fraction.

## Literature basis

The implementation is intentionally simpler than the published full
radiobiology models because CFB-GBM does not contain the dense time-resolved
measurements required to identify all of their parameters.

Relevant evidence:

1. Liu J, Hormuth DA II, Yang J, Yankeelov TE. *A Multi-Compartment Model of
   Glioma Response to Fractionated Radiation Therapy Parameterized via
   Time-Resolved Microscopy Data*. Frontiers in Oncology. 2022;12:811415.
   doi:10.3389/fonc.2022.811415.

   The paper separates proliferative and senescent compartments and models
   early and late radiation effects. It explicitly notes that mitotic
   catastrophe may occur days to weeks after radiation and that models without
   accumulation/late effects performed worse than models containing them in
   their experimental system.

2. Hormuth DA II et al. *Image-based personalization of computational models
   for predicting response of high-grade glioma to chemoradiation*. Scientific
   Reports. 2021;11:8520. doi:10.1038/s41598-021-87887-4.

   This study compares a family of image-informed models and selects a
   parsimonious two-species model rather than assuming that the most complex
   biological model is automatically preferable.

3. Rockne RC et al. *Predicting the efficacy of radiotherapy in individual
   glioblastoma patients in vivo: a mathematical modeling approach*. Physics
   in Medicine and Biology. 2010.

   This is part of the patient-specific PI/PIRT lineage that combines
   proliferation/invasion kinetics with LQ radiobiology.

4. Wen PY et al. *RANO 2.0: Update to the Response Assessment in
   Neuro-Oncology Criteria for High- and Low-Grade Gliomas in Adults*. Journal
   of Clinical Oncology. 2023. doi:10.1200/JCO.23.01059.

   RANO 2.0 emphasizes that early post-radiotherapy enhancement is confounded
   by pseudoprogression/treatment effect. Therefore enhancing MRI cannot be
   treated as a direct measurement of viable-cell density.

## State

Stage 9 uses three latent fields:

- v(x,t): viable/proliferative tumor density;
- d(x,t): treatment-damaged, non-proliferating burden;
- m(x,t): persistent proliferation modifier inherited from Stage 8.

The MRI-visible density surrogate is

    y(x,t) = clip(v + w_d d, 0, 1)

where w_d is a global damaged-visibility parameter.

Only v diffuses and proliferates. The logistic carrying capacity is shared
between v and d:

    dv/dt = D Laplacian(v) + rho m v (1 - v - d)

The damaged compartment clears exponentially:

    dd/dt = -lambda_d d

with

    lambda_d = ln(2) / T_half.

## Radiation event

Stage 9 deliberately retains the Stage 8 LQ/PIRT radiation loss so the
zero-damage-transfer candidate is a regression control.

For one fraction, the Stage 8 PIRT loss is

    L = (1 - S) v (1 - v)

where S is the LQ survival fraction.

Stage 9 then applies

    v <- v - L
    d <- d + eta_d L

where eta_d is the global damage-transfer fraction.

Thus:

- eta_d = 0 reproduces Stage 8 immediate removal;
- eta_d > 0 transfers part of the radiation-affected burden into a delayed
  compartment instead of making it disappear immediately.

The existing Stage 8 proliferation modifier m is still updated by the selected
Stage 8 proliferation-survival value.

## Assimilation at t1

The damaged compartment is latent, so t1 MRI cannot identify v and d
separately.

Stage 9 therefore performs a conservative constrained assimilation:

1. preserve the pre-t1 damaged burden when it is compatible with observed MRI;
2. cap damaged burden only if its visible contribution alone would exceed the
   observed density;
3. assign the remaining observed density to the viable compartment;
4. preserve the Stage 8 proliferation modifier.

This prevents both extremes:

- resetting treatment memory at t1;
- retaining a hidden state already inconsistent with t1 MRI.

## Candidate family

Stage 9 uses sequential nested ablation rather than a Cartesian sweep.

Phase 1 — delayed timescale:

- exact Stage 8 control: eta_d = 0;
- T_half = 14 days;
- T_half = 30 days;
- T_half = 60 days;

with eta_d = 1 and w_d = 1 for delayed candidates.

Phase 2 — damage-transfer sensitivity around the selected timescale:

- eta_d = 0.50;
- eta_d = 0.75;
- eta_d = 1.00.

Phase 3 — damaged-visibility sensitivity around the selected structure:

- w_d = 0.50;
- w_d = 0.75;
- w_d = 1.00.

The model family is intentionally small because the current longitudinal
dataset is too sparse to support patient-specific delayed-response parameters.

## Frozen Stage 8 kinetics

Stage 9 reads D and rho from two already sealed artifacts:

- Stage 8 development model selection;
- Stage 8 16-patient internal validation.

It does not refit them during delayed-response model selection.

The eta_d = 0 Stage 9 candidate must reproduce the sealed Stage 8 Dice for
every development patient within numerical tolerance. A mismatch aborts the
selection run.

This is both a regression test and an experimental-control requirement.

## Development cohort

Stage 9 development data are the union of:

- the Stage 8 development-exposed patients used for model selection;
- the 16 patients whose t2 was revealed during Stage 8 internal validation.

The original Stage 8 untouched holdout is not changed.

Eligible non-holdout patients whose t2 is still unopened become the Stage 9
reserve validation pool.

## Selection guardrails

A delayed candidate is not adopted merely because it improves the mean by a
tiny amount.

The default protocol requires:

- mean Dice gain over the exact Stage 8 control >= 0.005;
- no additional catastrophic failures relative to the control;
- catastrophic failure is defined as Dice delta vs persistence < -0.10.

Among eligible candidates, ranking is:

1. mean Dice descending;
2. median Dice descending;
3. catastrophic-failure count ascending;
4. mean HD95 ascending;
5. complexity ascending;
6. candidate ID.

Leave-one-patient-out selection counts are recorded for every phase.

## Mechanistic diagnostic

The Stage 9 artifact records, per patient:

- t1 and t2 days;
- forecast horizon;
- days from last RT fraction to t1;
- observed t1 and t2 volumes;
- predicted t2 volume;
- observed t1-to-t2 volume change;
- Dice, volume error, HD95, and centroid distance.

The final report is stratified into growth, stable, and regression trajectories
using a +/-10% observed-volume threshold.

The delayed-response hypothesis is considered scientifically interesting only
if it improves the regression subgroup without creating new large failures in
the other groups.

## What Stage 9 does not claim

The damaged compartment is not asserted to be a direct measurement of
senescence, necrosis, pseudoprogression, or viable tumor. It is a parsimonious
latent treatment-response state motivated by those mechanisms.

No TMZ schedule is invented.

No new patient-specific free treatment-response parameter is fitted.

No reserve or untouched-holdout t2 is used during Stage 9 model selection.

## Execution

After tests and Ruff pass:

    python scripts/twin/select_stage9_delayed_response.py \
      --repo-root . \
      --data-audit-root results/cohort/stage8-data-audit-v1 \
      --stage8-selection-root results/cohort/stage8-model-selection-v1 \
      --stage8-validation-root results/cohort/stage8-internal-validation-v1 \
      --output-dir results/cohort/stage9-delayed-selection-v1

The output is sealed as:

- stage9_delayed_selection.json;
- stage9_delayed_selection.sha256;
- stage9_delayed_selection.csv.

A new reserve validation subset must be planned only after this selection is
sealed.
