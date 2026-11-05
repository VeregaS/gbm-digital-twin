# Техническое задание: лаборатория in silico экспериментов GBM Digital Twin

Версия: 1.0. Дата: 17.10.2026.
Репозиторий: VeregaS/gbm-digital-twin, ветка `feat/twin-protocol`.
Проверенная исходная версия кода: `2a85f376b5009d0338d34b3ac41160c439b8bbef`.

Документ предназначен для реализации следующими coding agents.
Текущее поручение — подготовить ТЗ; функции ниже являются требованиями, а не
заявлением об уже завершённой реализации. Состояние этапов вести в
[IN_SILICO_LAB_PROGRESS.md](../../IN_SILICO_LAB_PROGRESS.md).
При начале реализации проверить изменения после указанного commit и
скорректировать инвентаризацию, сохранив пользовательскую работу.

## 1. Цель и рабочая тема

**Разработка программно-алгоритмического средства для проведения воспроизводимых
вычислительных экспериментов по моделированию роста глиобластомы и анализу
сценариев терапии на базе исследовательского цифрового двойника.**

Создать в существующем приложении работающую исследовательскую лабораторию:
готовый виртуальный случай → сценарий → расчёт → пространственная и временная
визуализация → сравнение → чувствительность/виртуальная когорта → воспроизводимый
научный эксперимент.

Математическая основа — опубликованная модель и реализация TumorTwin.
Не разрабатывать новую биологическую модель с нуля. Собственный вклад:
организация экспериментов, проверка корректности, анализ устойчивости выводов,
эффективное проведение серий и программный инструмент для исследователя.

Продольные МРТ остаются источником подготовленного авторского случая и
дополнительным направлением персонализации. Пользователь лаборатории не обязан
загружать и обрабатывать новый клинический MRI-набор для каждого эксперимента.
Первый результат должен работать без установленного CFB-GBM и atlas registration.

## 2. Границы работ

Обязательный законченный объём:
- авторский синтетический HGG-случай, воспроизведённый в закреплённом движке;
- каталог моделей/случаев и редактор воспроизводимых сценариев;
- постоянное хранение запусков, очередь, прогресс, отмена и обработка сбоев;
- траектории роста, 2D/3D-поля во времени и сопоставление сценариев;
- локальная чувствительность и глобальный screening;
- генерация виртуальных когорт и парные серии экспериментов;
- исследование устойчивости результатов по заранее записанному протоколу;
- CLI/API/GUI, экспорт, документация, проверки и воспроизводимый запуск.

Расширенный этап с отдельными условиями: адаптивное распределение вычислительного
бюджета. Не объявлять его необходимым для первого рабочего сквозного сценария.

В первую версию не входят: собственная новая PDE, новая нейросеть, иммунные/
клеточные механизмы PhysiCell, автоматический клинический выбор лечения, прогноз
реальной выживаемости, новая CFB reserve validation, обязательная облачная
инфраструктура, многопользовательская SaaS-платформа. Публичное размещение
предусмотреть архитектурно; фактическое размещение — после выполнения условий
раздела 4.

## 3. Что уже реализовано и как переиспользовать

Инвентаризация проверена по исходникам, а не только по README.

