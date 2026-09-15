Digital Twin — Healthcare Research

Полный handoff / ТЗ для нового чата

Дата handoff: 2026-09-15

0. Как использовать этот документ в новом чате

Это основной handoff-документ по проекту gbm-digital-twin.

В новом чате:

Подключить GitHub-репозиторий проекта или открыть чат внутри Project, где репозиторий доступен.

Перед любыми изменениями попросить ассистента:

прочитать этот документ;

посмотреть дерево репозитория;

посмотреть git status;

определить текущую ветку;

прочитать реальные версии файлов, а не продолжать работу по старым предположениям из истории.

Только после этого продолжать разработку.

Ключевое правило: состояние Git-репозитория является источником истины. Этот handoff описывает архитектуру, научные ограничения, достигнутые результаты и контекст, но любые точные сигнатуры и актуальные содержимое файлов нужно сверять с репозиторием.

1. Стиль совместной работы

Пользователь предпочитает:

русский язык;

конкретные решения без лишней теории;

при изменении файлов — ПОЛНЫЕ листинги файлов целиком;

никаких фрагментов вида:

«замени вот эти 10 строк»;

«добавь после такой строки»;

«поправь только функцию»;

если файл меняется существенно — всегда давать новый полный файл;

PowerShell-команды для Windows;

небольшие, понятные git-коммиты;

Conventional Commits;

не использовать git add .;

явно перечислять добавляемые в индекс файлы;

не заявлять, что тесты зелёные, если пользователь сам не показал успешный прогон;

не строить декоративный UI вокруг несуществующей функциональности;

сначала backend/workflow/test, потом UI;

если раздел реально не работает — он не должен выглядеть работающим.

Пользователь особенно недоволен текущим состоянием UI, которое описал как:

«велосипед в кузове машины: выглядит круто, но почти ничего не работает»

Это важное UX-ограничение для дальнейшей разработки.

2. Главная цель проекта

Проект: Digital Twin — Healthcare Research.

Основной MVP:

patient-specific digital twin glioblastoma по longitudinal MRI.

Главная научная идея:

наблюдаем опухоль на t0;

персонализируем параметры модели на t0 → t1;

ассимилируем наблюдение t1;

прогнозируем t1 → t2;

сравниваем прогноз с t2;

оцениваем качество на когорте;

позже добавляем treatment-aware, anatomy-aware и uncertainty-aware компоненты.

Development dataset:

CFB-GBM — основной development dataset;

Burdenko — позже, как external validation / treatment-aware этап.

3. Неподвижный научный протокол

3.1. Главный anti-leakage принцип

Калибровка patient-specific параметров выполняется только по t0 → t1.

t2 является held-out future observation.

Категорически нельзя использовать t2 для выбора:

D;

rho;

observation threshold;

soft temperature;

latent width;

alpha;

alpha/beta;

treatment model;

cohort/model choices;

параметров ассимиляции;

hyperparameters;

регистрационных решений, если они специально подбираются под прогноз качества t2.

t2 используется только для финальной оценки предсказания.

4. Базовая математическая модель

Основная PDE:

\nabla \cdot (D \nabla c)
+
\rho c(1-c)
]

Где:

c(x,t) — latent tumor state;

D — diffusion coefficient, mm²/day;

rho — proliferation rate, 1/day.

Начальные предположения:

isotropic homogeneous D;

no-flux boundary condition;

brain-constrained domain;

начальное состояние строится по наблюдаемому GTV.

Единицы:

spacing: mm;

D: mm²/day;

rho: 1/day;

dt: days.

5. V1 / V2 scientific history

5.1. V1

V1 использовал более простую treatment модель.

Untreated mini cohort:

mean twin Dice ≈ 0.646;

persistence ≈ 0.658;

V1 не превзошёл persistence baseline.

Multiplicative RT с alpha=0.1 чрезмерно подавлял MRI-visible tumor state.

