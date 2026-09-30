# GBM Digital Twin

Исследовательская платформа для patient-specific моделирования глиобластомы по longitudinal MRI.

> **Research only.** Проект не является клинической системой поддержки принятия решений. Все прогнозы, atlas-defined функциональные области и quality gates предназначены для исследовательской оценки.

## Текущее состояние

Актуальная линия разработки: `feat/twin-protocol`.

На 30 сентября 2026 года проект включает полноценный longitudinal pipeline:

```text
t0 MRI/GTV
    ↓
patient-specific calibration D, rho
    ↓
t1 observation assimilation
    ↓
frozen t1 → t2 forecast
    ↓
sealed reveal/evaluation against t2
    ↓
baselines + cohort metrics + failure analysis
```

Работают:

- CFB-GBM data preparation и longitudinal patient workflow;
- reaction-diffusion solver с brain-constrained domain;
- treatment-aware / radiotherapy model families;
- patient-specific calibration и diagnostics;
- freeze/reveal anti-leakage protocol;
- cohort evaluation, baselines и error analysis;
- FastAPI PatientTwin API;
- 2D/3D MRI/twin viewer;
- patient-level comparison и cohort workspace;
- technical QC;
- pre-t2 forecast reliability gate;
- atlas-based current/predicted anatomical impact;
- Stage 8 / Stage 9 model-selection workflows;
- published TumorTwin reference benchmark;
- Reference Fidelity v2;
- Stage 10 decoupled-damage diagnostic implementation.

Python и frontend проверяются GitHub Actions. После последнего Stage 10 integration patch полный Python suite содержит **438 passing tests**; frontend проходит ESLint и production build.

## Научный статус

### Stage 9 v2

Текущий лучший завершённый собственный development candidate:

`stage9-delayed-transfer-1-half-life-120d-visibility-1`

На 24 уже раскрытых development patients:

- mean Dice: `0.681404`;
- mean delta vs persistence: `-0.011792`;
- mean HD95: `11.2522 mm`;
- mean relative volume error: `0.950507`;
- catastrophic failures: `2`.

Stage 9 улучшил exact Stage 8 control (`0.667942` mean Dice), особенно regression subgroup, но в среднем всё ещё не превосходит persistence.

### Reference Fidelity v2

Reference Fidelity v2 завершён на тех же exposed development data.

- TumorTwin LM + tumor-centric ROI, 24 patients:
  mean Dice `0.636752`, catastrophic failures `5`;
- paired ROI-GTV, 9 ADC-eligible patients:
  mean Dice `0.575452`, catastrophic failures `3`;
- paired TumorTwin-style ADC-derived enhancing cellularity:
  mean Dice `0.393779`, catastrophic failures `5`.

ROI cropping не улучшил reference result, а tested ADC branch не прошёл predefined advancement rule.

Подробности: [docs/REFERENCE_FIDELITY_V2_RESULT.md](docs/REFERENCE_FIDELITY_V2_RESULT.md).

### Stage 10

По заранее заданному decision rule следующим experiment является Stage 10: разделение MRI-visible damaged burden и MRI-invisible inert occupancy.

Модель:

```text
v — viable/proliferating density
d — MRI-visible damaged burden
q — MRI-invisible inert occupancy
m — persistent proliferation modifier

visible = clip(v + d, 0, 1)
occupancy = clip(v + d + q, 0, 1)
```

Stage 10:

- не добавляет новый patient-specific fitted parameter;
- сохраняет frozen D/rho;
- сохраняет frozen radiobiology;
- использует exact Stage 9 v2 как control;
- проверяет только predefined `14/30/60 d` visible-damage half-lives;
- требует уменьшения catastrophic failures и улучшения regression subgroup;
- не открывает reserve или untouched holdout.

Код и checkpoint готовы. Реальный 24-patient run требует локальные medical data/artifacts и поэтому не выполняется в GitHub Actions.

Запуск на машине с подготовленными CFB данными:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\twin\run_stage10_checkpoint.ps1
```

Ожидаемые артефакты:

```text
results/cohort/stage10-decoupled-selection-v1/
    stage10_decoupled_selection.json
    stage10_decoupled_selection.csv
    stage10_decoupled_selection.sha256
```

Подробный protocol: [docs/STAGE10_DECOUPLED_DAMAGE_PROTOCOL.md](docs/STAGE10_DECOUPLED_DAMAGE_PROTOCOL.md).

## Anatomical / functional-region workspace

Проект умеет сравнивать:

```text
CURRENT
observed t1 GTV + t1 latent state
              ↓
      accepted t1 atlas

FORECAST
frozen prediction field/mask
              ↓
      same accepted t1 atlas
```

Таким образом predicted anatomical impact **не использует observed t2 anatomy**.

В интерфейсе вкладка **«Функциональные области»** показывает atlas-defined regions для текущего состояния и frozen forecast, включая новые прогнозируемые пересечения/близость.

Категории включают:

- речь и язык;
- motor-associated cortex;
- somatosensory regions;
- visual regions;
- memory-associated regions;
- critical subcortical structures.

Это population-atlas estimate, а не индивидуальная функциональная карта пациента. Интерфейс намеренно не делает утверждений вида «пациент потеряет речь».

### Registration safety gate

Функциональный анализ включается только для t1 atlas registration, которая прошла:

```text
atlas registration candidate
        ↓
automatic QC
        ↓
