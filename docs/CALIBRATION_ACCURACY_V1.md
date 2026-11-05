# Calibration Accuracy V1

## Purpose

This experiment tests one narrow hypothesis derived from the sealed V2 development-cohort error analysis:

> The current one-round adaptive D/rho search stops too early when the optimum reaches the artificial upper edge of the evaluated parameter grid.

The experiment changes only the calibration search strategy. It does **not** change the reaction-diffusion equation, MRI preprocessing, observation threshold, objective weights, radiotherapy model, held-out protocol, or baseline definitions.

## Baseline evidence

The sealed `v2-analysis` development artifact contained 8 evaluated patients. Seven calibrations were reported as non-identifiable and seven had a parameter at the evaluated boundary. Several selected diffusion values were `D = 0.0375`, which is the first upper extension produced from the original coarse maximum `D = 0.030` by the previous one-round refinement.

This pattern is consistent with an optimizer/search-space limitation, but it does not prove that a wider search will improve held-out t2 prediction. Accuracy V1 is designed to test that hypothesis directly.

## Controlled change

Baseline V2:

- one refinement round;
- upper-bound extension equal to half of the previous grid gap.

Accuracy V1:

- three refinement rounds;
- when the current best value remains at the artificial upper boundary, extend by one full previous grid gap;
- continue local midpoint refinement for interior optima;
- preserve the physical lower bound at zero.

The coarse grid remains unchanged:

- `D = [0.0, 0.005, 0.015, 0.030]`;
- `rho = [0.0, 0.015, 0.035, 0.055]`.

The experiment config is:

`configs/experiments/mini_cohort_accuracy_v1.yaml`

## Isolation rules

For this experiment, do not change:

- `threshold = 0.5`;
- `dt = 2 days`;
- `volume_weight = 0.5`;
- latent-state width;
- soft calibration temperature;
- radiotherapy alpha or alpha/beta;
- PDE structure;
- selected cohort;
- target spacing;
- t0/t1/t2 anti-leakage protocol.

Changing several of these at once would make the result scientifically ambiguous.

## Artifact isolation

Do not overwrite the baseline artifacts:

- `results/cohort/v2-freeze`;
- `results/cohort/v2-evaluation`;
- `results/cohort/v2-analysis`.

Accuracy V1 uses separate directories:

- `results/cache/v2-accuracy-v1`;
- `results/cohort/v2-accuracy-v1-freeze`;
- `results/cohort/v2-accuracy-v1-evaluation`;
- `results/cohort/v2-accuracy-v1-analysis`.

This allows patient-by-patient comparison against the exact baseline.

## Decision criteria

The search change is useful only if it improves held-out t2 behavior, not merely t0→t1 calibration loss.

Primary development criteria:

1. mean and median Twin Dice versus the baseline V2 run;
2. patient-level Dice change;
3. mean delta versus persistence and volume baseline;
4. number of patients worse than persistence;
5. HD95 and centroid-distance changes;
6. reduction in artificial upper-bound calibration cases;
7. whether gains are concentrated in only one or two outliers.

A better calibration Dice with worse t2 Dice is not considered an accuracy improvement.

## Interpretation of zero-bound solutions

`D = 0` and `rho = 0` are physical lower bounds of the current model. A solution at zero is different from a solution trapped at an arbitrary upper search boundary. Accuracy V1 mainly targets the latter.

Persistent zero-bound/non-identifiable solutions may indicate that the available t0→t1 observations do not uniquely identify both parameters under the current model and objective. They should not be fixed by simply allowing negative D or rho.

## Treatment model

The current V2 workflow already applies the reconstructed PIRT radiotherapy model during both calibration and prediction when treatment metadata is available. Therefore the poor performance on regression trajectories is **not** evidence that treatment is completely absent.

If Accuracy V1 does not materially improve held-out prediction, the next controlled experiments should inspect treatment parameterization/timing and calibration identifiability rather than adding a duplicate treatment term.

## Development-validation boundary

The CFB-GBM mini-cohort has now been inspected through held-out t2 error analysis. Any changes motivated by these results are development/model-selection changes.

Do not treat repeated performance on this same mini-cohort as independent validation. External validation remains a separate later stage, planned around the Burdenko cohort.