| Подсистема | Существующая реализация | Решение для лаборатории |
|---|---|---|
| Backend | `src/gbm_twin/api/app.py`, `api/config.py`, маршруты и Pydantic schemas | Расширить существующий FastAPI, добавить независимый namespace лаборатории |
| Frontend | React/TypeScript/Vite, `frontend/src/App.tsx`, Sidebar/Topbar/WorkbenchContent | Сохранить оболочку, стили и русскоязычные компоненты; добавить режим лаборатории |
| Возможности сервера | `api/routes/capabilities.py` | Добавить lab capabilities независимо от CFB; сейчас runs/tools/research явно не реализованы |
| 2D-просмотр | `TriPlanarViewer.tsx`, `MedicalViewerPanel.tsx`, `workflows/viewer.py`, `twin_viewer.py` | Переиспользовать подходы и чистые функции; убрать зависимость нового просмотра от patient_id/evaluation |
| 3D | vtk.js, `ThreeDViewer.tsx`, `TwinThreeDViewer.tsx`, `workflows/scene3d.py`, `twin_scene3d.py` | Общие mesh-функции и геометрию адаптировать к case/run/frame; поддержать время |
| Сравнение и графики | `TwinCompareTab.tsx`, `TwinCohortChart.tsx`, cohort analysis | Переиспользовать представление; сценарии не подменять patient forecast/baseline |
| TumorTwin | `reference/tumortwin.py`, `scripts/reference/tumortwin_worker.py`, bootstrap и smoke test | Сохранить старый adapter для повторяемости CFB; добавить отдельный lab adapter полного авторского случая |
| Загрузка MRI | `data/nifti.py`, `preprocessing/resampling.py`, geometry checks | Переиспользовать с сохранением affine/единиц; не заставлять lab проходить CFB loader |
| Модели проекта | `models/`, V2/V3 и Stage 8–10 | Сохранить как существующую исследовательскую линию; не объявлять Stage 10 новым lab engine |
| Происхождение/кэш | `workflows/provenance.py`, `repository.py`, calibration cache | Выделить общие primitives; CFB-зависимые payload не переносить без адаптации |
| Долгие задачи | Anatomy preparation через BackgroundTasks и JSON status | Использовать опыт UI polling; это не готовая постоянная очередь model runs |
| Когорты и оценка | freeze/reveal, paired metrics, CSV/JSON/SHA | Переиспользовать правила воспроизводимости; lab studies имеют отдельные schemas/хранилища |
| Тесты/CI | pytest, Ruff, ESLint, production build, GitHub Actions | Сохранить и дополнить значимыми lab tests; историческая последняя проверка — 571 тест |

Критические ограничения существующего adapter:
1. `TumorTwinReferenceRequest` требует calibration/observed field и integer
   patient_id; это не контракт виртуального случая.
2. Worker возвращает конечный `prediction_density`, не полную траекторию.
3. Он работает на CPU, создаёт упрощённый patient-like объект, RT specification;
   полного авторского HGG workflow с CT в этом adapter нет.
4. Результаты переводятся через NumPy/detach, `require_grad=False`; таким
   способом нельзя автоматически получить корректный upstream autograd.
5. Геометрия mask image создаётся из diagonal spacing. Для авторского случая
   нужно сохранять исходный affine, а не терять начало координат/ориентацию.
6. `run_external_tumortwin` синхронен, его нельзя вызывать внутри долгого HTTP GET.

## 4. Движок, авторство и лицензии

Основной upstream:
https://github.com/OncologyModelingGroup/TumorTwin
Закреплённый commit:
`bedf90a6d47ba48cf5cdb25901967d84730061d1`.
Первый случай: `input_files/HGG_demo_001`.
Методика:
https://oncologymodelinggroup.github.io/TumorTwin/tutorials/HGG_Demo/
Градиенты:
https://oncologymodelinggroup.github.io/TumorTwin/tutorials/HGG_Gradients/
Публикация:
https://doi.org/10.1186/s12911-026-03520-2

Работать через адаптер и отдельное окружение, совместимое с pinned upstream.
Уже существующее reference-окружение проверить и переиспользовать, а не
переустанавливать молча. Базовая совместимая версия — Python 3.11; версии Torch,
NumPy, solver packages и источника пакета сохранить в runtime manifest.
Отдельное окружение не отменяет лицензионные обязательства.

Проверять фактическую версию установленного кода/источник пакета; один текстовый
marker с SHA недостаточен для научного подтверждения версии.

