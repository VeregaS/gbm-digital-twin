# Stage 8 — image-informed chemoradiation digital twin

## Status

Stage 8 starts a new development cycle after the V2/Accuracy-V1 and V3
experiments. V2 Accuracy-V1 remains the current reference implementation.
V3 (global exponentially decaying post-RT kill) is retained as a negative
ablation: it improved calibration diagnostics but reduced held-out t2 Dice on
the already exposed mini cohort.

Stage 8 must not overwrite any V2/V3 artifacts.

## Why the model class changes

The previous pipeline treated a binary GTV as if it were a direct tumor-cell
density observation and reconstructed a logistic latent field whose GTV
boundary was effectively centered near density 0.5. It also calibrated `D`
and `rho` over a treated t0→t1 interval, used a scalar RT schedule, fixed
`alpha=0.01/Gy`, and reset the latent density to the observed t1 GTV before
forecasting t1→t2.

Those assumptions are too strong for the CFB-GBM setting. CFB is a
chemoradiation cohort, not an untreated natural-history cohort. Published
PI/PIRT work typically estimates intrinsic proliferation/invasion from serial
pre-treatment imaging and then models spatially varying RT response. More
recent high-grade-glioma model families distinguish immediate treatment
response from persistent changes in proliferative capacity and perform model
selection rather than assuming one response mechanism a priori.

Stage 8 therefore changes the *inverse problem* before adding more biological
parameters.

## Literature anchors

The implementation is informed by the following model families:

- Rockne et al., *Predicting efficacy of radiotherapy in individual
  glioblastoma patients in vivo: a mathematical modeling approach*, Phys Med
  Biol. 2010. DOI: `10.1088/0031-9155/55/12/001`.
- Rockne et al., *Toward Patient-Specific, Biologically Optimized Radiation
  Therapy Plans for the Treatment of Glioblastoma*, PLOS ONE. 2013. DOI:
  `10.1371/journal.pone.0079115`.
- Hormuth et al., *Image-based personalization of computational models for
  predicting response of high-grade glioma to chemoradiation*, Scientific
  Reports. 2021. DOI: `10.1038/s41598-021-87887-4`.
- Liu et al., *A time-resolved experimental–mathematical model for predicting
  the response of glioma cells to single-dose radiation therapy*, Integrative
  Biology. 2021. DOI: `10.1093/intbio/zyab010`.
- Hormuth et al., *Forecasting chemoradiation response mid-treatment for
  high-grade gliomas through patient-specific biology-based modeling*, Int J
  Radiat Oncol Biol Phys. 2025. DOI: `10.1016/j.ijrobp.2025.07.1423`.

The classic `~0.80` T1Gd and `~0.16` T2/FLAIR cell-density detection levels
are retained only as **versioned observation-model hypotheses**. They are not
asserted to be measured cell densities in CFB-GBM.

Likewise, the Stage 8 radiobiology candidates include the legacy
`alpha=0.01/Gy` plus `0.10`, `0.12`, and `0.14/Gy`. The latter values bracket
the pooled clinical GBM estimate around `alpha≈0.12/Gy`; Stage 8 treats the
chosen alpha as an effective cohort-level development hyperparameter rather
than co-fitting a patient-specific alpha together with `D/rho` from one
post-treatment interval.

## Leakage protocol

The ten original mini-cohort IDs

`8, 18, 25, 42, 65, 99, 108, 112, 214, 251`

are permanently marked `development-exposed`, because their t2 outcomes have
already been inspected during V2/V3 development.

A sealed Stage 8 data audit assigns the remaining eligible CFB cases using
only:

- MRI/GTV availability metadata;
- RT schedule completeness;
- RTDOSE availability;
- data-richness tier (`t1gd-only`, `t1gd-flair`, `mpmri`);
- broad RT regimen (conventional vs hypofractionated);
- a versioned deterministic hash seed.

The audit never opens RANO outcomes and never loads t2 image content. The
stratified untouched holdout is therefore chosen before its outcome is seen.
The non-holdout, previously unexposed cases are a reserve for internal
validation; they are not used by the initial model-family selector.

The Stage 8 model selector is allowed to load t2 only for
`development-exposed` cases. It performs leave-one-patient-out validation of
global model candidates. The untouched holdout is never loaded by selection.

## Observation model

`gbm_twin.models.observation` separates the biological state from the MRI
observation surface.

For an enhancing/GTV mask, a signed-distance logistic field is shifted so the
mask boundary corresponds to the configured enhancing detection threshold
(default `0.80`) rather than automatically to `0.5`.

