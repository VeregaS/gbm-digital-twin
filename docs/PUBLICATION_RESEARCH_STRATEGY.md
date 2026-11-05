# Publication-oriented research strategy — 2026-10-17

Implementation follow-up: [IN_SILICO_LAB_TECHNICAL_SPEC.md](IN_SILICO_LAB_TECHNICAL_SPEC.md)
defines the requested engineering work; [IN_SILICO_LAB_PROGRESS.md](IN_SILICO_LAB_PROGRESS.md)
tracks its state. The scientific study still needs a protocol frozen before
execution; this strategy is not evidence of established novelty or outcomes.

Status: reasoned recommendation for discussion, not a registered experiment or
a claim of established novelty. The user prioritizes scientific articles and
wants to avoid developing a new biological/mathematical model from scratch.

## Recommended research basis

Use the existing published spatial reaction-diffusion/treatment model in
TumorTwin, with an author-provided synthetic HGG case, as the first reference
engine. Build our experiment methodology and reproducible web workspace around
it. The existing reference integration reduces initial engineering work, but
does not yet implement the complete author-demo workflow.

Separate three contributions:
- Biological forward equations: attributed existing published model.
- Experiment design/analysis: our candidate research contribution.
- Web interface/orchestration: implementation and delivery of that contribution.

The website alone, ordinary parameter sliders, 3D views and an existing gradient
calculation are not sufficient evidence of methodological novelty.

TumorTwin is published as:
Kapteyn et al., BMC Medical Informatics and Decision Making 26, 237 (2026),
https://doi.org/10.1186/s12911-026-03520-2
It already provides calibration, treatment models, differentiable sensitivities
and example data; its paper describes UQ as a development direction. Do not
present these existing capabilities as our inventions.

## Prior work that limits novelty claims

1. Chaudhuri et al. (2023) already study Bayesian personalization and
   radiotherapy optimization under uncertainty in a synthetic HGG cohort.
   https://doi.org/10.3389/frai.2023.1222612
2. Hiremath et al. (2025) already study parameter/model identifiability under
   noise in HGG chemoradiation models.
   https://doi.org/10.1098/rsta.2024.0212
   https://pmc.ncbi.nlm.nih.gov/articles/PMC12105797/
3. Pash et al. investigate scalable quantified uncertainty for spatiotemporal
   oncology twins. This is further evidence that simply adding Bayesian
   uncertainty is not automatically novel.
   https://arxiv.org/abs/2505.08927
4. Efficient/multi-fidelity tumor UQ is also an existing topic, including a
   different porous-medium model in this 2026 preprint:
   https://arxiv.org/abs/2606.03607

The scoped search supports engine feasibility and identifies close work; it
does not prove that the proposed combination is the first of its kind. Before
freezing a paper protocol, make a contribution matrix against the closest
papers, including their exact inputs, uncertainties, computational budgets,
endpoints and validation data.

## Proposed first research question

How stable are conclusions of an in silico therapy comparison when biological
parameters, initial tumor state and numerical resolution are uncertain, and
can an experiment controller obtain the same reliable conclusion with fewer
expensive model evaluations?

A narrower first study can focus on the reliability analysis alone. Adaptive
allocation is an optional algorithmic extension, to be included only if the
pilot exposes a useful, measurable problem and the literature comparison
establishes a distinct contribution.

A useful result may be a reproducible map of stable, unstable and unresolved
comparisons, rather than a newly claimed optimal treatment. Do not assume in
advance that rankings will change or that the new controller will improve them.

## Feasible study design to specify before execution

1. Reproduce the author's baseline as published, including initialization and
   combined treatment assumptions. Save reference data/configuration/engine
   hashes and verify temporal/spatial convergence.
2. Use multiple explicitly synthetic initial configurations if making claims
   across tumor geometries. One case is adequate for integration testing, not
   for population-wide biological conclusions.
3. Define a small number of model-supported treatment scenarios, common
   evaluation horizons, endpoints and resource constraints. Avoid the trivial
   result that giving more cytotoxic treatment reduces model tumor burden.
   Tumor-only efficacy is not a clinical toxicity or benefit model.
4. Define biological ranges/distributions from sources or label them as
   exploratory stress-test assumptions. Perturb initial conditions in a
   controlled, recorded way. Synthetic cases are not independent clinical
   patients and sampled parameters need not represent a clinical population.
5. Compare a nominal single-parameter forecast against fixed-budget ensemble
   analysis. If adaptive allocation is developed, compare it against appropriate
   uniform/random or space-filling sampling under the same compute budget.
   Reuse the same virtual inputs for paired scenario comparisons.
6. Use independently sampled evaluation cases/seeds, separate from algorithm
   development. A finer numerical reference is an approximation requiring
   convergence checks, not an exact biological ground truth.
7. Record output spread, frequency of ranking changes within the specified
   simulated population, false confident conclusions relative to the reference,
   unresolved-case frequency, wall time, memory and model-evaluation count.
   Define treatment ties/indifference tolerances before seeing results.
8. Check sensitivity-rank stability and interactions. Local gradients,
   global sensitivity indices and parameter identifiability answer different
   questions; do not use these labels interchangeably. Correlated uncertain
   inputs require a method consistent with those dependencies.
9. If using adaptive sampling/stopping, ensure uncertainty estimates account
   for the design; do not attach ordinary fixed-sample confidence intervals
   after arbitrary repeated peeking. Independent evaluation can test controller
   error even when its internal bound is only empirical.

Start with a small runtime pilot. Choose study size from target precision and
measured compute cost, not an arbitrary promise of hundreds/thousands of full
3D simulations. Current claims of efficiency/performance belong to the
authors' hardware until we measure our own.

## Publication routes

Primary recommendation: a computational/methodological study combining a
reusable experiment platform with an independently evaluated research method.
Possible working focus:
"Reliability of in silico glioma treatment comparisons under parameter,
initial-state and numerical uncertainty."

A software article is another possible route if the platform makes a distinct,
reusable contribution and is evaluated through reference reproduction,
automation, reproducibility and performance. Journal fit and acceptance are
not established by this note.

A clinical efficacy/prognosis article is a different scope: a synthetic study
cannot validate real-patient treatment benefit. Current CFB negative results
remain intact; do not relabel them as a validation of the new platform.

PhysiCell-based GBM immune/oncolytic-virus models are a later alternative if
the scientific question specifically requires individual-cell/immune biology.
They introduce additional stochastic mechanisms and parameter/validation work;
they are not the most direct first path for our existing MRI/PDE codebase.

## Prerequisites and boundaries

- Preserve the TumorTwin research-license constraints documented in
  [IN_SILICO_LAB_PROPOSAL.md](IN_SILICO_LAB_PROPOSAL.md). Article CC-BY licensing
  is distinct from the software/data license. No engine redistribution or
  public deployment is authorized by this strategy note.
- Keep original and changed engine versions explicit. Do not silently amend
  Stage 10 physics or use its failed reserve cohort as tuning/evaluation data
  for a new clinical claim.
- 32 remaining reserve and 21 untouched holdout cases stay closed. A synthetic
  experiment study does not require them.
- No experiments, clinical comparisons, new PDEs, authorship contacts or
  deployments were performed for this strategy checkpoint.