Global V1 alpha sweep по t0→t1 выбрал:

alpha = 0.01 /Gy.

После этого был выполнен один held-out t2 evaluation:

twin mean Dice ≈ 0.5942;

persistence ≈ 0.6320;

delta ≈ -0.0378;

2 wins / 4 ties / 2 losses.

V1 заморожен.

6. V2 / PIRT

V2 использует PDE-style treatment loss.

LQ survival:

[
S = \exp(-\alpha d - \beta d^2)
]

Treatment loss:

[
R = (1-S)c(1-c)
]

Fraction update:

[
c \leftarrow c - (1-S)c(1-c)
]

с clip в [0,1].

Важное свойство:

c=0 и c=1 остаются fixed points treatment transform.

V2 latent state строится из GTV через signed distance / sigmoid.

Фиксированные значения V2:

alpha = 0.01 /Gy
alpha/beta = 10 Gy
latent transition width = 4.0 mm
observation threshold = 0.5
soft calibration temperature = 0.05

Эти параметры нельзя дальше подбирать на t2.

Global effective alpha V2 = 0.01/Gy был выбран только на t0→t1.

7. Treatment assumptions

CFB-GBM treatment metadata:

у большинства calibration patients есть RT exposure;

точные даты фракций отсутствуют;

используется weekday-like reconstructed schedule;

RT spatially homogeneous;

RTDOSE maps пока не используются;

chemo metadata надёжно не идентифицированы.

Нельзя писать или подразумевать:

RT — единственное биологическое лечение.

Также нельзя слепо добавлять PostRadiotherapyEffect.

Ранее диагностика показала, что RT model уже может чрезмерно подавлять MRI-visible state; дополнительный post-RT kill ухудшал поведение.

8. Calibration status

Используется soft objective для калибровки, чтобы избежать hard-threshold plateaus.

Финальная held-out оценка t2 остаётся hard Dice.

V2 alpha robustness на t0→t1:

alpha   mean_loss mean_softDice mean_hardDice mean_vol_error mean_maxc
.005    .4701     .6735         .7007         .2434         .9176
.010    .4291     .6634         .6805         .1833         .9044
.015    .4822     .6470         .6636         .2714         .9189

Поэтому V2 alpha заморожен на:

0.01 /Gy

Некоторые пациенты упирались в верхнюю границу diffusion grid:

patient 65: D=.060;

patient 251: D=.060;

patient 108: D=.045.

Перед окончательным held-out V2 t2 evaluation нужно:

сделать boundary-aware refinement D/rho;

убедиться, что optima bracketed;

после этого заморозить V2 настройки;

выполнить только один финальный t2 evaluation.

9. Текущая архитектура репозитория

Ожидаемая структура примерно следующая, но новый чат обязан сверить её с реальным Git:

src/gbm_twin/
├── anatomy/
├── api/
├── calibration/
├── data/
├── evaluation/
├── models/
├── preprocessing/
├── visualization/
└── workflows/

frontend/
├── src/
└── ...

scripts/
tests/
data/
results/

Известные важные модули:

src/gbm_twin/models/
├── reaction_diffusion.py
├── solver.py
├── latent_state.py
├── pirt.py
├── pirt_solver.py
├── radiobiology.py
├── rt_schedule.py
└── treatment.py

src/gbm_twin/calibration/
├── cache.py
├── grid_search.py
└── refinement.py

src/gbm_twin/data/
├── cfb_metadata.py
├── cfb_treatment.py
├── models.py
├── nifti.py
└── patient_loader.py

src/gbm_twin/evaluation/
├── metrics.py
├── soft_metrics.py
├── baselines.py
├── cohort.py
├── treatment_aware.py
└── ...

src/gbm_twin/workflows/
├── patients.py
├── patient_catalog.py
├── calibration.py
├── viewer.py
├── scene3d.py
└── ...

