# V3 delayed post-radiotherapy parameter selection

Status: **development experiment**

This document defines the parameter-selection stage for the first V3
treatment-response experiment.

V2 and Accuracy V1 remain immutable historical development artifacts.

## Motivation

The treatment-timing audit showed that every reconstructable radiotherapy
schedule in the current development cohort was completed before `t1`.
Consequently, the fractionated-only V2 treatment model has no fractions left
to apply during the held-out `t1 -> t2` forecast interval.

The current solver already supports a continuous exponentially decaying
post-radiotherapy effect:

$$
k(t) = k_0 \exp\left(-\frac{t-t_{RT}}{\tau}\right),
$$

where:

- `k0` is an effective initial post-RT kill rate in `1/day`;
- `tau` is the decay time in days;
- `t_RT` is the reconstructed day of the last RT fraction.

The corresponding reaction-diffusion update contains the additional term

$$
-k(t)c.
$$

This is an effective research model. `k0` and `tau` must not be interpreted
as directly measured patient radiosensitivity parameters.

## Leakage rule

The selector is intentionally restricted to the calibration interval.

It may load:

```text
t0 imaging / GTV / brain mask
t1 imaging / GTV / brain mask
treatment metadata
```

It must not load:

```text
t2 MRI
t2 GTV
t2 tumour volume
t2 evaluation metrics
V2/Accuracy-V1 t2 evaluation artifacts
```

The implementation has a regression test that fails if the selector requests
a prepared `t2` timepoint.

The development cohort has already been revealed during earlier experiments,
so this procedure does not restore independent validation status. Its purpose
is to keep V3 model construction algorithmically separated from held-out
forecast targets. External validation is still required later.

## Candidate model

Every candidate uses the same components as Accuracy V1:

```text
reaction-diffusion PDE
PIRT fraction operator
reconstructed weekday-like RT schedule
Accuracy-V1 D/rho search
observed-t1 assimilation
```

The only candidate-level change is an optional post-RT effect beginning at
the last reconstructed RT fraction.

The baseline candidate is:

```text
fractionated-only
```

The exploratory grid is stored in:

```text
configs/research/post_rt_selection_v1.yaml
```

The initial grid is deliberately small. It is a development sensitivity grid,
not a claim that the values are established biological constants.

## Selection criterion

For every global post-RT candidate and every patient with a reconstructable
RT schedule:

1. build the treatment model;
2. calibrate patient-specific `D` and `rho` on `t0 -> t1` only;
3. record calibration Dice, volume error, loss and diagnostics.

Candidates are ranked deterministically by:

```text
mean calibration loss
median calibration loss
boundary calibration count
non-identifiable calibration count
candidate id
```

The selected post-RT candidate is therefore a cohort-level treatment
hyperparameter, while `D` and `rho` remain patient-specific.

## Output

Run:

```powershell
python scripts\twin\select_post_rt.py `
  --repo-root . `
  --workers 4
```

The default output is:

```text
results/cohort/v3-post-rt-selection/
  post_rt_selection.json
  post_rt_selection.sha256
  post_rt_candidates.csv
  post_rt_patients.csv
```

The JSON artifact records an explicit leakage-control block and the exact Git
commit/config checksums used for selection.

## Decision rule

A post-RT candidate is not adopted merely because the mechanism is plausible.
The fractionated-only baseline participates in the same ranking.

If the baseline wins, the current `t0 -> t1` data do not support introducing
the delayed effect under this candidate grid.

If a post-RT candidate wins, its parameters are frozen into a separate V3
experiment configuration before any new V3 `t1 -> t2` prediction artifacts
are created.

The subsequent V3 evaluation must still report persistence and volume
baselines and must be interpreted as development feedback, not independent
validation.
