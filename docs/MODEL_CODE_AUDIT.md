# Predictive model code audit — 2026-10-05

Status: audit completed; hardening verified. Baseline commit:
`72ad7118868ebef8cc1fc7d2c73e4dd0d08cc5fd`.
This file is project context for subsequent agents. It is not a new model
selection or an authorization to reopen reserve/holdout outcomes.

## Scope

Repository inventory: 173 Python source modules (56,508 lines), 132 Python test
files (24,676 lines), 31 frontend TypeScript files (12,620 lines). Audit uses
repository-wide AST/import discovery and focused inspection of the complete
prediction path. Scientific/numerical core receives deeper review than UI and
CLI wrappers. Source inventory alone is not proof that every line is correct.

Review targets: data geometry and observation mapping, PDE discretization,
radiotherapy events, latent compartments and assimilation, D/rho calibration,
cache validity, artifact provenance, cohort/split enforcement, paired metrics,
GUI artifact/model routing and existing tests. Checks may use synthetic inputs
and existing sealed scalar/cache results. No new reserve/holdout t2 is opened.

## First checkpoint: confirmed architectural observations

- Stage 10 reserve validation calibrates D/rho with the Stage 8 single-state
  treatment-memory simulator and forecasts with Stage 10 v/d/q dynamics.
  This parameter transfer is intentional in the sealed diagnostic, but does
  not constitute a calibration of the full Stage 10 model to t0/t1.
- Current MRI state is inferred from GTV geometry via a fixed logistic
  signed-distance profile (width 4 mm, enhancing threshold 0.8). T1Gd intensity,
  FLAIR and ADC do not constrain the current Stage 10 state estimates.
- `calibration_identifiable` currently means a unique grid minimum with both
  parameters bracketed. It is not a likelihood/profile/posterior assessment
  of parameter identifiability or forecast uncertainty.
- GUI artifact loading and PatientTwinService support V2/V3, not Stage 10.
  The research Stage 10 validation path is separate from the interactive
  prediction/artifact path. Repointing existing settings cannot make a Stage 10
  scalar result an interactive Stage 10 frozen prediction.
- The Stage 10 freeze/reveal code does not use t2 to calibrate D/rho. Existing
  reserve failure remains a scientific failure; it must not be explained away
  by changing thresholds or substituting patients.

## Conclusion

The repository has a coherent research pipeline and a plausible
reaction–diffusion/RT model family. It does **not** establish an independent
accuracy advantage over persistence. Frozen Stage 10 failed reserve validation:
mean Dice `0.708427` versus persistence `0.742571`, paired mean delta
`-0.034144`, two catastrophic failures.
See [sealed result](STAGE10_VALIDATION_RESULT.md).

Engineering hardening does not change that scientific verdict. Priority:
align calibration with forecast dynamics, measure parameter/state uncertainty,
and evaluate observation assumptions on development data under a separate
protocol.

## Review coverage

| Area | Main inspected source groups | Assessment |
|---|---|---|
| Dataset/geometry | `data/cfb_metadata.py`, `cfb_treatment.py`, `nifti.py`, `patient_loader.py`; `preprocessing/resampling.py`; `workflows/patients.py`, `stage8_inputs.py`, `stage8_patient.py` | Grid checks, nearest-neighbour masks; eager RANO loading corrected |
| Numerical core | `models/solver.py`, `pirt_solver.py`, `reaction_diffusion.py`, `domain_crop.py`, `pirt.py`, `radiobiology.py`, `spatial_radiotherapy.py`, `rt_schedule.py` | Conservative masked Laplacian and stability bound; no general numerical accuracy certificate |
| State/treatment | `models/observation.py`, `latent_state.py`, `treatment_memory.py`, `delayed_response.py`, `decoupled_damage.py`; Stage 8/9/10 forecast workflows | Hidden-state assumptions, transfer of parameters, capacity clipping |
| Calibration | `calibration/stage8.py`, `grid_search.py`, `refinement.py`, `diagnostics.py`, `cache.py` | Point fit, heuristic identifiability, cache validity and tie reproducibility |
| Scientific protocol | Stage 10 selection/validation/plan/materialization/protocol, Stage 8 data audit, eligibility, prediction and cohort evaluation; metrics/baselines/frozen prediction | Current Stage 10 separates fitting from t2 use; direct validation cohort checks strengthened |
| Interactive path | PatientTwin, artifact/reliability loaders, API config/routes/schemas, frontend model-version rendering | V2/V3 artifacts; separate Stage 10 research path |

Only code/configuration, synthetic inputs, existing sealed scalar/cache results
and t0/t1 masks of five exposed patients were used. No new reserve/holdout t2
was read and no scientific experiment was rerun. The 16 validation patients
are already exposed; 32 remaining reserve and 21 untouched holdout remain closed.

## Accuracy constraints and reproducible probes

These findings identify limitations. They do not establish the cause of a
particular patient's failure or prove that a proposed replacement improves Dice.

### Calibration and forecast mismatch