src/gbm_twin/api/
├── app.py
├── config.py
├── routes/
└── schemas/

Новый чат должен получить фактический tree/список файлов из Git перед изменениями.

10. Data ingestion и preprocessing

Основной workflow подготовки пациента находится в workflows/patients.py.

Известно:

DEFAULT_TARGET_SPACING = (2.0, 2.0, 2.0)

Prepared timepoint содержит:

patient id;

timepoint name;

days from baseline;

T1Gd;

GTV;

brain mask.

Научный solver сейчас работает на 2 mm grid.

Очень важный архитектурный принцип:

visualization resolution и solver resolution не должны быть жёстко связаны.

2 mm grid подходит для PDE MVP, но недостаточен для высокодетального медицинского viewer.

11. Solver / PDE implementation

reaction_diffusion.py содержит:

ReactionDiffusionParameters;

computational domain;

initial condition;

brain-constrained evolution.

solver.py содержит:

masked finite-difference Laplacian;

crop / restore;

treatment events;

FractionatedRT;

PIRT;

splitting timesteps around treatment events.

Ранее был замечен странный участок, где локальная переменная domain могла сбрасываться в None после построения result. Это нельзя случайно рефакторить в ходе unrelated задач без тестов.

12. Cache / calibration

Calibration cache имеет собственную signature/version.

PIRT signature должна учитывать:

alpha;

alpha/beta;

treatment model.

.cache/ нельзя коммитить.

Grid search поддерживает:

hard objective;

soft objective;

multiprocessing;

cache.

Известная историческая проблема:

tests/calibration/test_refinement.py мог падать из-за exact float list equality:

0.009999... != 0.01

Новый чат должен проверить актуальное состояние тестов, а не считать эту проблему существующей автоматически.

13. API

Архитектура:

React + TypeScript + Vite
            ↓ HTTP
FastAPI
            ↓
gbm_twin.workflows
            ↓
domain/model/data code

Рабочие известные backend vertical slices:

health;

patient catalog;

patient details;

MRI viewer;

3D viewer;

anatomy endpoint infrastructure.

Исторически:

GET /api/health
GET /api/patients
GET /api/patients/{patient_id}

Viewer endpoints существовали примерно как:

GET /api/patients/{patient_id}/viewer/{timepoint}
GET /api/patients/{patient_id}/viewer/{timepoint}/slice
GET /api/patients/{patient_id}/viewer/{timepoint}/scene3d

Anatomy endpoint:

GET /api/patients/{patient_id}/anatomy/{timepoint_name}

Важно: ранее frontend ошибочно использовал /risk suffix, затем это было исправлено.

14. Frontend / UX

Frontend:

React;

TypeScript;

Vite;

lucide-react;

vtk.js.

Текущий дизайн пользователю визуально нравится:

light clinical/research shell;

neutral surfaces;

teal accent;

dark MRI viewport;

sidebar;

patient selector;

timeline;

viewer.

Но функциональная проблема серьёзная:

много sidebar/nav sections выглядят активными;

многие кнопки/карточки фактически ничего не делают;

много статических плашек написаны так, будто представляют real system state.

Это нужно исправить как приоритетную продуктовую задачу.

UX rule

Primary navigation должен содержать только реально функционирующие разделы.

Пока реально проверены в первую очередь:

Patients
Imaging / Viewer

Anatomy появляется только после устойчивого anatomy pipeline.

Не должны отображаться как рабочие до реализации:

Digital Twin
Runs
Tools
Research

Нельзя показывать fake-state вроде:

Simulation Ready
Research Pipeline Active
Digital Twin Running

если backend действительно не предоставляет такое состояние.

15. MRI viewer

Реальный 2D MRI viewer уже работал.

Функции:

real T1Gd;

GTV overlay;

t0/t1/t2;

axial/coronal/sagittal;

slice slider;

spacing;

GTV volume;

server-side PNG rendering.

Известный viewer workflow:

