# Stage 10 — sealed reserve internal validation

Decision: `validation_failed`

Frozen model: `stage10-decoupled-half-life-60d`

The frozen Stage 10 model did not pass every pre-specified reserve-validation guardrail. Do not tune on the revealed reserve outcomes.

## Primary metrics

- patients: 16
- mean Twin Dice: 0.7084
- mean persistence Dice: 0.7426
- mean delta vs persistence: -0.0341
- median delta vs persistence: +0.0000
- bootstrap 95% CI for mean delta: [-0.0878, +0.0053]
- catastrophic failures: 2
- mean Twin RVE / persistence RVE: 0.3527 / 0.3875
- mean Twin HD95 / persistence HD95: 7.8380 / 8.4652 mm

## Guardrails

Failed guardrails:

- `mean_delta_vs_persistence`
- `catastrophic_failure_count`

## Leakage status

- validation patients revealed: 16
- remaining reserve patients sealed: 32
- untouched holdout t2 loaded: false

## Next step

return_to_development_failure_analysis_without_reserve_tuning

## Execution provenance — 2026-10-05

- Exact cohort: `15,47,57,71,73,91,139,140,142,144,161,194,201,234,241,254`.
- JSON SHA-256: `f565a0713de52666b3c5a7624486b8bfa32280cb45b69fd3816c809d89aa885a`.
- Plan SHA-256: `ef969c47adb953efbc862f18d1006b4e7007bdd927b1d975db005b4e8d56a37f`.
- Execution code: clean commit `f02a553ad548d70997d5f32df4a0880d7adb9e30`.
- Runtime: original project environment, Python 3.11.9, NumPy 2.4.6, SciPy 1.17.1.
- Calibration workers: 4; frozen scientific settings unchanged.
- Official input release: TCIA CFB-GBM version 4, package 1345.
- Acquisition receipt SHA-256: `900768007d358a25659db1503a62f92ccca6954a5d67503b330aa3c4eaddaf20`.
- Inputs: 144 files, 2,356,539,655 bytes; prepared via hardlinks.
- Better/equal/worse than persistence: `3/6/7`.
- Catastrophic patients: `73` (delta `-0.3621`), `254` (delta `-0.1251`).

The median delta, mean RVE and mean HD95 conditions passed. The positive mean
delta and zero-catastrophic-failure conditions failed. The bootstrap interval
includes zero and remains descriptive; it does not override the frozen verdict.

The sealed JSON/CSV/SHA and generated report remain in
`D:/Projects/gbm-digital-twin/results/cohort/stage10-internal-validation-v1/`.
The execution log is
`D:/Projects/gbm-digital-twin/results/stage10-reserve-validation-execution.log`.
JSON seal, source/config provenance, all CSV values and all 16 freeze-before-reveal
log entries were checked. No patient was replaced, and no global model setting
was fit to reserve outcomes.

See [individual failure analysis](STAGE10_RESERVE_FAILURE_ANALYSIS.md) and
[execution checkpoints](STAGE10_EXECUTION_PROGRESS.md). Medical images and local
result/cache files remain outside Git.
