# Cohort error analysis protocol

## Purpose

This stage analyzes errors of an already sealed V2 cohort evaluation. It does **not** modify, recalibrate, or rerun patient predictions.

The input chain is:

```text
sealed cohort freeze
        -> held-out t2 reveal/evaluation
        -> sealed cohort evaluation
        -> cohort error analysis
```

The analysis is therefore post-evaluation and may use observed `t2` quantities, including tumour volume and geometry QC.

## Reproducible artifact

Run from the repository root:

```powershell
python scripts\twin\analyze_cohort.py --repo-root .
```

Default output:

```text
results/cohort/v2-analysis/
    cohort_analysis.json
    cohort_analysis.sha256
    cohort_analysis.csv
```

`results/` is ignored by Git. The analysis artifact stores SHA-256 references to:

- the sealed cohort evaluation;
- the source cohort freeze referenced by that evaluation;
- the analysis YAML configuration;
- the repository commit recorded by the evaluation.

The API refuses to serve an analysis whose `source_evaluation_sha256` no longer matches the current sealed cohort evaluation.

## Patient-level variables

For each evaluated patient the artifact contains:

- calibration interval `t0 -> t1`;
- forecast horizon `t1 -> t2`;
- observed GTV volumes at `t0`, `t1`, and `t2` on the evaluation grid;
- relative volume changes and qualitative trajectory (`growth`, `stable`, `regression`);
- fitted reaction-diffusion parameters `D` and `rho`;
- calibration Dice, volume error, and loss;
- identifiability and search-boundary diagnostics;
- Twin, persistence, and volume-baseline metrics;
- Dice deltas versus both baselines;
- post-reveal geometry/QC flags;
- radiotherapy timing context already present in the patient metadata.

## Cohort-level summaries

The current report includes:

- mean and median Twin Dice;
- mean and median Dice delta versus persistence;
- mean and median Dice delta versus the volume baseline;
- better/equal/worse counts against both baselines;
- QC-flagged patient count;
- non-identifiable calibration count;
- calibration search-boundary count;
- ranked worst cases;
- descriptive Pearson and Spearman correlations for:
  - forecast horizon vs Twin Dice;
  - `t1 -> t2` tumour-volume change vs Twin Dice;
  - calibration Dice vs forecast Twin Dice;
- summaries stratified by observed `t1 -> t2` volume trajectory.

Correlation values are descriptive diagnostics. They are not interpreted as causal effects.

## Analysis configuration

Parameters live in:

```text
configs/analysis/cohort_error_analysis.yaml
```

They currently control:

- the relative-volume threshold used to call a trajectory stable;
- the number of worst patients retained in ranked summaries;
- the minimum number of finite observations required before a correlation is reported.

These parameters are analysis settings, not prediction-model parameters.

## Anti-leakage interpretation

The original V2 forecast for every patient remains valid as a held-out `t1 -> t2` prediction because it was frozen before `t2` reveal.

However, once `t2` results from this cohort have been inspected and used to choose new model assumptions, parameter ranges, objectives, thresholds, or architectures, this cohort becomes a **development set for subsequent model iterations**.

Therefore:

1. The existing sealed V2 evaluation remains a valid record of the pre-reveal baseline.
2. Error analysis may guide the next model version.
3. A new model version must create a new freeze/evaluation artifact rather than overwrite V2.
4. Performance after tuning on these cases must not be described as independent validation on the same cases.
5. Final generalization claims require data not used for model selection; the planned Burdenko cohort is reserved for external validation.

## Decision rule for the next modeling stage

Do not add biological complexity solely because aggregate Dice is imperfect.

Use the error analysis to distinguish at least four failure classes first:

1. **Data/geometry failure** — QC flags, masks outside brain, fragmented targets, or registration/resampling concerns.
2. **Calibration failure** — poor `t0 -> t1` fit, non-identifiability, or optimum on a search boundary.
3. **Forecast-horizon / trajectory failure** — degradation associated with longer horizons or rapid regression/growth.
4. **Model-form failure** — clean data and stable calibration, but systematic spatial errors remain relative to simple baselines.

Only the fourth class directly motivates a more expressive biological model. The second class should first be addressed by calibration/objective/search improvements, and the first class by data/QC corrections.
