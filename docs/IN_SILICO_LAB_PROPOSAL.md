# Proposed pivot: GBM in silico experimental laboratory

Implementation follow-up: the user requested a complete specification after
discussing this proposal. Read [IN_SILICO_LAB_TECHNICAL_SPEC.md](IN_SILICO_LAB_TECHNICAL_SPEC.md)
and [IN_SILICO_LAB_PROGRESS.md](IN_SILICO_LAB_PROGRESS.md) for current scope and
execution order. This document retains the initial research rationale.

Research checkpoint: 2026-10-17. Status: proposal in response to the user's
question about using an existing digital twin and building an experiment website.
This is not approval of a final engine/license/deployment choice and does not
activate a new clinical prediction experiment.

## Product objective

Build a web laboratory around an existing published tumor model and a prepared
reference case. Users choose a case, modify model-supported biological/treatment
parameters, run scenarios, compare trajectories and perform sensitivity studies.

The user does not need to upload and recalibrate a different patient's MRI for
each experiment. Initial data can be a fixed author-provided synthetic case,
initialized/calibrated once and versioned. New real-patient personalization can
remain a separate future extension.

Use clear labels: synthetic HGG reference case, virtual patient, simulation
under model assumptions. A virtual case is not an independently validated
clinical twin of a particular person. HGG also should not automatically imply
molecularly confirmed IDH-wildtype GBM.

## Verified primary candidate: TumorTwin

- Repository: https://github.com/OncologyModelingGroup/TumorTwin
- Current main, checked 2026-10-17:
  `bedf90a6d47ba48cf5cdb25901967d84730061d1` (2026-04-07).
- This is already the upstream commit pinned by our reference adapter.
- Ready case: `input_files/HGG_demo_001`; other HGG example folders also exist.
- Tutorial: https://oncologymodelinggroup.github.io/TumorTwin/tutorials/HGG_Demo/
- Sensitivities: https://oncologymodelinggroup.github.io/TumorTwin/tutorials/HGG_Gradients/
- Paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC13330372/

The repository contains a synthetic HGG example, input images/masks and a
treatment configuration. The tutorial supports 3D reaction-diffusion simulation,
RT/chemotherapy specifications, gradients, calibration and an alternative
treatment scenario. The paper describes an idealized synthetic demonstration,
not a validation of real-patient treatment predictions.

Our current integration:
`src/gbm_twin/reference/tumortwin.py`,
`scripts/reference/tumortwin_worker.py`,
`scripts/reference/bootstrap_tumortwin.ps1`.
It is an isolated reference/CFB adapter, not yet a complete web adapter for the
author's demo and all its treatment/sensitivity features. Do not claim that the
new website already exists.

The earlier negative CFB benchmark is preserved in
[REFERENCE_FIDELITY_V2_RESULT.md](REFERENCE_FIDELITY_V2_RESULT.md).
It evaluated a different task from reproducing an author's synthetic case.
Changing product scope does not convert that negative clinical-data benchmark
into evidence of accuracy.

## License constraint for engine selection

Authoritative text:
https://github.com/OncologyModelingGroup/TumorTwin/blob/bedf90a6d47ba48cf5cdb25901967d84730061d1/LICENSE.md

The UT Austin Research License grants specified academic/research/experimental/
personal uses, excludes commercial use and restricts distribution, sublicensing
and transfer. It also imposes derivative-product and attribution requirements.
Public source availability is not permission to redistribute freely.

Do not vendor or publish the engine/demo data as part of our site/repository
without establishing applicable rights. Whether our intended hosted service
fits the grant needs to be resolved before public deployment. Reading and
research planning here do not authorize contacting the authors on the user's
behalf. Exact data/atlas rights also need verification for redistribution.

Preferred engineering arrangement is an engine adapter with explicit
version/license/provenance, so the platform does not depend on a single
restricted implementation. Isolation is an engineering boundary, not a
workaround for licensing obligations.

## Other checked candidates

| Candidate | Fit | Current limitation |
|---|---|---|
| PhysiCell-GBM-oHSV1 | Published GBM agent model for virus, stroma and immune-cell experiments | Different biological scope; not a ready human MRI growth/RT twin; extension/data licensing and reproducibility still need review |
| Willcox et al. 2023 predictive HGG twin | Published in silico cohort and uncertainty-aware RT comparison | The code URL supplied in the paper returned 404 through both browser and GitHub API; do not present it as a verified runnable download |

PhysiCell model/code:
https://github.com/adriannejnner/PhysiCell-GBM-oHSV1
Primary paper:
https://pmc.ncbi.nlm.nih.gov/articles/PMC9142563/
The authors also link an online nanoHUB application; its present runtime
availability was not tested:
https://nanohub.org/tools/ohsv1gbmapp

Willcox-group paper:
https://pmc.ncbi.nlm.nih.gov/articles/PMC10598726/
Unavailable code URL checked:
https://github.com/Willcox-Research-Group/predictive-dtwin-glioma-frontiers

Do not recommend a repository simply because its README calls it a digital
twin or uses a permissive license. Require runnable cases, traceable methods,
usable data and reproducible reference outputs.

## Proposed first usable version

1. One immutable reference case with source, engine version, parameter units,
   reference outputs and data provenance. Reproduce it before building scenario
   claims. Prefer the author demonstration as a whole rather than replacing
   initialization/treatment assumptions silently.
2. Scenario editor for quantities actually supported by that model: growth,
   migration, treatment sensitivity and RT/CT timing/dose. Preserve the original
   baseline and save every modification.
3. Run queue with progress and cancellation. Show 2D/3D density over time,
   model-derived tumor burden and treatment timeline. Do not promise that full
   3D simulation or a large cohort recomputes instantly on every slider move.
4. Paired scenario comparisons and exports with units, seeds, full parameter
   configuration, engine/data hashes and numerical settings.
5. Sensitivity screening and virtual cohorts drawn from explicitly documented
   distributions. Local gradients are not automatically global sensitivity,
   and simulation intervals are not automatically clinical confidence intervals.

Existing frontend/API/visualization infrastructure can be reused. The existing
patient forecast views should remain distinguishable from the new virtual-case
experiment workspace.

## Scientific contribution and evaluation

The proposed contribution is reproducible experiment orchestration, parameter
exploration, sensitivity analysis, cohort design and comparative visualization.
Merely wrapping a notebook with a web page is not the whole research contribution.
Whether this meets dissertation requirements depends on the actual approved
topic and institutional criteria.

Evaluate the platform through reproduction of reference trajectories, numerical
convergence, verified treatment timing, gradient/finite-difference agreement,
repeatability, batch execution and measured runtime. Real-patient predictive
accuracy is a separate claim requiring real-patient validation.

Keep Stage 10 results, configs and cohort identities intact. Do not open the
32 still-closed reserve cases or 21 untouched holdout cases to implement a
synthetic experimental laboratory. No dataset read, model run, engine
redistribution or deployment was performed for this research checkpoint.
