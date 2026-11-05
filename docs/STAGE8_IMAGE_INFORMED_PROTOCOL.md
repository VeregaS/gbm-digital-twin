# Stage 8 — image-informed chemoradiation digital twin

## Status

Stage 8 starts a new development cycle after the V2/Accuracy-V1 and V3
experiments. V2 Accuracy-V1 remains the current reference implementation.
V3 (global exponentially decaying post-RT kill) is retained as a negative
ablation: it improved calibration diagnostics but reduced t2 Dice on the
already exposed mini cohort.

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

Stage 8 therefore changes the inverse problem before adding more biological
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
are retained only as versioned observation-model hypotheses. They are not
asserted to be measured cell densities in CFB-GBM.

Likewise, Stage 8 includes the legacy `alpha=0.01/Gy` plus `0.10`, `0.12`, and
`0.14/Gy`. The latter values bracket the clinical-reference region used for
the development experiment. The chosen alpha is treated as an effective
cohort-level hyperparameter rather than a directly measured patient-specific
radiosensitivity.

## Leakage protocol

The ten original mini-cohort IDs

`8, 18, 25, 42, 65, 99, 108, 112, 214, 251`

are permanently marked `development-exposed`, because their t2 outcomes have
already been inspected during V2/V3 development.

A sealed Stage 8 data audit assigns the remaining eligible CFB cases using
only MRI/GTV availability, RT schedule completeness, RTDOSE availability,
data-richness tier, broad RT regimen, and a versioned deterministic hash seed.
The audit never opens RANO outcomes and never loads t2 image content.

The split has three logical roles:

1. `development-exposed`: previously revealed cases; model-family selection is
   allowed to use their t2.
2. internal validation: previously unexposed non-holdout cases; the selected
   model is evaluated once here after selection is sealed.
3. `untouched-holdout`: final CFB test; t2 stays sealed until model and
   protocol are fixed after internal validation.

Stage 8 audit schema v1 uses the label `development` for role 2. Downstream
validation treats that label as `internal-validation`; the semantic role is
explicit in the validation artifact and leakage contract.

If internal-validation outcomes are subsequently used to change the model,
those patients become development-exposed for the next protocol version. The
final untouched holdout remains sealed.

## Observation model

`gbm_twin.models.observation` separates the biological state from the MRI
observation surface. For an enhancing/GTV mask, a signed-distance logistic
field is shifted so the mask boundary corresponds to the configured enhancing
detection threshold (default `0.80`) rather than automatically to `0.5`.

An optional infiltrative mask can provide a lower-density surface (default
`0.16`). Raw FLAIR is not automatically thresholded into this mask. A future
FLAIR-derived infiltrative mask must have an explicit segmentation method and
provenance before this branch of the model can be enabled.

DWI/ADC is audited and prepared but is not currently converted directly to
cell density. Published ADC-cellularity mappings are model-dependent, so this
conversion must be separately validated before use.

## Spatial radiotherapy

`gbm_twin.models.spatial_radiotherapy` supports voxel-wise LQ survival

`S(x) = exp(-alpha*d(x) - beta*d(x)^2)`.

RTDOSE is resampled to the exact T1Gd reference geometry, not merely to the
same nominal voxel spacing. Dose units fail closed: an unexpected Gy/cGy scale
must be investigated rather than guessed.

The first spatial-dose implementation converts one cumulative RTDOSE map to a
per-fraction map under the explicit assumption that each fraction shares the
same relative spatial dose distribution. Sequential boost/adaptive plans that
violate this assumption must not be silently represented by this model.

## Persistent treatment state

The Stage 8 single-species treatment-memory model maintains two fields:

- tumor density `c(x,t)`;
- proliferative-capacity modifier `m(x,t)`.

Between fractions,

`dc/dt = div(D grad c) + rho*m*c*(1-c)`.

