# Stage 10 result — decoupled damage advanced

Current status, 2026-10-05: the development gate below passed, but the frozen
model subsequently **failed reserve internal validation**. See the
[sealed reserve result](STAGE10_VALIDATION_RESULT.md) and
[failure analysis](STAGE10_RESERVE_FAILURE_ANALYSIS.md). It must not advance
to untouched holdout. The development selection below remains unchanged.

## Sealed development result

Stage 10 was executed on the same 24 already exposed development patients.

Sealed selection artifact SHA-256:

`2bff489685dd2d8ed9d28f8ce2abe55214475ade8ce287f73d0bc8e19f6b4326`

Decision:

`decoupled_candidate_advanced`

Selected model:

`stage10-decoupled-half-life-60d`

The selected structure keeps MRI-visible damaged burden separate from persistent
MRI-invisible inert occupancy. The visible-damage half-life is fixed at
`60 d` for the next validation stage.

No reserve t2 or untouched-holdout t2 was loaded during selection.

## Aggregate result

| Model | Mean Dice | Median Dice | Δ vs persistence | Catastrophic | RVE | HD95 mm |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Stage 9 control | 0.681404 | 0.731461 | -0.011792 | 2 | 0.950507 | 11.252165 |
| Stage 10 14 d | 0.694163 | 0.760661 | +0.000966 | 0 | 0.727966 | 11.126114 |
| Stage 10 30 d | 0.695902 | 0.756572 | +0.002706 | 0 | 0.700260 | 11.082456 |
| Stage 10 60 d | 0.696845 | 0.755809 | +0.003649 | 0 | 0.663907 | 11.084416 |

The selected 60-day model therefore:

- improves mean Dice over Stage 9 by approximately `+0.01544`;
- moves the development mean from below persistence to slightly above it;
- reduces catastrophic failures from `2` to `0`;
- reduces mean relative volume error from `0.9505` to `0.6639`;
- slightly improves mean HD95.

The gain is still modest at cohort level. It must not be interpreted as
validated predictive superiority until evaluated on previously unopened
patients.

## Trajectory groups

Stage 9 control:

- regression mean delta vs persistence: `-0.029112`;
- growth mean delta vs persistence: `+0.006254`.

Selected Stage 10:

- regression mean delta vs persistence: `+0.006040`;
- growth mean delta vs persistence: `+0.004390`.

The primary mechanistic target was achieved: the regression subgroup no longer
has a negative mean delta relative to persistence, while the growth subgroup
remains positive and within the pre-specified degradation tolerance.

## Former catastrophic cases

The two Stage 9 catastrophic cases improve substantially.

### Patient 108

- Stage 9 control Dice: `0.461433`;
- Stage 10 60 d Dice: `0.579516`;
- gain vs Stage 9: approximately `+0.11808`;
- delta vs persistence improves from `-0.179625` to about `-0.06154`.

### Patient 205

- Stage 9 control Dice: `0.660450`;
- Stage 10 60 d Dice: `0.794170`;
- gain vs Stage 9: approximately `+0.13372`;
- delta vs persistence improves from `-0.192041` to about `-0.05832`.

Neither remains catastrophic under the pre-specified
`delta_vs_persistence < -0.10` rule.

Patient 251 remains a severe absolute failure with Dice around `0.0705`, but
it is not a catastrophic failure relative to persistence under the project
definition. It remains an important failure-analysis case.

## Scientific interpretation

Stage 10 supports the hypothesis that two effects should not share one
clearance parameter:

1. loss of MRI-visible post-treatment burden;
2. persistent occupancy / suppression of viable regrowth.

The improvement does **not** establish that a 60-day half-life is a biological
constant. It identifies the pre-specified model-family candidate that best
satisfied the development guardrails.

No further Stage 10 half-life sweep is permitted before validation.

## Frozen model

The repository freezes this development result in:

- `configs/research/stage10_frozen_model.yaml`;
- `configs/research/stage10_reserve_validation.yaml`.

The frozen model binds reserve validation to the exact sealed Stage 10
selection SHA-256.

## Next step

The next scientific step is a sealed reserve internal validation.

The first reserve checkpoint uses a deterministic stratified subset of
`16` of the `48` still-unopened reserve patients. The cohort is selected
from metadata only and sealed before any reserve t2 image content is opened.

Pre-specified validation guardrails require:

- mean delta vs persistence > `0`;
- median delta vs persistence >= `0`;
- zero catastrophic failures;
- mean RVE no worse than persistence;
- mean HD95 no worse than persistence.

The bootstrap 95% confidence interval for paired mean Dice delta is reported
but is not used for post-hoc model selection.

If the checkpoint passes, the model may proceed toward untouched-holdout
evaluation without model changes. If it fails, revealed reserve outcomes may
be used for failure analysis but not for tuning the frozen Stage 10 model.