UT Austin Research License разрешает указанные исследовательские применения,
но ограничивает распространение, коммерческое использование и производные
продукты. До публикации engine/data в нашем репозитории или публичного сервиса
установить соответствующие права; оформить результат проверки в
`docs/TUMORTWIN_LICENSE_AND_DATA_USE.md` со ссылками на конкретные условия.
Лицензия статьи и лицензия кода/atlas/data — разные документы.
Не распространять сторонние исходники/данные по умолчанию.
Не писать авторам без прямого разрешения пользователя.
При неразрешённом публичном размещении продолжать допустимую локальную
исследовательскую работу; не останавливать всё ТЗ из-за hosting.

## 5. Научные границы и сохранение результатов

- Случай HGG автора синтетический. Маркировать его именно так; не представлять
  как доказанно персонализированный клинический GBM twin или молекулярный диагноз.
- Старые CFB workflows, V2/V3 artifacts и результаты Stage 8–10 не удалять.
  Frozen Stage 10 failed reserve validation; новый продукт не меняет этот verdict.
- 16 раскрытых reserve случаев не использовать для настройки новой методики;
  32 оставшихся reserve и 21 untouched holdout не открывать.
- Это отдельный synthetic-lab workflow. Он не требует запуска условного
  `OBSERVATION_MODEL_NEXT_CYCLE.md` и не отменяет его условий для patient studies.
- Не ослаблять QC, не заменять закрытые/неподходящие клинические случаи и не
  изменять frozen settings ради демонстрации.
- Не обещать клиническую эффективность или качество индивидуального прогноза
  по результатам синтетического эксперимента.
- Любую новую/исправленную динамику публиковать отдельной версией модели.
  Нельзя молча исправить уравнения Stage 10 и назвать это старым результатом.

## 6. Контракты данных

### 6.1. Engine и prepared case

`EngineDescriptor`: id/version, upstream commit, adapter/schema version, supported
parameters/treatments, solver capabilities, environment fingerprint, citation,
license/use status. Возможности интерфейса определяются этим descriptor.

`PreparedCase`: строковый case_id, version, kind=synthetic, источник и SHA файлов,
engine compatibility, MRI/маски/начальная плотность, shape/spacing/affine/единицы,
origin of parameters, временная шкала и авторская baseline-конфигурация.
Отделить известные generative parameters, стартовые guesses и fitted parameters.
Не создавать фиктивный CFB patient_id для `HGG_demo_001`.

Подготовка: explicit script → загрузка разрешённых файлов в отдельный local data
root → проверка hash/геометрии/конечности → immutable manifest → reference run.
Первый API GET не скачивает данные, не калибрует и не запускает симуляцию.
Нет файлов — capability с объяснением и способом подготовки.
Не перезаписывать пользовательские данные при несовпадении checksum.

В авторском reproduction режиме допустимы доступные synthetic visits; сохранить
точные cropping/initialization conventions и указать использование наблюдений.
Это не доказательство проспективного прогноза. В новых forecast experiments
future observations не участвуют в построении входного состояния/подборе
параметров; evaluation truth используется отдельно.

### 6.2. Scenario и план запуска

`Scenario`: immutable id/version, case reference, parent/baseline, engine,
параметры с единицами, RT/CT schedule, начальные условия, горизонт, output times,
solver/integration settings, precision/device, seed, analysis endpoints.
Редактирование завершённого сценария создаёт новую версию.

Установить явное соответствие upstream `k` и project `rho`, `d/D`, времени,
пространства, RT и CT dose units. Значения из авторского примера переносить
без неявного пересчёта. Не выдумывать поддерживаемые дозировки или параметры.
Все числа конечны, ограничения и сочетания валидируются перед постановкой
в очередь; dt/горизонт/число кадров/размер массива имеют явные лимиты.

RT и CT могут иметь событие в один день; не удалять такие события как дубликаты.
Семантику снимка до/после события и граничных времён зафиксировать и проверить
относительно upstream. Шаг интегрирования и шаг сохранения кадров различаются.

