# Stage 10 reserve internal-validation protocol

## Status

**Pre-registered after the sealed Stage 10 development selection and before
opening reserve t2.**

Frozen model:

`stage10-decoupled-half-life-60d`

Frozen Stage 10 selection SHA-256:

`2bff489685dd2d8ed9d28f8ce2abe55214475ade8ce287f73d0bc8e19f6b4326`

## Cohort

The Stage 10 selection artifact reports:

- development patients already exposed: `24`;
- reserve patients still unopened: `48`;
- untouched holdout remains sealed.

The first internal-validation checkpoint uses `16` reserve patients selected
by deterministic stratified hashing with seed `20261001`.

Selection uses the Stage 8 audit metadata and `split_stratum` only. It does
not load t2 image content.

The remaining `32` reserve patients remain sealed.

## Frozen quantities

Before reserve reveal the following are fixed:

- Stage 10 model structure;
- visible-damage half-life = `60 d`;
- full inert retention;
- Stage 8 radiobiology;
- Stage 8 proliferation survival;
- MRI observation parameters;
- calibration objective/grid/refinement;
- evaluation spacing and timestep;
- baseline definitions;
- validation cohort-selection algorithm;
- validation pass/fail guardrails.

For each reserve patient only D and rho remain patient-specific. They are
calibrated from t0→t1 and frozen before t2 is loaded.

No Stage 10 global parameter is fit on reserve outcomes.

## Validation metrics

Primary paired comparison is Stage 10 versus persistence.

Report:

- mean and median Dice;
- mean and median Dice delta vs persistence;
- better/equal/worse counts;
- catastrophic failures using
  `delta_vs_persistence < -0.10`;
- mean relative volume error;
- mean HD95;
- centroid distance;
- trajectory-group summaries;
- deterministic bootstrap 95% CI for mean paired Dice delta.

The bootstrap interval is descriptive uncertainty, not an additional tuning
criterion.

## Pass criteria

The checkpoint passes only if all are true:

1. mean Dice delta vs persistence is strictly positive;
2. median Dice delta vs persistence is non-negative;
3. catastrophic failure count is zero;
4. mean relative volume error is no worse than persistence;
5. mean HD95 is no worse than persistence.

These criteria are intentionally stricter than the development-selection rule.

## Failure handling

If validation fails:

- do not change the Stage 10 half-life using reserve outcomes;
- do not search additional Stage 10 candidates;
- do not open untouched holdout;
- retain the revealed patients as exposed failure-analysis cases;
- any revised model must return to an explicitly defined development cycle
  before evaluation on still-unopened patients.

## Execution

After pulling the repository, run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\twin\run_stage10_reserve_validation.ps1
```

The checkpoint:

1. runs targeted tests and full Python quality gates;
2. verifies the exact frozen Stage 10 selection SHA;
3. creates and seals the 16-patient validation plan if it does not exist;
4. [materializes only the verified sealed reserve cohort](STAGE10_RESERVE_MATERIALIZATION.md)
   from the official NIfTI source and verifies local inputs before any t2 image
   content is loaded;
5. calibrates each patient D/rho from t0→t1;
6. freezes D/rho and then reveals t2;
7. evaluates the frozen Stage 10 forecast against persistence;
8. writes sealed JSON/CSV/SHA-256;
9. creates `STAGE10_VALIDATION_RESULT.md`.

Expected outputs:

```text
results/cohort/stage10-reserve-validation-plan-v1/
    stage10_validation_plan.json
    stage10_validation_plan.sha256
    stage10_validation_patient_ids.txt
    stage10_validation_required_paths.txt

results/cohort/stage10-internal-validation-v1/
    stage10_internal_validation.json
    stage10_internal_validation.csv
    stage10_internal_validation.sha256
    STAGE10_VALIDATION_RESULT.md
```