manual review
   accepted / rejected
        ↓
canonical labels.nii.gz
```

Accepted registration дополнительно проверяется по SHA-256:

- canonical `labels.nii.gz` должен совпадать с reviewed candidate;
- `registration.json` должен совпадать с reviewed provenance;
- automatic QC `fail` нельзя принять.

Без verified accepted t1 registration прогноз функциональных областей остаётся недоступным.

## Pre-t2 forecast quality gate

В Digital Twin → «Обзор» показывается техническая оценка надёжности, вычисляемая **без observed t2**.

Используются только:

- calibration identifiability;
- D/rho boundary diagnostics;
- frozen prediction geometry;
- t1 brain mask;
- frozen Git/protocol provenance.

Статусы:

- `nominal` — известных pre-t2 технических флагов нет;
- `caution` — есть технические оговорки;
- `limited` — обнаружен существенный reliability flag.

Это **не calibrated probability** правильности прогноза и не клиническая confidence score.

## Anti-leakage rules

Главный контракт проекта:

- patient-specific calibration выполняется только на `t0 → t1`;
- t2 не используется для выбора D/rho;
- t2 не используется для подбора observation threshold;
- t2 не используется для выбора treatment-response parameters;
- model-family diagnostics после раскрытия development t2 остаются только development evidence;
- reserve patients нельзя использовать для повторного tuning;
- untouched holdout открывается только после freeze структуры;
- Burdenko предназначен для последующей external validation.

Большие medical data и generated results в Git не коммитятся.

## Установка

Требуется Python 3.11+.

```powershell
cd D:\Projects\gbm-digital-twin

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Для frontend:

```powershell
cd frontend
npm ci
```

## Dataset paths

Типичный локальный CFB setup:

```powershell
$env:GBM_TWIN_CFB_ROOT = "D:\Datasets\CFB-GBM"
$env:GBM_TWIN_CFB_PATIENTS_ROOT = "D:\Datasets\CFB-GBM\patients"
$env:GBM_TWIN_CFB_METADATA_ROOT = "D:\Datasets\CFB-GBM"
```

Atlas является optional capability:

```powershell
$env:GBM_TWIN_ATLAS_ROOT = "D:\Projects\gbm-digital-twin\data\anatomy\atlas"
```

Пути могут отличаться локально.

## Запуск приложения

Backend:

```powershell
cd D:\Projects\gbm-digital-twin
.\.venv\Scripts\Activate.ps1

uvicorn gbm_twin.api.app:app --reload
```

Frontend:

```powershell
cd D:\Projects\gbm-digital-twin\frontend
npm run dev
```

## Проверки

Python:

```powershell
python -m ruff check .
python -m pytest -q
```

Frontend:

```powershell
cd frontend
npm run lint
npm run build
```

CI выполняет Python и frontend jobs независимо.

## Важные директории

```text
src/gbm_twin/
    anatomy/        atlas, registration, QC, anatomical risk
    api/            FastAPI routes and schemas
    calibration/    D/rho calibration and diagnostics
    data/           dataset contracts and loading
    evaluation/     metrics, baselines, error analysis
    models/         PDE and treatment/state models
    reference/      TumorTwin adapters
    workflows/      reproducible patient/cohort protocols

frontend/src/
    api/
    components/
        workbench/

configs/
    datasets/
    experiments/
    research/

scripts/
    anatomy/
    reference/
    twin/

tests/
    anatomy/
    api/
    calibration/
    evaluation/
    models/
    reference/
    workflows/
```

## Reproducibility

Generated scientific artifacts carry:

- Git commit provenance;
- dirty-tree status;
- config SHA-256;
- input SHA-256;
- protocol/model version;
- artifact SHA-256.

Sealed evaluation verifies source freeze manifests and per-patient prediction manifests before loading them.

`data/`, `results/`, medical images (`*.nii*`, DICOM), transforms and local caches intentionally находятся вне Git.

## Основные документы

- [PROJECT_DIRECTION_RU.md](docs/PROJECT_DIRECTION_RU.md) — текущий scientific direction;
- [STAGE9_V2_RESULT.md](docs/STAGE9_V2_RESULT.md) — завершённый Stage 9 result;
- [REFERENCE_BENCHMARK_V1_RESULT.md](docs/REFERENCE_BENCHMARK_V1_RESULT.md) — published-reference checkpoint;
- [REFERENCE_FIDELITY_V2.md](docs/REFERENCE_FIDELITY_V2.md) — predefined fidelity protocol;
- [REFERENCE_FIDELITY_V2_RESULT.md](docs/REFERENCE_FIDELITY_V2_RESULT.md) — sealed fidelity result;
- [STAGE10_DECOUPLED_DAMAGE_PROTOCOL.md](docs/STAGE10_DECOUPLED_DAMAGE_PROTOCOL.md) — текущий next experiment;
- [MVP_PROTOCOL_V2.md](docs/MVP_PROTOCOL_V2.md) — исторический frozen V2 protocol.

## Ближайшая scientific развилка

После реального Stage 10 run:

- если decoupled candidate уменьшает catastrophic failures, улучшает regression subgroup и проходит guardrails — структура фиксируется до reserve validation;
- если Stage 10 не проходит — дальнейшее добавление RT compartments прекращается, а следующий development cycle переносится на MRI observation model / defensible multimodal representation и uncertainty.

Reserve cohort и untouched holdout до этого не расходуются.