`RunPlan`: canonical scientific inputs, content hash, compute/disk budget,
requested outputs и frozen study reference. Display name/локальные пути не
меняют scientific identity. Численно значимые versions/device/precision
учитывать при повторном использовании результата.

### 6.3. Запуск и результаты

`Run`: UUID, plan hash, attempt, status, timestamps, progress phase, completed/
total work, worker identity, сообщения/ошибки, resource measurements,
artifact references, resume/retry lineage и `reused_from`, если был cache hit.
Повторный запрос одного run по idempotency key не создаёт дубликат задачи.
Явный rerun может создать новую попытку с тем же scientific plan.

`RunResult`: status и качество проверки, массивы/кадры с реальным временем,
полная density trajectory или declared сохранённое подмножество, geometry,
TCC/burden time series, модели лечения, summaries, provenance, SHA artifacts.
Частичные результаты не равны успешному полному результату.

Пример дерева (уточнить имена при реализации, смысл сохранить):
```text
results/lab/
  runs.sqlite3
  cases/<case_id>/<case_version>/manifest.json
  runs/<run_id>/
    plan.json
    environment.json
    progress.json
    events.jsonl
    metrics.csv
    frames/
    result.json
    artifacts.sha256
  studies/<study_id>/
    protocol.json
    cohort.csv
    cohort.sha256
    execution.jsonl
    results.csv
    analysis.json
    figures/
    README.md
```

Медицинские volumes/большие результаты и сторонние данные остаются git-ignored.
В Git хранить наш код, schemas, протоколы, документацию и допустимые небольшие
синтетические fixtures. JSON с NaN/Inf не записывается как валидный artifact.
Использовать атомарную публикацию manifest и проверку checksums при чтении.
Не доверять cache только по существованию `result.json`: сверять plan, версии,
полноту и hashes. Повреждённый результат требует явного восстановления.

## 7. Архитектура и выполнение

Расширять существующий проект. Предлагаемое расположение:
- `src/gbm_twin/lab/`: contracts/config, case registry, scenario validation,
  storage, jobs, engine interface, comparison, sensitivity, cohorts/studies;
- `src/gbm_twin/lab/engines/tumortwin.py`: adapter; внешний worker отдельно
  под `scripts/lab/`, внутри совместимого engine-окружения;
- `api/routes/lab.py`, `api/schemas/lab.py` и `frontend/src/api/lab.ts`;
- `frontend/src/components/lab/`: компоненты нового режима;
- `configs/lab/`, `scripts/lab/`, `tests/lab/` и API tests.

Названия можно уточнять под архитектуру, но не создавать второй параллельный
backend/frontend. Общие функции выделять из существующих модулей без изменения
поведения старых routes/artifacts.

Worker выполняется вне HTTP request и event loop. Для первой версии достаточно
SQLite + локальный bounded worker/subprocess, без обязательных Redis/Celery/K8s.
Начальная concurrency=1, затем настраиваемый лимит с учётом RAM/GPU/CPU threads.
Не создавать вложенные бесконтрольные process pools для cohort/sensitivity.

Статусы: `queued → running → succeeded | failed | cancelled | interrupted`;
отмена выполняющегося расчёта проходит через `cancel_requested`.
Частично завершённая серия сообщает число успешных/ошибочных/отменённых задач.
После restart прежний running не остаётся вечным spinner: помечается interrupted;
продолжение возможно только с проверенного checkpoint и той же конфигурацией.
Если двигатель не поддерживает точное продолжение, явно перезапустить попытку,
переиспользуя только завершённые независимые элементы серии.

Отмена прекращает принадлежащий запуску worker и его дочерние вычисления,
сохраняет диагностику, не влияет на чужие процессы. Timeout/OOM/неверный output
переводят задачу в конечное состояние с понятной причиной и возможностью retry.