At a radiation fraction, `c` receives an immediate density-dependent PIRT/LQ
update while `m` receives a multiplicative persistent suppression factor. At
t1, MRI assimilation updates the density field but does not reset `m`. This is
the key distinction from V2/V3 hard assimilation, which discarded hidden
treatment-response history.

A future multi-compartment proliferative/damaged/senescent model remains a
candidate only if this simpler persistent-state family fails and the extra
parameters can be constrained.

## Chemotherapy

CFB-GBM represents standard chemoradiation, but the current project metadata
reader does not provide an explicit patient-level temozolomide dose calendar
suitable for mechanistic simulation. Therefore `chemotherapy.enabled=false`.
TMZ must not be synthesized from an assumed schedule and presented as a
patient-specific input.

## Nested model-family selection

Stage 8 deliberately does **not** run a full Cartesian product of every alpha,
dose representation, and memory parameter. Such a search is slower and makes
mechanistic attribution harder because several effects can compensate for one
another during patient-specific `D/rho` calibration.

The sealed selector uses a fixed sequential nested-ablation design:

1. **Radiobiology phase** — uniform dose, no treatment memory; compare all
   configured effective alpha values.
2. **Dose phase** — fix the selected alpha; compare uniform versus spatial
   RTDOSE.
3. **Treatment-memory phase** — fix alpha and dose representation; compare
   `SF_prolif=1` against the configured persistent-memory candidates.
4. **Final alpha-sensitivity phase** — keep the selected dose/memory structure
   and re-check all configured alpha values.

With the current protocol this produces at most about eleven unique candidates
along one sequential path instead of the 32-candidate full Cartesian family.
Repeated candidates are reused from memory/disk cache.

Each phase compares candidates on the same paired development-exposed cohort.
The within-phase ranking is:

1. higher mean t2 Dice;
2. higher median t2 Dice;
3. lower mean relative volume error;
4. lower mechanism-complexity rank;
5. deterministic candidate-ID tie-break.

Leave-one-patient-out statistics are recorded as **within-phase stability
diagnostics**. They are not presented as an independent estimate of the full
adaptive selection pipeline. Generalization is tested by the subsequent
one-shot internal-validation cohort.

## Performance contract

The Stage 8 workflow separates data preparation from candidate evaluation.
t0/t1, the allowed t2 target, registered geometry, treatment schedule, latent
initial state, and RTDOSE are prepared once per patient and reused across
candidate evaluations. Model candidates therefore do not repeatedly perform
MRI/RTDOSE disk I/O and resampling.

Calibration cache keys include the latent state, masks, geometry, absolute
start time, treatment events, objective configuration, and candidate `D/rho`.
Changing scientific inputs creates a new cache namespace rather than reusing a
stale result.

## Validation gates

The intended sequence is:

`data audit -> development-exposed selection -> sealed model -> internal validation -> final freeze -> untouched-holdout reveal -> external validation`.

The internal-validation workflow verifies the SHA of the audit, protocol,
experiment config, and sealed model-selection artifact before loading any new
t2. It compares the selected model against persistence patient-by-patient and
records Dice, relative volume error, HD95, centroid distance, and calibration
diagnostics. It never loads untouched-holdout t2.

Only after this gate is acceptable is a final untouched-holdout freeze/reveal
scientifically meaningful. Burdenko remains external validation after the CFB
protocol is fixed.

## What Stage 8 explicitly does not claim

- MRI detection thresholds are not ground-truth cell densities.
- Effective alpha is not a direct assay of intrinsic radiosensitivity.
- Persistent proliferation suppression is not claimed to be the unique
  biological mechanism of delayed response.
- A cumulative RTDOSE map is not assumed to encode fraction/boost history when
  that information is absent.
- Raw FLAIR and ADC are not silently converted into tumor cell density.
- Results from the already exposed mini cohort are development performance,
  not independent validation.
- Internal validation ceases to be independent if its outcomes are used to
  redesign the model.
- None of these research outputs are for clinical decision support.