An optional infiltrative mask can provide a lower-density surface (default
`0.16`). **Raw FLAIR is not automatically thresholded into this mask.** A
future FLAIR-derived infiltrative mask must have an explicit segmentation
method and provenance before this branch of the model can be enabled.

DWI/ADC is audited and prepared but is not currently converted directly to
cell density. This is deliberate: published ADC-cellularity mappings are
model-dependent and more recent biopsy-based evidence argues against treating
ADC as a universally valid single predictor of glioma cell density.

## Spatial radiotherapy

`gbm_twin.models.spatial_radiotherapy` supports voxel-wise LQ survival

`S(x) = exp(-alpha*d(x) - beta*d(x)^2)`.

RTDOSE is resampled to the exact T1Gd reference geometry, not merely to the
same nominal voxel spacing.

Dose units fail closed. In `auto` mode the loader accepts only a plausible Gy
or cGy interpretation relative to the prescribed course dose. An unexpected
scale must be investigated explicitly.

The first Stage 8 spatial-dose implementation converts one cumulative RTDOSE
map to a per-fraction map under the explicit assumption that each fraction
shares the same relative spatial dose distribution. This is appropriate only
for a single uniform plan. If a patient has sequential boost/adaptive plan
information that violates this assumption, the spatial candidate must not be
silently used.

## Persistent treatment state

The Stage 8 single-species treatment-memory model maintains two fields:

- tumor density `c(x,t)`;
- proliferative-capacity modifier `m(x,t)`.

Between fractions,

`dc/dt = div(D grad c) + rho*m*c*(1-c)`.

At a radiation fraction, `c` receives an immediate density-dependent PIRT/LQ
update, while `m` receives a multiplicative long-term suppression factor.
This is a deliberately parsimonious analogue of published models in which RT
has both immediate survival effects and longer-lived effects on the actively
proliferating fraction.

At t1, MRI assimilation updates the density field but **does not reset `m`**.
This is the key distinction from V2/V3 hard assimilation, which discarded the
hidden treatment-response history.

A future multi-compartment proliferative/damaged/senescent model remains a
candidate only if the simpler persistent-state model fails and the additional
parameters can be constrained. Stage 8 does not add compartments merely for
biological realism.

## Chemotherapy

CFB-GBM represents standard chemoradiation, but the current project metadata
reader provides RT start/dose/fractions and does not provide an explicit
patient-level temozolomide dose calendar suitable for mechanistic simulation.

Therefore `chemotherapy.enabled=false` in the Stage 8 protocol. TMZ must not
be synthesized from an assumed schedule and presented as patient-specific
input. If an explicit treatment source is added later, chemotherapy can become
another nested candidate with its own provenance.

The selected `alpha` is consequently described as an **effective** radiation
response parameter; it may absorb treatment effects that are not separately
identifiable in this dataset, as older PIRT literature also cautions for
chemoradiation cohorts.

## Model family and selection

The initial model family crosses three controlled mechanisms:

1. uniform vs spatial RT dose;
2. global effective `alpha` candidates;
3. no persistent proliferation memory (`SF_prolif=1`) vs configured
   persistent-memory candidates.

Every candidate still receives patient-specific `D/rho` calibration on
t0→t1. Candidate comparison itself uses the already exposed development t2
outcomes. A candidate must cover the complete paired development cohort to be
eligible; a spatial model cannot win by evaluating itself only on an easier
subset with local RTDOSE files.

Candidates are ranked by:

1. higher mean development t2 Dice;
2. higher median development t2 Dice;
3. lower mean relative volume error;
4. lower mechanism-complexity rank;
5. deterministic candidate ID tie-break.

A leave-one-patient-out estimate is recorded separately to expose unstable
model choice on the small exposed cohort.

The final Stage 8 candidate is then frozen before any previously unexposed t2
is revealed. Internal validation is revealed before the final untouched
holdout. If the model is changed using internal-validation outcomes, those
patients become development data and the untouched holdout remains sealed.

## What Stage 8 explicitly does not claim

- The MRI detection thresholds are not ground-truth cell densities.
- Effective alpha is not a direct assay of intrinsic radiosensitivity.
- Persistent proliferation suppression is not claimed to be the unique
  biological mechanism of delayed response.
- A cumulative RTDOSE map is not assumed to encode fraction/boost history when
  that information is absent.
- Raw FLAIR and ADC are not silently converted into tumor cell density.
- Results from the already exposed eight evaluable mini-cohort cases are
  development performance, not independent validation.
- None of these research outputs are for clinical decision support.
