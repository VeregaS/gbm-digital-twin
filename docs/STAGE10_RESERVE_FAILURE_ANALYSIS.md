# Stage 10 reserve failure analysis — 2026-10-05

The frozen 60-day model failed the preregistered reserve checkpoint. This
document describes the completed sealed experiment; it defines no new
candidate, threshold, tuning rule or replacement cohort.

Full aggregate report: [STAGE10_VALIDATION_RESULT.md](STAGE10_VALIDATION_RESULT.md).

## Scope and provenance

- Patients: `15,47,57,71,73,91,139,140,142,144,161,194,201,234,241,254`.
- Result JSON SHA-256: `f565a0713de52666b3c5a7624486b8bfa32280cb45b69fd3816c809d89aa885a`.
- Execution code: clean commit `f02a553ad548d70997d5f32df4a0880d7adb9e30`.
- 32 remaining reserve patients and the untouched holdout remain closed.
- All 16 log entries record t0/t1 calibration and D/rho freeze before t2 reveal.
- JSON seal, all CSV rows, cohort identity, paired deltas and summary means verified.

## Individual paired outcomes

| Patient | Trajectory | Calibration Dice | Twin Dice | Persistence Dice | Delta | Twin RVE | Persistence RVE |
|---|---|---:|---:|---:|---:|---:|---:|
| 15 | regression | 0.7119 | 0.6923 | 0.6923 | +0.0000 | 0.6081 | 0.6081 |
| 47 | growth | 0.6809 | 0.7476 | 0.6370 | +0.1106 | 0.2747 | 0.5258 |
| 57 | regression | 0.7417 | 0.8105 | 0.8339 | -0.0234 | 0.2538 | 0.1132 |
| 71 | regression | 0.4274 | 0.7215 | 0.7215 | +0.0000 | 0.6314 | 0.6314 |
| 73 | regression | 0.2919 | 0.2045 | 0.5666 | -0.3621 | 0.7857 | 0.9868 |
| 91 | growth | 0.7565 | 0.7710 | 0.7956 | -0.0245 | 0.0690 | 0.1591 |
| 139 | regression | 0.0928 | 0.2528 | 0.2755 | -0.0227 | 1.5600 | 2.1200 |
| 140 | growth | 0.5961 | 0.7085 | 0.7085 | +0.0000 | 0.2461 | 0.2461 |
| 142 | stable | 0.6924 | 0.7806 | 0.7803 | +0.0003 | 0.0796 | 0.0857 |
| 144 | growth | 0.6678 | 0.8004 | 0.8619 | -0.0615 | 0.3322 | 0.2338 |
| 161 | growth | 0.6653 | 0.7414 | 0.7810 | -0.0396 | 0.1269 | 0.0921 |
| 194 | growth | 0.6840 | 0.6349 | 0.6349 | +0.0000 | 0.1719 | 0.1719 |
| 201 | stable | 0.4700 | 0.9178 | 0.9162 | +0.0016 | 0.0240 | 0.0319 |
| 234 | stable | 0.8010 | 0.8762 | 0.8762 | +0.0000 | 0.0534 | 0.0534 |
| 241 | stable | 0.7598 | 0.8907 | 0.8907 | +0.0000 | 0.0767 | 0.0767 |
| 254 | stable | 0.7425 | 0.7840 | 0.9091 | -0.1251 | 0.3490 | 0.0634 |

## Catastrophic cases

The frozen threshold is paired Dice delta `< -0.10`. No case is removed from
the primary analysis.

| Patient | Horizon (days) | Observed t1 (cm³) | Observed t2 (cm³) | Predicted t2 (cm³) | Calibration identifiable |
|---|---:|---:|---:|---:|---|
| 73 | 112.0 | 14.464 | 7.280 | 1.560 | False |
| 254 | 91.0 | 29.800 | 31.816 | 20.712 | False |

Patient 73's forecast underestimated observed t2 volume (1.560 versus 7.280
cm³) and had a substantially worse spatial overlap than persistence. The t0→t1
calibration Dice was already low (`0.2919`). Its RVE and HD95 nevertheless
improved relative to persistence, illustrating why all frozen criteria must
pass together.

Patient 254 had nearly stable observed volume, but the forecast reduced volume
to 20.712 cm³ and worsened Dice, RVE and HD95. Both catastrophic cases had
non-identifiable calibration and fitted rho `0`. Non-identifiability was also
present in other cases; these associations do not establish the cause of the
failure or justify a post-hoc gate.

## Trajectory diagnostics

These subgroups use revealed outcomes and are descriptive. They cannot be
used to select a model or construct a pre-t2 gate.

| Trajectory | Patients | Mean Dice | Mean paired delta |
|---|---:|---:|---:|
| growth | 6 | 0.7340 | -0.0025 |
| regression | 5 | 0.5363 | -0.0816 |
| stable | 5 | 0.8499 | -0.0246 |

## Interpretation and permitted next step

The development improvement did not satisfy the stricter independent reserve
criteria. Dice, volume and distance errors are observed model failures; these
summaries alone cannot identify a biological mechanism or separate
calibration, registration, observation and treatment-model causes.

The 16 cases are now exposed failure-analysis cases. Keep the frozen Stage 10
model and this result intact. Do not sweep half-lives, fit global parameters,
select alternatives or define a persistence gate using their t2 outcomes.
Do not advance this model to untouched holdout.

A revised model must return to an explicitly specified development cycle on
the existing development cohort, freeze its structure and global parameters,
and receive a separate prospective evaluation plan before opening any of the
32 remaining reserve cases. The conditional
[observation-model protocol](OBSERVATION_MODEL_NEXT_CYCLE.md) is a design
reference; this failure analysis does not bypass its activation conditions.