Для больших 3D-полей сохранять ограниченное число кадров. UI запрашивает
нужный кадр/срез/mesh; не пересылать всю 4D-траекторию в каждом HTTP ответе.
Визуальное сглаживание не изменяет численные поля и научные метрики.

## 8. API

Новый namespace `/api/lab`, совместимый с существующим `/api`.
Минимальный контракт:
- `GET /engines`, `GET /cases`, `GET /cases/{case_id}`;
- `POST /scenarios`, `GET /scenarios/{scenario_id}`;
- `POST /runs` → 202 и run_id, `GET /runs`, `GET /runs/{run_id}`;
- `POST /runs/{run_id}/cancel`;
- `GET /runs/{run_id}/metrics`, `.../frames`, `.../slices`, `.../scene3d`;
- `GET /runs/{run_id}/export`;
- `POST /comparisons`, `GET /comparisons/{comparison_id}`;
- `POST /studies`, `GET /studies/{study_id}`,
  `POST /studies/{study_id}/run`, `.../cancel`, `.../results`, `.../export`.

Study kinds включают sensitivity/cohort/robustness; не плодить отдельные
несовместимые исполнители. OpenAPI/Pydantic и TypeScript types согласовать.
В `/api/capabilities` lab readiness отделить от dataset_ready и V2 seal.
Отсутствие Torch/авторских данных возвращает корректную capability/ошибку;
не включать ложный available с неработающей кнопкой.

## 9. Интерфейс исследователя

Первый пользовательский путь:
1. Открыть лабораторию без CFB и выбрать подготовленный HGG case.
2. Увидеть происхождение, synthetic label, исходное состояние и авторский режим.
3. Создать копию baseline, изменить поддерживаемые параметры/расписание.
4. Запустить, видеть очередь/этап/прогресс, отменить при необходимости.
5. Получить временную кривую, 2D/3D-картину и сравнение с baseline.
6. Сохранить/экспортировать эксперимент и запустить серию.

Основные представления: «Готовые модели», «Эксперименты», «Сравнение»,
«Чувствительность», «Виртуальные когорты», «Исследования».
CFB patient workspace сохранить отдельным доступным направлением.
Не переносить старый patient-specific badge на виртуальные случаи.

В текущем `App.tsx` при mount загружаются CFB patients; новый lab startup не
должен ждать эти запросы, требовать selectedPatientId или показывать CFB error
как ошибку всей лаборатории. Atlas assets не скачиваются ради открытия lab.

Параметры: понятные названия, единицы, источник/default, границы и reset.
Перед запуском показывать отличие от baseline, requested horizon, объём серии
и оценку стоимости по измеренному pilot; не выдавать выдуманный ETA.
Ошибки — на русском с полезным действием; stack traces оставлять в diagnostics.
SHA/schema/worker детали доступны в раскрываемой методике и экспорте.

Просмотр времени: слайдер и play по сохранённым кадрам, реальные даты/дни,
совпадающий физический FOV и цветовая шкала в парном сравнении.
Не имитировать новый PDE расчёт декоративной анимацией.
Для недостаточно подготовленной функции показывать честное недоступное
состояние, а не фиктивные графики или заранее придуманные результаты.

## 10. Анализ и научный эксперимент

### 10.1. Метрики и сценарии

Обязательные outputs: нормированная модельная density, TCC при согласованных
carrying-capacity/voxel units, изменение tumor burden и интеграл burden по времени.
Пороговый объём допустим как дополнительная метрика с явным fixed threshold.
TCC не называть измеренным клиническим объёмом. Пороговый time-to-progression
не называть реальной выживаемостью.

Сравнение проводить на одинаковом начальном случае, временной сетке outputs
и горизонте; при различии numerical settings показывать предупреждение и
отдельно исследовать сходимость. Сохранять матрицу изменённых параметров.
Первый набор: авторский baseline, поддерживаемый изменённый schedule и
диагностический контроль. Конкретные schedules зафиксировать до основной серии.
При выводах о сравнении схем задавать общие ресурсные ограничения; результат
«больше cytotoxic treatment → меньше опухолевой массы» недостаточен.
Клиническую токсичность не подменять одним tumor-only endpoint.

