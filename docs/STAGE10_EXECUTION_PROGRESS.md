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
Actual
144-file acquisition and hardlink preparation have now been started. Reserve
evaluation remains pending until preparation and full code checks complete.
