# GBM Digital Twin — V3 delayed post-RT development protocol

Status: **development protocol after V2 reveal**

Dataset role: **CFB-GBM development feedback only**

External validation: **not performed in this stage**

## Motivation

The frozen V2/Accuracy-V1 error analysis showed that the largest systematic
forecast failure was associated with observed t1-to-t2 regression. A separate
pre-t2 treatment-timing audit established that, for every patient with a
reconstructable radiotherapy schedule in the current development mini-cohort,
all reconstructed RT fractions had already occurred before t1. Therefore the
fractionated RT component has no fraction events during the t1-to-t2 forecast
interval.

V3 evaluates one additional effective treatment-response component: a delayed
post-radiotherapy effect that decays after the final reconstructed fraction.
This is a research model of effective post-treatment dynamics. Its parameters
must not be interpreted as directly measured patient radiosensitivity.

## Model change

The V2 reaction-diffusion state is retained:

$$
\frac{\partial c}{\partial t}
=
\nabla\cdot(D\nabla c)+\rho c(1-c).
$$

For V3, the post-RT component contributes an additional loss term after the
last reconstructed fraction:

$$
\frac{\partial c}{\partial t}
=
\nabla\cdot(D\nabla c)+\rho c(1-c)-k(t)c,
$$

with

$$
k(t)=k_0\exp\left(-\frac{t-t_{RT}}{\tau}\right),
\qquad t\ge t_{RT}.
$$

The fractionated PIRT model remains present. V3 therefore uses a composite
`RadiotherapyProtocol` containing the reconstructed PIRT fractions and the
delayed post-RT effect.

No other scientific component is intentionally changed relative to Accuracy
V1: target spacing, observation threshold, latent width, calibration objective,
D/rho search strategy, assimilation rule and mandatory baselines remain the
same.

## Pre-t2 parameter selection

Global post-RT parameters were selected before the V3 t2 freeze/reveal cycle.
The selection workflow used only:

```text
t0 imaging / GTV
t1 imaging / GTV
reconstructable treatment metadata
```

It did not load t2 imaging. Candidate ranking was predeclared as:

```text
mean t0->t1 calibration loss
then median calibration loss
then calibration boundary count
then non-identifiable count
```

The selected candidate is read from the sealed
`results/cohort/v3-post-rt-selection/post_rt_selection.json` artifact. The V3
freeze must validate that artifact and its SHA-256 seal; the values must not be
copied manually into the freeze command.

Current selected development candidate:

```text
candidate_id: post-rt-k0.005-tau60
k0: 0.005 / day
tau: 60 days
```

The selected candidate had the lowest predeclared mean composite calibration
loss in the tested grid. Its advantage over the fractionated-only candidate is
modest and the candidate ranking is sensitive to individual development
patients. This uncertainty is part of the V3 result and must not be hidden by
post-hoc switching to another candidate after t2 evaluation.

## Anti-leakage and artifact chain

The V3 workflow is:

```text
sealed pre-t2 post-RT selection
        |
        v
V3 freeze for every eligible patient
        |
        v
sealed V3 cohort manifest
        |
        | only after all predictions are frozen
        v
reveal t2
        |
        v
V3 cohort evaluation
        |
        v
V3 error analysis
        |
        v
paired comparison with Accuracy V1
```

The V3 cohort freeze must use a clean Git working tree. The freeze records both
the current repository commit and the SHA-256 of the earlier sealed parameter
selection. Patient artifacts additionally record the selected candidate and
its selection provenance.

## Interpretation

V3 is a development experiment, not an independent validation result. CFB-GBM
t2 outcomes have already been inspected during prior error analysis, so V3
performance on this cohort may be used for model development but not presented
as unbiased final validation.

The key comparison is paired Accuracy-V1 versus V3 on the same eligible
patients. Report Dice, relative volume error, HD95, centroid distance, baseline
deltas, calibration diagnostics and trajectory-stratified behavior. A useful
V3 result should improve the regression failure mode without materially
sacrificing stable/growth cases or creating pathological volume collapse.

Burdenko remains reserved for the later external-validation stage.