### 10.2. Чувствительность

V1: нормированные локальные конечные разности вокруг nominal с повтором при
меньшем perturbation step; обработать нулевой nominal и границы параметров.
Upstream autograd — дополнительная реализация, которую необходимо сверить с
конечными разностями; не проводить градиент через старый detached adapter.

Затем глобальный Morris screening с явными ranges, траекториями, seed,
числом evaluations и оценкой устойчивости рангов при повторных seeds.
Документировать, какие параметры непрерывны и могут изменяться независимо.
Не называть локальный derivative глобальной чувствительностью или
идентифицируемостью. Sobol/другой расширенный метод добавлять только с
согласованными предпосылками и compute budget; независимость параметров не
предполагать молча.

### 10.3. Виртуальные когорты и устойчивость

Когорта — explicit sampled parameter/case table с единицами, seed, источниками
распределений и SHA, сохранённая до запуска. Uniform/random и space-filling
sampling имеют зарегистрированные названия/настройки. Изменение ROI/state
выполняется явным генератором synthetic case с QC, исходным TCC и provenance;
нельзя молча подставить прежний GTV logistic profile вместо авторского ADC case.

Для всех сценариев использовать одинаковые virtual subjects (paired design).
Сбойные subjects не заменять новыми; сообщать полный знаменатель и coverage.
Частичные/cohort failures не исключать из сводки без зарегистрированного правила.
Один seed и одна анатомия не обосновывают клиническую репрезентативность.

Первый научный вопрос: насколько сохраняются выводы сравнения сценариев при
неопределённости параметров, начального состояния и численной точности?
Сопоставить nominal single-run и fixed-budget ensemble.
Outputs: распределение парных различий, частота смены ранга в заданной
синтетической популяции, устойчивость чувствительности, unresolved comparisons,
численная ошибка, wall time/RAM/evaluation count.

До основной серии создать `configs/lab/studies/robustness_v1.yaml` и
`docs/IN_SILICO_LAB_STUDY_PROTOCOL.md`: гипотеза, inputs, endpoints, варианты,
ranges/correlations, budgets, seeds/splits, tie tolerance, failed-run policy,
численные допуски, методы статистики, multiple comparisons и stopping rule.
Отдельные development и evaluation seeds/cases. Точный размер определить после
runtime pilot по точности оценок и ресурсам, а не обещать произвольную большую N.

Интервалы ансамбля — распределение результатов при заданных предположениях,
не автоматически клинические confidence intervals. Reference с более мелкой
сеткой сам требует проверки сходимости. Синтетическая self-consistency и
восстановление известных параметров не равны внешней клинической валидации.

### 10.4. Расширение: адаптивное планирование

Разрабатывать после baseline study и матрицы близких публикаций, если остаётся
самостоятельный исследовательский вопрос. Проверить гипотезу: можно ли
сократить стоимость достижения устойчивого вывода, сохранив качество сравнения?
Сравнить с fixed-budget random/space-filling sampling при одинаковом бюджете
и на независимых evaluation inputs. Учитывать sequential stopping при расчёте
интервалов; при empirical bounds честно проверить ошибку независимым benchmark.
Не добавлять surrogate/новую нейросеть без отдельного обоснования.
Отрицательный результат сохранить. Прохождение MVP не зависит от доказательства
заранее обещанного ускорения или новизны алгоритма.

## 11. Проверка корректности и критерии приёмки

Численные допуски ниже — проектные цели проверки реализации, а не опубликованная
клиническая точность и не изменения старых Stage 10 criteria.