workflows/viewer.py

Текущая orientation логика исторически была voxel-plane based, а не полноценная validated RAS/LPS canonical orientation.

Нельзя произвольно подписывать:

L/R/A/P

пока affine orientation не валидирована.

16. 3D viewer

3D viewer на vtk.js уже работал.

Содержал:

brain surface;

GTV surface;

latent state surfaces;

rotate / zoom / pan;

layer toggles.

Brain surface на 2 mm binary mask выглядел недостаточно медицински детально.

Это не следует пытаться исправить бесконечным smoothing.

Правильная долгосрочная архитектура:

PDE остаётся на 2 mm;

viewer может использовать native/max available MRI resolution;

3D brain surface — secondary aid;

основные медицинские данные — MRI planes + segmentation + prediction overlay;

позже возможно полноценное volume rendering.

17. Anatomy / functional risk: зачем это делалось

Пользователь предложил важную будущую функцию:

если опухоль находится рядом с областями мозга, связанными с речью, моторикой и т.д., показывать предупреждения.

Правильная формулировка должна быть консервативной.

Нельзя:

Tumor affects speech center.

Можно:

Observed GTV overlaps an atlas-defined left inferior frontal language-associated region.

Или:

Predicted tumor is within 5 mm of an atlas-defined language-associated region.

Это population atlas research interpretation, а не patient-specific functional mapping.

Для surgical/clinical-level interpretation могут потребоваться:

fMRI;

DTI / tractography;

intraoperative mapping;

neuropsychological assessment;

другие modality-specific данные.

Система не является surgical guidance.

18. Anatomy pipeline — что было сделано

Был построен experimental anatomy subsystem.

Известные файлы:

src/gbm_twin/anatomy/
├── atlas.py
├── models.py
├── risk.py
├── bootstrap.py
├── registration.py
├── registration_mask.py
├── registration_review.py
├── qc.py
└── source_qc.py

Могут существовать не все или иметь другие версии — обязательно проверить Git.

Atlas bootstrap использовал:

Harvard-Oxford cortical atlas;

Harvard-Oxford subcortical atlas;

TemplateFlow MNI152NLin6Asym;

T1 template;

brain mask;

merged labels;

manifest.

Generated layout:

data/anatomy/atlas/
├── manifest.json
├── template_t1.nii.gz
├── template_brain_mask.nii.gz
├── template_labels.nii.gz
└── patients/
    └── <patient>/
        └── <timepoint>/
            └── ...

Большие generated NIfTI нельзя коммитить.

19. Anatomy source QC — важный результат

Для patient 108, timepoint t1 был сделан source-QC.

Atlas source QC

Результат визуально хороший:

MNI T1;

MNI brain mask;

Harvard-Oxford label support

в целом согласованы.

Вывод:

bootstrap / atlas source выглядит корректно.

Patient source QC

Patient T1 и brain mask в целом согласованы.

Был замечен небольшой disconnected component на низком axial slice.

Вывод:

patient source в целом пригоден, но registration-specific mask должен удалять disconnected components.

20. Anatomy registration — текущая проблема

Изначально SimpleITK affine registration давал:

Brain Dice ≈ 0.8116
Labels inside brain ≈ 0.7848
Quality: warn

Визуально registration была явно плохой:

inferior brain mismatch;

anterior/inferior spill;

local anatomical misalignment;

global Dice выглядел лучше, чем реальная локальная anatomical quality.

После registration-only mask + B-spline:

Selected stage: affine+bspline
Brain Dice: 0.8710
Labels inside brain: 0.8808
Automatic QC: pass

Но визуальный QC всё равно показал заметно неправильную анатомию.

Ключевой вывод:

overlap metrics alone are insufficient.

Нельзя принимать registration только по Dice.

21. Решение: остановить anatomy over-engineering

На последнем этапе обсуждался переход на ANTsPy/SyN, включая lesion-excluded metric mask.