`calibration/stage8.py::_run_candidate` simulates Stage 8 treatment memory.
`stage10_validation.py` transfers the fitted D/rho to Stage 10 v/d/q dynamics.
Synthetic input: density 0.8, D=rho=0, one day-0 fraction with survival 0.2,
proliferation survival 1, horizon/half-life 60 days. Stage 8 visible density ends
at `0.672000`; Stage 10 at `0.736000`. Their forward maps are different.

D/rho are effective parameters conditional on treatment/observation assumptions.
A matched Stage 10 t0→t1 calibration must be a new development candidate; it
cannot be silently substituted into the completed frozen reserve experiment.

### Observation and hidden state

Stage 10 derives density from GTV geometry with a 4 mm logistic profile and
enhancing threshold 0.8. Its t1 assimilation sets visible density from a mask
while retaining/reconciling hidden treatment state. One mask cannot uniquely
identify viable, damaged, inert and proliferative components.

Optional modality support elsewhere does not mean frozen Stage 10 uses MRI
intensity, FLAIR or ADC. The prior Reference Fidelity ADC branch failed its own
development gate; more modalities alone are not an accuracy guarantee.

TCIA describes rigid registration to t0 T1Gd and supplies GTV annotations.
These are not simply unregistered arrays with matching shapes. Equal geometry
still does not prove local alignment or annotation consistency for each case.
[Official dataset description](https://www.cancerimagingarchive.net/collection/cfb-gbm/).

### Identifiability and uncertainty

The current label checks a unique minimum within a fixed `1e-12` loss
tolerance and parameter bracketing. It does not estimate profile curvature,
posterior modes, segmentation uncertainty or forecast spread.

A nine-point synthetic surface
`loss = 1 + 1e-9*(abs(D-0.01) + abs(rho-0.02))` can be labelled identifiable
despite being nearly flat. Existing reserve scalar diagnostics: mean t0→t1
calibration soft Dice `0.611364`, 8/16 non-identifiable, 6/16 fitted rho=0.
Soft calibration Dice and hard evaluation Dice are different quantities.
Exposed-case associations cannot define a new reliability/selection threshold.
All 16 saved best minima were unique within the current tolerance: exact cache
ties did not explain this reserve outcome.

MRI parameter non-identifiability and correlated/multiple parameter solutions
are discussed in the primary
[Bayesian personalization study](https://ohsu.elsevierpure.com/en/publications/mri-based-bayesian-personalization-of-a-tumor-growth-model/).
This supports investigating uncertainty, not a claim that Bayesian calibration
will improve this repository's Dice. GUI reliability already states that it is
not a calibrated probability of correctness.

### Stage 10 implicit mass sink

`decoupled_damage_step` diffuses viable density, then caps it by
`1-damaged-inert`. Flux entering an occupied voxel can be discarded after
leaving the donor. The masked Laplacian itself is conservative.

Probe: shape 3×3×3, v[0,1,1]=1, q[1,1,1]=1, all other v/d/q=0,
modifier=1, D=0.2, rho=0, spacing 1 mm, dt=0.5 day, half-life 60 days.
One step changes sum(v) from 1 to about `0.90000004`, with no RT, growth or
damaged-state decay. Initial occupancy is valid and dt satisfies the bound.

The frozen equation/projection was **not changed**. Capacity-aware conservative
flux or an explicit death mechanism requires a new model definition and
development ablation. First quantify clipping loss on synthetic/development
trajectories. No evidence presently links this sink to the reserve catastrophes.

### Numerical sensitivity

The core uses explicit stepping, float32 state, a 2 mm research grid and
configured dt=2 days. Existing tests cover pure masked diffusion mass,
crop/full-domain equivalence and treatment-event ordering.

Logistic ODE probe against its exact solution:
D=0, rho=0.055/day, c0=0.2, horizon=28 days.

| dt, days | Absolute density error |
|---:|---:|
| 2 | 0.00616533 |
| 1 | 0.00304728 |
| 0.5 | 0.00151441 |
| 0.25 | 0.00075485 |

This is expected first-order time convergence, not proof of instability.
Spatial/time convergence and thresholded-mask sensitivity need development
checks; smaller dt/spacing is not automatically better generalization.

Limited t0/t1 volume checks for exposed IDs 8,18,108,73,254 found changes from
native to 2 mm nearest-neighbour masks between about -2.35% and +0.39%.
This does not measure boundary Dice error or audit every patient. There is no
basis to blame reserve failure entirely on resampling.

### Biological assumptions

Selected Stage 10 has uniform scalar D and the selected uniform RT branch,
a reconstructed five-fractions/two-day-gap schedule, fixed global radiobiology
and proliferation survival, permanent inert retention and no recovery of the
treatment modifier. TMZ timing/dose information is insufficient for the frozen
experiment; chemotherapy response is not explicitly identified.

PIRT loss `(1-S)*c*(1-c)` is a deliberate published-style assumption, not an
accidental missing multiplication by S. See the primary
[Holdsworth et al. model, equations 2–4](https://faculty.washington.edu/trawets/rds/pdf/ho12_pmb57p8271to8283.pdf).
Its weak effect near saturation is a model sensitivity question, not grounds
to rewrite the frozen equation.

## Evaluation and platform boundaries

- Stage 10 freezes D/rho before t2 loading; no t2 mask is passed to its forecast
  function. The validation loop nevertheless loads the target before computing
  the forecast and does not persist a per-patient forecast seal before reveal.
  Future prospective evaluation should obtain horizon from allowed MRI timing
  metadata, save/hash the full forecast, then decode the target.
- Legacy `evaluation/cohort.py` loads t2 eagerly and uses RANO-based cohort
  completeness. It is not the sealed Stage 10 entry point and must not discover
  or replace reserve patients.
- HD95/centroid are undefined for an empty mask; optional means omit undefined
  values. Future protocols should record undefined counts and prespecify their
  handling. All 16 current forecasts were nonempty, so this did not explain
  the reported reserve means.
- GUI/PatientTwinService load V2/V3 frozen artifacts. Research Stage 10 scalar
  results are not an interactive Stage 10 forecast. Loaded model versions are
  exposed by API/frontend; no false Stage 10 label was found in that path.
- Cache keys bind inputs/settings but not every solver source/library version.
  Future numerical/dynamical changes need explicit cache versioning and exact
  code/environment provenance.

## Confirmed implementation fixes

Valid frozen settings, equations, cohort, selection and thresholds are unchanged.

1. Restore full geometry for zero-duration cropped reaction–diffusion runs.
2. Reject invalid/nonfinite timing and dt at/below integration resolution before
   compartment loops; reject nonfinite growth/state/event inputs in touched
   core contracts.
3. Reject NaN/Inf summary/config values before Stage 10 verdict comparisons and
   invalid catastrophic counts. Previously the pure summary function could
   return pass for NaN, but the JSON writer's `allow_nan=False` would still
   have prevented sealing that invalid result.
4. Check exact deterministic cohort, seed, remaining reserve and holdout in
   direct validation as well as materialization before patient access.
5. Load RANO outcomes lazily on explicit request. The timeline loader previously
   read them even though Stage 10 did not use them to fit D/rho or select cases.
6. Treat nonfinite/out-of-range/corrupt calibration metrics as cache misses.
7. Preserve original uncached grid ordering for exact ties after partial cache
   resume in Stage 8 and legacy search. This fixes cache-dependent choice,
   retaining untied minima and the normal uncached search result.

Tests exercise numerical contracts, zero-horizon geometry, poisoned-cache
recomputation, tied-cache resume, lazy outcomes, finite guardrails and direct
validation rejection before patient access.

## Next accuracy work: ordered proposal, not an activated experiment

1. Define a separate development protocol on the existing 24 development cases.
   Keep all 16 exposed reserve cases descriptive only. Specify patient-grouped
   comparison, candidate budget, selection, numerical tolerances, baselines and
   catastrophic criteria before evaluating new candidates. The
   [conditional observation protocol](OBSERVATION_MODEL_NEXT_CYCLE.md) has a
   different trigger/frozen calibration and is not automatically activated.
2. Audit development t0/t1 geometry/units, local registration, annotation
   provenance, boundary resampling, modality scale/availability, treatment
   timing and mass/time/grid convergence. Do not exclude patients using t2 error.
3. Test minimal matched calibration/forecast dynamics. Evaluate the capacity
   sink explicitly. Keep the frozen model as an exact reference and isolate
   changes with single-factor ablations.
4. Propagate near-optimal D/rho ensembles and profile-loss sensitivity, including
   segmentation/profile perturbations. Report forecast spread. Such an ensemble
   is not automatically a calibrated confidence interval. Validate uncertainty
   and any persistence fallback using development data only.
5. Then compare predefined observation/assimilation alternatives and usable
   FLAIR/ADC branches after unit/scale/annotation QC. Preserve paired subgroup
   controls and all-patient analysis. Raw FLAIR intensity is not a tumor mask.
6. Freeze code, global settings, calibration, cache versions and full forecasts.
   Define a new plan before opening any still-closed reserve outcomes. Advance
   to untouched holdout only after that plan passes; external/Burdenko testing
   is a later generalization step.

Avoid adding unidentifiable compartments or sweeping until an appealing result
appears. Improvement on 24 reused development cases is development evidence
and requires independent confirmation. No method can promise maximum accuracy.

## Verification checkpoint

- Ruff passed.
- Full Python 3.11 suite, original scientific runtime against audited checkout:
  **571 passed**, two dependency deprecation warnings.
- Python 3.13 suite passed at the preceding 568-test checkpoint; the final three
  additions test tied-cache resume and the direct cohort boundary.
- Frontend ESLint and production build passed.
- GitHub Actions must be checked for this change's exact commit, not a prior
  green run. Run status is available in the repository Actions history.
- No frozen config, split, threshold, completed result or patient dataset was
  rewritten. No new accuracy outcome is claimed.