| ID | Критерий и способ подтверждения |
|---|---|
| A01 | Lab открывается при отсутствующих CFB/atlas; API/UI tests не допускают вызов CFB loader в этом пути |
| A02 | Pinned upstream и hashes case проверены; package marker сам по себе не принимается за доказательство |
| A03 | Авторский case посчитан непосредственно upstream и через adapter при одинаковых inputs/times/settings; сохранены независимый reference и сравнение |
| A04 | Для A03 relative TCC error ≤1e-3 и normalized density RMSE ≤1e-4 по outputs; нормировка — к declared carrying capacity. Для near-zero TCC заранее задать абсолютный допуск. Не ослаблять по увиденному результату |
| A05 | Уточнение dt и пространственной сетки измерено отдельно; начальная физическая геометрия/масса сопоставимы. Допуски основной science series фиксируются по pilot до её запуска |
| A06 | Существующий analytic logistic smoke test остаётся зелёным; новые checks покрывают события лечения на границах шагов, finite values, единицы и отсутствие повторного применения фракции |
| A07 | Реальная trajectory содержит несколько времён; график/срез/mesh относятся к одному run/frame/geometry. GUI не показывает финальный кадр под любым временем |
| A08 | Run переживает API restart, не зависает в running; failure/timeout/cancel/retry проверены управляемыми тестовыми workers |
| A09 | Два одновременных клиента/idempotent POST не создают дубли; лимит concurrency соблюдён; отмена одного запуска не ломает другой |
| A10 | Plan/cache key изменяется при изменении case/engine/solver/treatment/seed; checksum mismatch и неполный cache не выдаются за succeeded |
| A11 | Повторный deterministic CPU run совпадает в зарегистрированных допусках; source/environment/seed доступны в export |
| A12 | Сравнение разных сценариев на одних subjects воспроизводится из export без ручного редактирования; denominators и failures сохранены |
| A13 | На analytic/small fixtures local sensitivities совпадают с известным/finite-difference reference; неподдерживаемые методы не показывают фиктивный ответ |
| A14 | Глобальное screening/cohort повторяются по сохранённому плану и seed; результаты и план не зависят от порядка завершения задач |
| A15 | UI: выбрать case → clone baseline → изменить → run → progress → результат → compare → export; browser smoke покрывает этот путь |
| A16 | Старые API/CFB artifacts, V2/V3 и scientific guardrails проходят regression suite; synthetic lab не открывает reserve/holdout |
| A17 | Ruff/pytest, ESLint/build и новые browser checks проходят; GitHub Actions проверены на точном итоговом commit |
| A18 | Выполнен frozen robustness protocol, включая отрицательные/неопределённые результаты; science artifacts имеют seal и воспроизводимый запуск |
| A19 | Setup/run/stop/recovery/data preparation документированы для Windows и CI; минимальный lab setup не требует полной клинической коллекции |

Если A04 не выполняется, сначала расследовать несовпадение workflows,
геометрии/normalization/events/runtime. Любое обоснованное изменение допуска
оформить как версию протокола до основной серии, не задним числом.

Полный engine integration test отдельно от быстрых small-fixture tests:
обычный CI не скачивает медицинские данные и не запускает большую 3D-когорту.
Для реального pinned engine предусмотреть отдельный воспроизводимый integration
job/локальную проверку. Моки проверяют orchestration, но не доказывают fidelity.
Добавить browser smoke инструмент при реализации (например Playwright);
сейчас в frontend имеются только lint/build, этого недостаточно для A15.

## 12. Порядок реализации и контрольные точки

