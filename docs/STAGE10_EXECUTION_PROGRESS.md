# Stage 10 execution log

## 2026-10-05 — source acquisition checkpoint

The user reran commit `f9c5d98`: 473 tests and Ruff passed. The existing sealed
16-patient plan was reused, but source preflight found all 144 required NIfTI
files missing from `D:/Datasets/CFB-GBM/data`. No reserve t2 image was decoded
and no patients were substituted.

The authorized next work is to obtain the official inputs selectively, prepare
this exact cohort, run frozen reserve validation, seal/report its result,
update the scientific status, and push tested code/docs. The untouched holdout
and remaining 32 reserve patients must remain closed unless their separate
predeclared gate and protocol permit advancement.

Official source: https://www.cancerimagingarchive.net/collection/cfb-gbm/
(Version 4, updated 2026-09-11). The full NIfTI collection is about 208 GB.
Local free space is insufficient for the full collection; selective acquisition
must use only the sealed required paths. MRI materialization remains opaque
byte transfer; each t2 is interpreted only after that patient's D/rho freeze.

### Official transport and layout verified

The official public Faspex link points to package 1345, `CFB-GBM version 4`.
Its standard public-link OAuth flow succeeds. Direct passcode calls are not
accepted for browsing on this deployment, so acquisition must use the normal
public-link authorization code flow and keep scoped tokens in memory.

The remote tree uses `/CFB-GBM/015/t0/15_t0_*.nii.gz`: patient folder names are
zero-padded while filenames use the integer ID. File entries are server-side
symbolic links. This is a deterministic representation of patient 15, not a
cohort substitution. The local tree uses `15/t0/15_t0_*.nii.gz`.

The installed Aspera executable successfully transferred one brain-mask file
using the official package's scoped token and IBM's publicly distributed SSH
transport key. The full remote dry run then verified all 144 required paths for
exactly the 16 sealed patients. No MRI image content was decoded.

### Selective downloader implemented and tested

The materializer now supports `--download-missing`, exposed by the PowerShell
runner as `-DownloadMissing`. The downloader pins the official version-4 package,
checks remote availability before transfer, preserves patient identity and local
paths, and records byte size/SHA-256 in a sealed acquisition receipt. It never
downloads unselected patients or unused MRI modalities. Transfer tokens stay in
memory/environment and are excluded from command arguments and saved receipts.
Completed files can be reused after interruption; modified or unverified existing
files are rejected.

Targeted acquisition/materialization tests: 20 passed; full suite: 483 passed;
Ruff and PowerShell syntax passed. Frozen artifacts were copied byte-for-byte
into the isolated checkout so validation can record a clean committed revision.
At this checkpoint, 144-file acquisition and hardlink preparation were started. Reserve
evaluation remains pending until preparation and full code checks complete.

The first downloader CI run completed frontend lint/build successfully and found
one overlong Python comment. That comment was wrapped; the root data ignore rule
is anchored to `/data/` so new source/test modules under `data` are included in
both Git and lint discovery. The full local Ruff check now includes those files.

### Acquisition and preparation complete

All 144 official files for the exact sealed cohort were acquired successfully:
2,356,539,655 bytes (about 2.20 GiB). All 144 prepared inputs were created as
hardlinks under `D:/Datasets/CFB-GBM/patients`, without duplicating the source
storage. The acquisition receipt and its SHA seal are saved under
`D:/Datasets/CFB-GBM/data`. No MRI image content was decoded by acquisition.
Receipt SHA-256:
`900768007d358a25659db1503a62f92ccca6954a5d67503b330aa3c4eaddaf20`.

The corrected downloader CI is green:
https://github.com/VeregaS/gbm-digital-twin/actions/runs/37241838045

Full tests also passed in the original project environment: Python 3.11.9,
NumPy 2.4.6, SciPy 1.17.1; 483 tests passed. Validation will use this environment
with the clean isolated checkout's code, four calibration workers, the original
sealed plan/configs, and the standard cache/result locations. Workers affect
execution concurrency only; no scientific parameter or selection rule changes.

Next checkpoint: run the frozen reserve experiment and seal its verdict. The
untouched holdout and remaining 32 reserve cases remain unopened.

### Interim execution checkpoint — first five patients

The real run has completed patients 15, 47, 57, 71 and 73. The log records D/rho
freeze before each t2 reveal. Patient 73 has Dice delta `-0.3621` versus
persistence, below the prespecified catastrophic threshold `-0.10`. Therefore
the zero-catastrophic-failure advancement condition cannot pass for this cohort.

The experiment continues through all 16 prespecified patients without changing
parameters or selecting alternatives. Aggregate metrics and the formal verdict
will be recorded only after the complete result is sealed. Untouched holdout
will not be opened; failure analysis must not tune on these reserve outcomes.

### Preparation reuse verified during execution

The real acquisition/materialization dry run with `--download-missing` verified
the sealed receipt and all local source hashes. It reported `created: 0`,
`reused: 144`, with the same 16 patient IDs. No network transfer, MRI decoding,
or additional data writes were needed. After ten completed patients the
experiment continues unchanged; all final metrics remain pending.

### Frozen reserve experiment complete and sealed

All 16 prespecified patients completed successfully using the clean execution
commit `f02a553ad548d70997d5f32df4a0880d7adb9e30`. Computational execution
completed; the scientific decision is `validation_failed`.

- Mean Twin / persistence Dice: `0.708427 / 0.742571`.
- Mean / median paired delta: `-0.034144 / 0.000000`.
- Bootstrap 95% CI: `[-0.087773, +0.005257]`.
- Catastrophic failures: `2`, patients `73` and `254`.
- Mean Twin / persistence RVE: `0.352656 / 0.387454`.
- Mean Twin / persistence HD95: `7.838010 / 8.465184 mm`.
- Better/equal/worse counts: `3/6/7`.

The positive-mean-delta and zero-catastrophic-failure criteria failed; the other
three criteria passed. JSON SHA-256:
`f565a0713de52666b3c5a7624486b8bfa32280cb45b69fd3816c809d89aa885a`.
JSON/CSV identity, source/config hashes, paired summaries and all 16
freeze-before-reveal log entries were verified. The sealed originals and
generated MD are preserved at the standard result location in the user's
`D:/Projects/gbm-digital-twin` checkout.

[Result](STAGE10_VALIDATION_RESULT.md) and
[failure analysis](STAGE10_RESERVE_FAILURE_ANALYSIS.md) record the negative
result without a new candidate search. The remaining 32 reserve patients and
untouched holdout remain closed. Frozen protocols/configs have not changed.

The acquisition, preparation and real frozen-validation work is complete.
Final checkpoint: push the result/status documentation, verify latest GitHub
Actions, and fast-forward the clean original checkout.