Однако пользователь справедливо отметил:

мы уходим в дебри.

Поэтому новый чат не должен автоматически продолжать ANTs/SyN implementation.

Сначала нужно сделать архитектурный reassessment всего проекта по Git.

Рекомендуемое решение после открытия репозитория:

проверить реальный объём и качество anatomy-кода;

оценить, нужна ли anatomy функция для текущего MVP вообще;

не позволять anatomy feature задерживать основную Digital Twin задачу;

при необходимости заморозить anatomy как experimental branch/module;

вернуться к core digital twin milestones.

В частности:

patient-specific prediction t1→t2 важнее anatomical warning system для текущего MVP.

22. Что сейчас важнее anatomy

Следующий стратегический приоритет проекта:

A. Репозиторий и baseline

GitHub — источник истины;

clean branch;

test baseline;

lint baseline;

frontend build;

inventory реально работающих endpoints/components.

B. Functional UI cleanup

Сделать интерфейс честным:

Patients
Imaging

и только подтверждённые функции.

Убрать fake sections.

C. V2 calibration finalization

Проверить:

D/rho boundaries;

refinement;

caching;

no t2 leakage.

D. t1 assimilation

Строить latent state из observed t1 с fixed width 4 mm.

E. held-out prediction

Запустить:

t1 state
+ calibrated D/rho
+ frozen treatment model
        ↓
predict to t2

F. baselines

Минимум:

persistence;

simple volume/growth baseline при наличии;

twin.

G. cohort evaluation

Метрики:

Dice;

volume error;

spatial metrics;

wins/ties/losses;

confidence/uncertainty позже.

H. PatientTwin API

Только после science workflow.

I. UI Digital Twin tab

Только после working PatientTwin API.

J. Anatomy

Вернуться после core MVP либо оставить как experimental optional module.

23. V2 held-out evaluation protocol

Перед финальным t2:

все hyperparameters фиксируются;

никаких изменений по результатам t2;

calibration только t0→t1;

t1 assimilation только по t1;

один prediction t1→t2;

один evaluation;

результаты сохраняются и не используются для tuning этой версии.

Если после evaluation модель плохая:

V2 фиксируется как результат эксперимента;

следующий дизайн становится V3;

V2 нельзя ретроспективно «докрутить» по t2.

24. Git / reproducibility rules

Не коммитить:

data/
results/
.cache/
*.nii
*.nii.gz
*.tfm
registration QC images
patient-specific generated artifacts
model checkpoints

Исключение:

небольшие synthetic fixtures, специально созданные для tests.

Коммитить:

src;

tests;

scripts;

frontend/src;

configs;

YAML experiment configs;

docs;

dependency manifests;

small test fixtures.

Notebooks:

только exploration;

stable logic должна жить в src.

25. Environment

Известная локальная среда:

Windows
Python 3.11.9
.venv

Install:

python -m pip install -e ".[dev]"

Основные переменные окружения:

$env:GBM_TWIN_CFB_ROOT = "D:\Datasets\CFB-GBM"

$env:GBM_TWIN_CFB_PATIENTS_ROOT = `
  "D:\Datasets\CFB-GBM\patients"

$env:GBM_TWIN_CFB_METADATA_ROOT = `
  "D:\Datasets\CFB-GBM"