| Этап | Работы | Условие перехода и MD |
|---|---|---|
| M0 — спецификация | Это ТЗ, reuse map, принятый scope, отслеживание состояния | ТЗ/README/direction/progress согласованы; не заявлять готовность кода |
| M1 — эталон | Проверка лицензии/версий, подготовка авторского case, native reproduction, adapter trajectory, fidelity и runtime pilot | A02–A07, case/source/environment manifests; `docs/IN_SILICO_LAB_REFERENCE_RESULT.md` |
| M2 — сквозной MVP | Settings/capabilities, durable runs, API, case/scenario editor, run/progress/cancel, timeline 2D/3D | A01, A07–A11, A15–A16; рабочий пользовательский путь без CFB |
| M3 — сравнение | Versioned scenarios, comparison, парные результаты, export/import, история и recovery | A08–A12; минимум baseline и изменённый сценарий посчитаны реальным движком |
| M4 — серии | Local sensitivity, global screening, cohorts, budgets, paired execution и diagnostics | A13–A14; небольшие реальные integration серии, не только mocks |
| M5 — исследование | Матрица литературы/вклада, frozen protocol, convergence/budget pilot, independent evaluation, анализ | A05, A18; reproducible study, а не скриншоты интерфейса |
| M6 — расширение | Adaptive budget controller при выполнении условий раздела 10.4 | Независимое сравнение с baseline и честная фиксация результата; можно обоснованно отложить |
| M7 — завершение | Документация, browser/integration/regression checks, release settings и license-gated deployment readiness | A17–A19 и все обязательные функции; public hosting только при выполнении раздела 4 |

Строить по сквозным этапам. Не делать сразу все экраны с заглушками, оставив
реальный engine напоследок. Не начинать большую серию до проверки fidelity.
После важного этапа обновлять progress и связанные MD, затем выполнять
соответствующие проверки и публиковать reviewable изменения в рабочую ветку.
Обычные обратимые инженерные решения выполнять автономно в рамках поручения;
не запрашивать повторное разрешение на уже согласованные работы.

## 13. Итоговые поставляемые материалы

1. Работающий lab в существующем приложении и сохранённый patient workspace.
2. Setup/data-preparation/run CLI, pinned engine adapter и reference artifacts.
3. Versioned contracts/API, persistent job execution, scenarios, comparison.
4. Sensitivity/cohort/robustness modules с протоколом и измеренными результатами.
5. Source/configuration/result provenance, export и повторение эксперимента.
6. Значимые unit/integration/browser tests, CI и hardware/runtime benchmark.
7. Developer/user MD: quickstart, assumptions/units, architecture, recovery,
   license/data use, limitations, исследования и воспроизведение.
8. Матрица самостоятельного вклада относительно TumorTwin и близких работ,
   методика и figures/tables для будущей статьи. Не обещать принятие статьи
   или заявлять новизну до сопоставления с литературой.

Работа завершена, когда другой исследователь может подготовить разрешённый
reference case, запустить и повторить эксперимент, понять предположения/ошибки,
сравнить сценарии и получить научно проверяемые результаты из сохранённого плана.

## 14. Контекст и старт следующего agent

Прочитать это ТЗ и progress, проверить Git/текущие instructions, затем начать M1.
Не выполнять заново завершённую CFB reserve validation и не переписывать проект.

Обязательный контекст:
- [IN_SILICO_LAB_PROPOSAL.md](../../IN_SILICO_LAB_PROPOSAL.md);
- [PUBLICATION_RESEARCH_STRATEGY.md](../../PUBLICATION_RESEARCH_STRATEGY.md);
- [MODEL_CODE_AUDIT.md](../../MODEL_CODE_AUDIT.md);
- [REFERENCE_BENCHMARK_PROTOCOL.md](../../REFERENCE_BENCHMARK_PROTOCOL.md);
- [REFERENCE_FIDELITY_V2_RESULT.md](../../REFERENCE_FIDELITY_V2_RESULT.md);
- [STAGE10_VALIDATION_RESULT.md](../../STAGE10_VALIDATION_RESULT.md).

При недоступности сети или лицензировании одного способа hosting продолжать
независимые локальные работы, фиксируя фактический blocker. Не подменять
TumorTwin непроверенной собственной динамикой, чтобы показать готовый интерфейс.
