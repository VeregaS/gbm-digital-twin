# Stage 10 — decoupled visible clearance and inert occupancy

## Current execution status

**Paused after the published-reference checkpoint.**

The protocol below remains the predefined fallback mechanistic experiment, but
it must not be implemented or run before Reference Fidelity v2 is completed.
Reference benchmark v1 showed that the pinned TumorTwin solver and upstream LM
calibration also underperform Stage 9/persistence when forced onto the current
GTV-derived observation problem. Before adding another latent treatment state,
the project is therefore testing tumor-centric ROI calibration and pre-t2
ADC-derived cellularity on the same already exposed development cohort.

No reserve or untouched-holdout patient should be opened for this pause-stage
diagnostic.

## Status

**Paused before implementation pending the published-reference benchmark.**

Stage 10 remains a pre-specified mechanistic fallback, not the immediate next
experiment. The project first compares the current pipeline with the pinned
TumorTwin reference implementation and audits the locally available mpMRI
modalities. Stage 10 proceeds only if that benchmark does not identify solver,
calibration, or observation-model limitations that should be addressed first.

Stage 9 v2 hit its predefined 120-day diagnostic ceiling. The selected
half-life remained the largest tested value and was chosen in all 24
leave-one-patient-out folds.

Stage 10 is therefore a new **development-only mechanistic diagnostic**. It
must use the same already exposed 24-patient cohort. Reserve patients and the
untouched holdout remain sealed.

## Reference-benchmark gate

See `docs/REFERENCE_BENCHMARK_PROTOCOL.md`.

No new Stage 10 code or reserve-cohort reveal should occur until the benchmark
has produced a sealed result.

## Failure in the Stage 9 state semantics

Stage 9 uses:

- `v(x,t)`: viable/proliferative density;
- `d(x,t)`: damaged, MRI-visible, non-proliferating density;
- `m(x,t)`: persistent proliferation modifier.

Its growth term is:

    dv/dt = D Laplacian(v) + rho m v (1 - v - d)

and damaged burden clears as:

    dd/dt = -lambda_d d

with MRI-visible surrogate:

    y = clip(v + w_d d, 0, 1)

This couples two distinct effects to one half-life:

1. loss of MRI-visible damaged burden;
2. release of logistic carrying capacity.

The monotonic 60 -> 90 -> 120 day improvement implies that the model benefits
from keeping post-treatment occupancy for a long time. It does **not** justify
continuing to increase one nominal clearance half-life.

## Stage 10 hypothesis

A fraction of radiation-damaged burden can become radiographically less
visible while continuing to exert an inert/non-proliferating occupancy effect
on the modeled tissue state.

This is a latent modeling state, not a claim that a specific histologic tissue
class has been measured.

## Minimal state extension

Add one latent field:

- `q(x,t)`: MRI-invisible inert post-treatment occupancy.

Stage 10 state:

- `v`: viable/proliferating;
- `d`: MRI-visible damaged;
- `q`: inert occupancy;
- `m`: persistent proliferation modifier.

Visible density:

    y = clip(v + w_d d, 0, 1)

Logistic occupancy:

    o = clip(v + d + q, 0, 1)

Viable dynamics:

    dv/dt = D Laplacian(v) + rho m v (1 - o)

Visible damaged-state clearance:

    dd/dt = -lambda_d d

Diagnostic inert transfer:

    dq/dt = +lambda_d d

for the full-retention candidate.

Thus the Stage 10 diagnostic preserves total damaged occupancy while allowing
the MRI-visible part of that burden to decline.

No new patient-specific parameter is introduced.

## Radiation and assimilation

Radiation-event equations remain identical to Stage 9 for comparability:

    L = (1 - S) v (1 - v)
    v <- v - L
    d <- d + eta_d L

with the selected Stage 9 global values:

- `eta_d = 1`;
- `w_d = 1`.

At t1 assimilation:

1. preserve `q` where compatible with total occupancy;
2. preserve `d` while its visible contribution is compatible with observed
   density;
3. assign remaining observed visible density to `v`;
4. if `v + d + q > 1`, reduce latent occupancy conservatively only as much as
   required to satisfy the observation and carrying-capacity constraint;
5. preserve the Stage 8 proliferation modifier `m`.

The assimilation implementation must have explicit unit tests for all five
properties.

## Candidate family

Keep the experiment deliberately small.

### Control

Exact selected Stage 9 v2 candidate:

- transfer = `1`;
- damaged visibility = `1`;
- damaged half-life = `120 d`;
- no inert `q` compartment.

### Decoupled candidates

Full transfer of cleared `d` into persistent `q`, with visible-damage
half-life:

- `14 d`;
- `30 d`;
- `60 d`.

No 90/120-day decoupled candidate is needed in the first diagnostic. The point
is to test whether realistic/shorter visible clearance can coexist with
long-lived occupancy.

## Frozen quantities

For every patient:

- D remains frozen from the sealed Stage 8 artifact;
- rho remains frozen from the sealed Stage 8 artifact;
- radiobiology remains frozen;
- Stage 8 proliferation-survival remains frozen;
- no patient-specific Stage 10 state parameter may be fit to t2.

Only the global model-family choice is selected on the already exposed
development cohort.

## Primary scientific question

Stage 10 is not asking "what is the best new half-life?"

It asks:

> Does separating radiographic clearance from occupancy remove the pressure for
> an ever-longer damaged-state half-life and reduce the regression-case
> overgrowth failures?

## Selection priorities

Evaluate the exact Stage 9 v2 control and all decoupled candidates on the same
24 development patients.

Primary priorities, in order:

1. fewer catastrophic failures than Stage 9 v2;
2. improved regression-subgroup mean delta vs persistence;
3. no material degradation of the growth subgroup;
4. mean Dice not materially worse than Stage 9 v2;
5. lower relative volume error;
6. lower HD95;
7. lower model complexity when performance is effectively tied.

A decoupled candidate should not advance merely because of a tiny aggregate
mean-Dice increase.

## Stop conditions

After this diagnostic:

- if a decoupled candidate reduces catastrophic failures and improves the
  regression subgroup without meaningful global degradation, freeze that
  structure before opening any new reserve patients;
- if all decoupled candidates fail, stop adding latent RT compartments and
  move the next development cycle to the MRI observation model / multimodal
  information rather than adding more treatment-response parameters;
- do not reopen the 120-day half-life sweep.

## Leakage control

Stage 10 development cohort is exactly the same 24 already exposed patients
used by Stage 9.

During Stage 10 model-family selection:

- reserve t2 must remain unopened;
- untouched-holdout t2 must remain unopened;
- no selection criterion may use future reserve outcomes.

Only after Stage 10 structure is frozen may a new reserve-validation subset be
planned.