$env:GBM_TWIN_ATLAS_ROOT = `
  "D:\Projects\gbm-digital-twin\data\anatomy\atlas"

Реальные dataset paths могут отличаться.

26. Запуск backend / frontend

Backend:

cd D:\Projects\gbm-digital-twin

.\.venv\Scripts\Activate.ps1

uvicorn gbm_twin.api.app:app --reload

Frontend:

cd D:\Projects\gbm-digital-twin\frontend

npm install

npm run dev

Build:

npm run build

27. Testing philosophy

После изменения subsystem:

targeted tests;

ruff;

frontend build, если затронут frontend;

затем full suite.

Не скрывать dependency warnings, но различать:

blocking failure;

nonblocking deprecation warning.

Исторически встречались Starlette/httpx/anyio deprecation warnings в TestClient.

28. Git workflow

Использовать небольшие feature branches:

feat/ui-functional-shell
feat/v2-boundary-refinement
feat/patient-twin-api
feat/anatomy-experimental

Conventional Commits:

feat(viewer): add ...
fix(api): handle ...
refactor(calibration): ...
test(anatomy): ...
docs(project): ...

Не использовать:

git add .

Вместо этого:

git add `
  src/... `
  tests/... `
  frontend/src/...

29. Что новый чат должен сделать первым

Первый рабочий запрос к новому ассистенту должен быть:

Прочитай PROJECT_HANDOFF_RU.md. Затем изучи реальный GitHub-репозиторий целиком на уровне структуры: дерево директорий, git status/branch, pyproject, frontend package.json, API routes, workflows, tests и текущий anatomy-код. Не меняй ничего, пока не сформируешь краткий verified baseline: что реально работает, что является декоративным UI, что находится в experimental состоянии, какие тесты и builds сейчас проходят. Старые предположения из handoff не считать точными, если Git им противоречит.

После baseline ассистент должен предложить не огромный roadmap, а ближайший vertical slice.

Рекомендуемый первый vertical slice после repo audit:

убрать нерабочие UI-разделы и оставить честный functional shell без изменения science code.

После этого:

вернуться к V2 D/rho boundary refinement и preparation к held-out prediction.

30. Критические запреты для нового чата

Нельзя:

использовать t2 для tuning;

менять frozen V2 alpha;

подавать experimental atlas warnings как clinical facts;

считать Dice registration достаточным medical QC;

продолжать anatomy deep dive, не оценив влияние на MVP;

строить fake UI state;

рефакторить solver одновременно с unrelated feature;

коммитить patient data;

писать fragmented patches вместо полных файлов;

утверждать, что tests green, без реального прогона;

менять scientific preprocessing ради viewer convenience;

автоматически переносить визуальные transformations в scientific pipeline.

31. Что считается успешным MVP

Минимальный научно честный MVP:

Patient
  ↓
longitudinal MRI / GTV
  ↓
prepare t0, t1, t2
  ↓
calibrate D/rho on t0→t1
  ↓
assimilate observed t1
  ↓
predict t1→t2
  ↓
compare with held-out t2
  ↓
compare against baselines
  ↓
cohort metrics
  ↓
PatientTwin API
  ↓
functional research UI

Anatomical atlas warnings — полезное расширение, но не blocker core MVP.

32. Итоговое состояние на момент handoff

Работает или было подтверждено ранее:

CFB patient preparation;

longitudinal workflow;

2 mm resampling;

PDE solver;

treatment-aware solver;

PIRT;

soft calibration;

calibration cache;

patient catalog API;

real MRI 2D viewer;

3D viewer;

frontend shell;

V2 alpha selection на t0→t1.

Требует verify по Git:

текущие tests;

current full test count;

current frontend build;

exact API routes;

anatomy experimental files;

current git changes;

current branch;

dependency state.

Experimental / not accepted:

atlas registration;

functional warnings;

anatomy clinical interpretation.

Не завершено:

final D/rho boundary refinement;

t1 assimilation production workflow;

frozen V2 held-out prediction;

cohort V2 evaluation;

PatientTwin API;

working Digital Twin UI;

runs/workbench UI.

33. Главная мысль для продолжения

Не нужно превращать проект в коллекцию сложных технологий.

Приоритет:

scientific correctness → reproducibility → working vertical slices → honest UI → advanced features

а не:

красивый dashboard → много вкладок → много experimental subsystems.

Следующий чат должен сначала увидеть реальный репозиторий и привести development roadmap в соответствие с тем, что уже действительно работает.