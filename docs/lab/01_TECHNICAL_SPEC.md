# Техническое задание GBM Digital Twin Research Lab

Версия 2.0 • 6 ноября 2026 года • Язык продукта и основной документации русский

**Назначение:** единый исполняемый план завершения исследовательского программного средства для подготовки научных статей и последующего использования в дипломе по программной инженерии. Читатели: автор проекта, научный руководитель, разработчик и нейросеть исполнитель. Этот пакет задает требования к будущей реализации; он не объявляет перечисленные функции готовыми.

## 1. Решение и границы результата

Создать в существующем репозитории локальную лабораторию воспроизводимых вычислительных экспериментов на опубликованной модели роста опухоли и ответа на терапию. Первый движок — TumorTwin, первый случай — авторский synthetic HGG_demo_001. Существующие FastAPI, React, TypeScript и vtk.js переиспользовать. Первый рабочий путь не зависит от CFB-GBM, атласа и ранее скачанных данных пациентов: пользователь сообщил, что удалил тяжелые данные.

Общая тема проекта сохраняется: «Программно-алгоритмическое средство на базе исследовательского цифрового двойника глиобластомы для моделирования роста опухоли и прогнозирования ответа на терапию по продольным МРТ-данным». Первый релиз реализует исследовательскую среду и эксперименты на синтетическом HGG-случае. Он не подтверждает клиническую точность индивидуального прогноза по реальным МРТ. HGG-случай не переименовывать в молекулярно подтвержденную глиобластому реального человека.

**Законченный результат:** другой исследователь может подготовить разрешенный эталонный случай, воспроизвести upstream, создать сценарий, выполнить фоновый расчет, просмотреть реальные временные кадры, сравнить сценарии, провести ограниченную серию, экспортировать план и повторить расчет с проверкой допусков. Из результатов автоматически получаются таблицы и рисунки для двух самостоятельных исследовательских работ.

**В релиз входят:** проверенный engine adapter; кейсы и версии сценариев; устойчивая локальная очередь; временные кривые и 2D/3D; сравнение; конечные разности; Morris screening; воспроизводимая виртуальная выборка; исследование устойчивости ранжирования; контроль ресурсов и хранения; экспорт, повторение, тесты и документация.

**В релиз не входят:** новая биологическая PDE, собственная нейросеть, клинический подбор лечения, выживаемость, новый CFB reserve/holdout experiment, развитие атласной регистрации, облачная SaaS-инфраструктура, авторизация нескольких организаций, произвольная загрузка DICOM, Sobol как обязательный метод, Bayesian calibration как обязательная подсистема, surrogate/GPU acceleration и адаптивный вычислительный бюджет. Эти задачи не добавлять для обхода трудностей текущего этапа.

## 2. Актуальность и публикационный замысел

Актуальна задача проверяемых вычислительных экспериментов и обоснованности выводов механистических моделей. Но неопределенность, виртуальные когорты, цифровые двойники и адаптация терапии уже представлены в литературе. Нельзя заявлять, что проект первым вводит эти понятия или что веб-интерфейс устанавливает научную новизну.

Матрица первоисточников находится в [03_RESEARCH_BASIS.md](03_RESEARCH_BASIS.md). По проверке 05–06.11.2026 особенно существенны: опубликованный TumorTwin 2026 года; risk-aware HGG twin Chaudhuri et al. 2023; работа Pash et al. о пространственном прогнозировании с неопределенностью, доступная как arXiv:2505.08927; Bayesian personalization Lê et al. 2016. Последние две ограничивают притязания на новизну общей идеи учета неопределенности. Для Pash в этом пакете проверена аннотация; полный текст должен быть разобран на CP01 до окончательной заявки о вкладе.

**Самостоятельный вклад пока является проверяемой гипотезой:** единый проверенный жизненный цикл эксперимента и измерение устойчивости сравнений сценариев при ограниченных вычислительных ресурсах, с раздельным учетом параметрических, наблюдательных и численных возмущений.

Статья A отвечает: «Как организовать и проверить воспроизводимое выполнение сценарных экспериментов на опубликованном движке?» Статья B отвечает: «Когда сравнительное ранжирование заранее определенных сценариев меняется при допустимых возмущениях и численном уточнении?» Каждая получает собственные методы, основные результаты и выводы. Общие описание движка и набор данных цитируются без повторной выдачи одних результатов за два исследования.

Ни индексирование журнала, ни публикация не являются критерием завершения разработки. Обязательны проверяемые материалы статьи A и самостоятельный результат исследования B, включая отрицательный. Подготовка и отправка рукописи, переписка с редакциями и авторами внешнего движка выполняются только по отдельному поручению пользователя.

## 3. Исходное состояние и происхождение ТЗ

Аудит выполнен для `VeregaS/gbm-digital-twin`, рабочая ветка `feat/twin-protocol`, commit `e6ccf399ceb85d37c891ce053f631e5706bbef6b`. Ветка `main` остается на `3f20086e800be5f15c8c022efec36f6c9da7e953`. При старте реализации заново проверить branch, HEAD, status и применимые AGENTS.md. Состояние диска пользователя может отличаться от копии аудита.

В текущем чате подтверждены 571 Python test, Ruff, ESLint, frontend build и успешный CI для audited HEAD. Локальный прогон: Python 3.13, 57 dependency warnings; CI использует 3.11. Это baseline старого кода, а не приемка будущей лаборатории. Научные серии заново не запускались. Данные и локальные JSON/CSV старых результатов отсутствуют в копии аудита; сохранность на машине автора нужно инвентаризировать.

Существующее ТЗ 17.10.2026 и progress служат источниками контекста. Версия 2.0 конкретизирует их требования, меняет порядок внедрения на CP00–CP12 и вводит атомарную приемку. После принятия пакета разместить его в `docs/lab/`; старое ТЗ снабдить ссылкой на новое. Не удалять исторические научные протоколы. До внедрения пакета в репозиторий этот архив остается самостоятельным документом.

### 3.1. Что переиспользовать

| Область | Реальные исходники | Действие |
|---|---|---|
| Приложение | `api/app.py`, `api/config.py`, React App/Sidebar/Topbar | Добавить lab namespace и независимый startup |
| Геометрия | `data/nifti.py`, `preprocessing/resampling.py` | Переиспользовать; сохранять affine и единицы |
| Визуализация | `workflows/viewer.py`, `scene3d.py`, twin viewers | Выделять общие функции только при реальной необходимости |
| Движок | `reference/tumortwin.py`, `scripts/reference/tumortwin_worker.py` | Старый CFB adapter сохранить; новый lab adapter отделить |
| Происхождение | `workflows/provenance.py`, `repository.py` | Общие hash/version primitives; не переносить CFB payload целиком |
| Очередь | Anatomy BackgroundTasks и JSON status | Опыт polling; не считать готовой постоянной очередью |
| Старые модели | `models/`, `workflows/stage8_*`, `stage9_*`, `stage10_*` | Регрессия и архив результатов, без нового tuning |
| Проверки | `tests/`, GitHub Actions | Расширить meaningful lab tests и browser smoke |

### 3.2. Защищенное научное наследие

Stage 10 reserve validation по отчету: n=16, mean Dice 0.7084 против persistence 0.7426, paired delta −0.0341, два провала по принятому порогу; итог validation_failed. Новая лаборатория не меняет этот вывод. 16 раскрытых reserve случаев не использовать для настройки, оставшиеся 32 reserve и 21 holdout не открывать. Не переименовывать V2/V3 GUI artifacts в Stage 10. Не исправлять старые уравнения и не выдавать новый расчет за старый frozen результат. Пользовательское удаление данных не разрешает их незаметно скачивать заново.

## 4. Приоритеты и правила исполнения

`MUST` означает обязательную приемку текущего релиза. `LATER` — отдельный будущий change request. Все требования в приложении имеют ID, checkpoint, способ проверки и ожидаемое свидетельство. Реестр CSV является производной копией того же набора; при расхождении исправить генерацию, а не поддерживать две истины.

Порядок: научные границы → эталон движка → хранение и worker → минимальный сквозной UI → сравнение → серии → frozen исследование → release. Следующий checkpoint не считается принятым, пока его зависимости не имеют проверяемого результата. Прототип и mocks допускаются в тестах и разработке, но не заменяют проверку реального движка.

Исполнитель работает последовательно, не создает фоновые делегированные агенты без явного поручения. Не меняет stack ради удобства. Не добавляет новую подсистему для улучшения внешнего вида. Не делает полный рефакторинг старых workflows одновременно с лабораторией. Автономно решает обратимые инженерные вопросы в согласованных границах. Вопрос пользователю требуется при изменении темы, защищенных данных, разрешений внешней публикации или существенного вычислительного бюджета; отсутствие ответа не считать согласием.

После двух неудачных попыток одной гипотезы записать наблюдения и выбрать диагностическую проверку. После трех попыток без новой информации прекратить повторение, точно локализовать зависимость и продолжить независимые требования. Не ослаблять допуски ради зеленой приемки. Отрицательный научный результат является допустимым итогом исследования.

## 5. Пользователи и сценарии использования

Основной пользователь — исследователь на одном Windows ПК. Дополнительные роли: разработчик, воспроизводящий рецензент и научный руководитель. Это роли работы с локальным средством, а не требование реализовать учетные записи. Два браузерных клиента могут обращаться к одному серверу; межпроцессные конфликты должны обрабатываться.

### UC01. Первый запуск без данных пациентов

Предусловия: приложение установлено, CFB и атлас отсутствуют. Пользователь открывает «Лаборатория». Сервер возвращает легкие capabilities, engine status и case status. UI показывает отсутствующий эталон и инструкцию подготовки. Каталог, справка и диагностика доступны. Никакого patient-loader, загрузки атласа или автоматического скачивания не происходит. После явной подготовки кейс получает available. Сбой сети сохраняет локальную работоспособность и понятную причину unavailable.

### UC02. Подготовка авторского случая

Пользователь запускает документированную команду с источником и local data root. Система предварительно показывает состав, оценку размера и права использования. Загружает только whitelisted файлы выбранного случая, проверяет digest и геометрию, создает immutable case manifest. Прерванная загрузка остается incomplete; поврежденный файл не затирает исправную версию. Повторная подготовка использует verified files. Итог — case_id/version и receipt, без вычисления прогноза.

### UC03. Эталон upstream

Разработчик выполняет pinned author workflow напрямую, затем через новый adapter с теми же входами, preprocessing, RT/CT, solver и временами. Получает независимые outputs и fidelity report. Для reproduction разрешено точно повторить авторское использование visits/cropping, но отчет явно перечисляет использованные визиты. Этот режим не объявляется prospective forecast.

### UC04. Создание сценария

Исследователь открывает baseline, видит synthetic label и источник параметров, выбирает «Создать копию». Изменяет поддерживаемый параметр или schedule. Система валидирует конечность, единицы и ограничения, показывает diff и стоимость. Сохранение создает новую immutable версию. Невалидные значения сохраняются только в локальном несданном черновике; запуск блокирован с ошибкой у поля.

### UC05. Расчет и отмена

Исследователь подтверждает план кнопкой «Запустить расчет». POST возвращает 202 и ID; переход на страницу запуска происходит сразу. Страница отображает очередь, текущую фазу, прошедшее время и доступные подтвержденные счетчики. Отмена queued задачи исключает ее из очереди. Отмена running проходит cancel_requested и завершает только принадлежащее запуску дерево процессов. Поздний ответ worker не может перевести отмененную задачу в succeeded.

### UC06. Сбой и восстановление

API закрывается во время расчета. При следующем старте stale lease обнаруживается, попытка становится interrupted. Действующий подтвержденный worker может быть восстановлен только при совпадении ownership token и heartbeat; PID сам по себе недостаточен. Неподдерживаемое продолжение не имитируется: «Повторить» создает новую попытку с тем же plan. Завершенные элементы серии переиспользуются по hashes.

### UC07. Просмотр траектории

После succeeded исследователь видит метрики и первый фактически сохраненный кадр. Выбор времени синхронно меняет график, срезы и 3D. Во время загрузки новый кадр помечен loading; старый кадр не подписывается новым временем. Быстрые переключения игнорируют устаревшие ответы. Play проигрывает сохраненные кадры, а не симулирует вычисление. Отсутствующий mesh не блокирует график и срезы.

### UC08. Парное сравнение

Пользователь выбирает два завершенных запуска одного case/version. Система проверяет начальное состояние, time origin, units, endpoints и geometry. UI показывает diff, общую шкалу времени и цвета. Сравнение solver/settings с разными значениями разрешается в явно помеченном численном режиме. Несопоставимые случаи отклоняются. Нельзя заключить о лучшей терапии из разных горизонтов или неодинаковой начальной массы.

### UC09. Локальная чувствительность

Исследователь выбирает endpoint и continuous parameters, шаги h и h/2, фиксированные сценарий и начальное состояние. План показывает требуемые оценки. Выполняются nominal и возмущения через ту же очередь. В результате представлены производные, единицы, нормирование и сходимость шага. На границе применяется объявленная односторонняя формула; при нулевом nominal используется range-normalization. Ошибочные расчеты видны и не превращаются в нулевую чувствительность.

### UC10. Глобальный screening

Пользователь задает ranges, Morris trajectories/levels и seed. Предпросмотр содержит число evaluations и бюджет. После freeze sample matrix неизменна. Выполнение можно прервать и повторить, сохранив соответствие строк. Выводятся mu, mu_star, sigma и неопределенность оценки от конечного дизайна; точность индивидуального прогноза этими величинами не обозначается.

### UC11. Виртуальная когорта

Исследователь фиксирует генератор, параметры, распределения и общий initial geometry. Seed порождает неизменный subject table. Для каждого subject считаются одинаковые сценарии с общими параметрами subject. Неполные пары явно учитываются. Эти subjects — параметрические реализации на заданной геометрии; их число не приравнивается к числу независимых пациентов.

### UC12. Исследование устойчивости

Исследователь записывает question, candidate scenarios, endpoints, epsilon, uncertainties, seeds, budget и правила обработки failures. Pilot проверяет feasibility, после чего protocol замораживается. Генератор создает execution manifest. Все варианты оцениваются на одних subjects. Получаются paired differences, доля смены предпочтения и статус unresolved, если numerical error сопоставим с эффектом. Анализ выполняется одинаковым script, независимо от желательности результата.

### UC13. Экспорт и повторение

Пользователь выбирает compact export или полный разрешенный export. Компактный архив включает manifests, параметры, метрики, инструкции и hashes; запрещенные сторонние volumes не включаются. Другой workspace импортирует пакет как данные без исполнения произвольного кода. Проверяет hashes, сообщает отсутствующие licensed assets и после их явной подготовки повторяет план. Совпадение проверяется в заранее определенных допусках.

### UC14. Контроль диска

Исследователь открывает «Хранилище», видит размер data, outputs, caches и environments. Выбирает удаление выбранных производных кадров. Предпросмотр перечисляет зависимости и что останется воспроизводимым. Активные и publication-pinned artifacts не удаляются. После удаления скалярные результаты и provenance сохраняются, поле unavailable объяснено. Восстановление поля — новый расчет, не фиктивный cache hit.

### UC15. Старое пространство пациентов

Переход в «Данные пациентов» доступен независимо от лаборатории. При отсутствии CFB видна локальная инструкция, а не ошибка всей системы. Ни переход, ни старт лаборатории не загружают удаленную коллекцию. Старые routes/artifacts сохраняют контракты. Новый clinical dataset experiment не входит в этот релиз.

### UC16.Прогноз по продольным синтетическим МРТ

Предусловия: pinned author case и optimizer проверены, forecast protocol заморожен до target decoding. Пользователь выбирает режим synthetic forecast. Разрешены initialization по первому visit и fit по первым пяти visits в хронологическом порядке; cutoff — время пятого. Crop определяется только статической brain geometry и разрешенными данными. Predictions сохраняются и хешируются до чтения последующих observation arrays. Evaluator сравнивает разрешенные future visits с persistence последнего доступного состояния и author fixed-parameter model. Отчет показывает exact fit visits, forecast horizon, density/burden errors и data kind synthetic. Точность может оказаться низкой: это сохраняется без подбора дополнительных параметров по future observations. При отсутствии пяти visits остановить именно этот protocol как несовместимый, не подменять случай молча.

В demo forecast используются опубликованные initialization/observation mapping и upstream optimizer; optimizer budget и bounds фиксируются до main forecast. Будущая маска не используется для crop/threshold/fit selection. Prediction artifact и seal предшествуют evaluator access. Primary forecast endpoint — normalized density RMSE на разрешенных future frames с одним declared carrying-capacity scale; scalar burden error и thresholded Dice — secondary при заранее фиксированном threshold. Этот обязательный демонстрационный эксперимент связывает лабораторию с продольными MRI observations; он не является clinical validation и не расширяет scope до новой пациентской коллекции.

## 6. Архитектура

Один backend и один frontend. Новый домен `src/gbm_twin/lab/`: contracts, config, engine registry, cases, scenarios, plans, storage, runner, artifacts, comparison, sensitivity, cohorts, studies. Transport: `api/routes/lab_*`, `api/schemas/lab_*`; UI: `frontend/src/components/lab`, `frontend/src/api/lab.ts`. Конкретное дробление выбирать по связности, не создавать пустую иерархию на будущее.

FastAPI обслуживает короткие запросы; worker выполняет моделирование в отдельном процессе совместимого engine environment. SQLite хранит entities/statuses, filesystem хранит immutable arrays/manifests. В v1 достаточно одного supervisor и bounded workers, по умолчанию concurrency=1. Redis, Celery, Kubernetes, отдельный второй web server и пользовательский Python-код в API не требуются.

Engine adapter предоставляет `describe`, `validate`, `estimate`, `execute` и сведения о supported_outputs/cancellation. Autograd — отдельная capability; старый NumPy/detach adapter не подходит для градиентов. В v1 конечные разности обязательны, autograd — LATER. Выполнение через argv без shell-интерполяции; клиент не задает executable/module/import path. Descriptor проверяется сервером, а не доверяется браузеру.

### 6.1. Состояния запуска

Разрешены `queued → running → succeeded|failed|cancel_requested|interrupted`; `queued → cancelled`; `cancel_requested → cancelled|interrupted`. `running → timed_out` — отдельный терминальный статус. Результат завершения и причина доступны как machine code и русский текст. `succeeded` устанавливается только после проверки artifacts и atomic publication. Терминальное состояние не меняется поздним heartbeat. Retry создает новый attempt, не стирает старую ошибку.

Каждое изменение статуса имеет compare-and-set transaction с version и ownership token. Worker claim атомарен; два supervisors не выполняют одну попытку. Lease heartbeat раз в 5 s, stale после 30 s; startup сначала проверяет ownership. Polling интерфейса раз в 2 s при активном запуске, backoff до 10 s при ошибках; idle страницы не создают постоянный поток запросов. Длительный шаг может не давать научного прогресса, но supervisor продолжает heartbeat.

POST /runs поддерживает Idempotency-Key: тот же ключ и тот же canonical request возвращает прежний run; другой payload с тем же ключом — 409. Одинаковый plan без общего ключа допускает явный rerun. Cache reuse — отдельное подтвержденное действие/политика; run имеет reused_from и не имитирует новый расчет.

### 6.2. Хранение и транзакции

WAL SQLite с foreign_keys и versioned migrations. Короткие транзакции, bounded busy timeout, отсутствие долгой симуляции под write lock. Бэкап live database выполняется SQLite backup API; копирование только .db при активном WAL не считается бэкапом [S11]. Сохранение большого результата: temporary directory → все frames/metrics → проверки → manifest/hash → atomic rename → DB commit. Startup reconciliation определяет orphaned temp и ready artifacts без DB record; не угадывает successful status.

Пути формируются из server-side UUID и проверяются относительно разрешенного root. Экспорт не следует произвольным symlink/junction. Import отвергает path traversal, executable payload и pickle; ограничивает количество/размер распакованных файлов. Миграция никогда не переписывает scientific artifact in place: новый schema version и явный converter.

## 7. Модель данных

Все timestamps — ISO 8601 UTC; UI отображает локальное время. Научная ось времени — days_from_origin с явным origin. Все числа конечны. JSON serialization запрещает NaN/Inf. UUID используется для entities, content hashes — для научной идентичности. Название и заметки могут меняться в metadata; научная версия immutable.

| Сущность | Обязательные поля и инварианты |
|---|---|
| EngineDescriptor | engine_id, upstream_commit, source_fingerprint, adapter_version, environment_fingerprint, schema_version, supported parameters/treatments/solvers, citations, use_status |
| PreparedCase | case_id/version, synthetic kind, source URI/commit, file hashes, geometry, dates, observation roles, baseline_id, size_bytes, compatibility |
| Geometry | shape[3], affine[4,4], spacing_mm[3], spatial_units, orientation, domain hash; affine nonsingular, arrays same grid |
| Parameter | key, symbol, display_name_ru, finite value, unit, range, origin=author|assumed|fitted|generative, editable capability |
| ScenarioVersion | UUID/version, parent, case/version, engine, parameters, initial_state_ref, RT/CT events, horizon, outputs, solver, precision/device, seed |
| RunPlan | canonical scenario snapshot, all scientific hashes, output policy, limits, study_ref, plan_hash, schema_version |
| RunAttempt | run_id, attempt, plan_hash, state/version, token/lease, lifecycle timestamps, phases, resource stats, error code, artifact_refs, reused_from/retry_of |
| ResultManifest | run_id, validated state, frames(time,index,shape,dtype,hash), metrics schema, geometry hash, engine/environment, warnings, complete flag |
| Comparison | ordered run refs, compatibility verdict, interpolation policy, endpoints, epsilon, paired metrics and unit |
| StudyProtocol | study_id/version/kind, question, candidates, parameters/distributions, seed splits, primary/secondary endpoints, failures, budget, freeze_hash; kind включает local_sensitivity, morris, cohort, ranking_robustness и synthetic_forecast |
| StudyExecution | frozen protocol ref, sample/subject table hash, child task matrix, child attempts, denominators, timestamps, analysis_version |

Canonical identity использует сортированные keys и явные единицы, normalized float serialization с документированным алгоритмом без грубого округления. Включаются численно значимые engine/source/adapter/solver/library/device/precision versions, treatment events, geometry и входные digest. Absolute local paths, display name, local UI state не меняют scientific hash. Отдельный execution hash включает output policy и runtime resources. Это позволяет различать scientific equivalence и допустимость reuse точных artifacts.

Scenario draft — frontend состояние с явным «Не сохранено». Сохранение требует server validation. Любая scientific edit создает новую ScenarioVersion; сохраненный baseline read-only. Result immutable; attach note хранится отдельно.

### 7.1. Расположение артефактов

```text
<LAB_ROOT>/
  lab.sqlite3
  cases/<case_id>/<version>/manifest.json
  runs/<run_id>/attempt-<n>/
    plan.json
    environment.json
    events.jsonl
    metrics.csv
    frames/<index>.npy
    result.json
    artifacts.sha256
  studies/<study_id>/<version>/
    protocol.json
    protocol.sha256
    subjects.csv
    execution.jsonl
    outcomes.csv
    analysis.json
    figures/
  exports/
  tmp/
```

Формат frames допускается заменить на chunked storage через ADR, если сохраняются правила хеширования, выборочного чтения и лимиты; для v1 достаточно отдельных .npy без pickle. SQLite, medical volumes, внешние данные и большие arrays вне Git. В Git — source, tests, допустимые tiny synthetic fixtures, schemas, configs, документация и небольшие обезличенные scientific tables при разрешенных правах.

## 8. Эталон и численная корректность

Pinned upstream: `OncologyModelingGroup/TumorTwin`, commit `bedf90a6d47ba48cf5cdb25901967d84730061d1`. Перед использованием проверить фактический source fingerprint и environment; marker-файл с SHA недостаточен. Первый case — `input_files/HGG_demo_001`; JSON источника содержит MRI visits, RT и CT, поэтому silent omission CT недопустим при заявлении faithful reproduction [S02].

Режимы явно разделены:

1. **Author reproduction:** точное воспроизведение авторского workflow, включая cropping/visits. Эталон получается отдельным прямым upstream запуском; adapter не может сравниваться со своей копией результата.
2. **Synthetic forecast:** отдельный cutoff; initialization/calibration/crop используют только разрешенные наблюдения до cutoff. Future targets доступны исключительно evaluator. Если это не реализовано, называть режим forward simulation, а не verified forecast.
3. **Scenario simulation:** одни стартовые условия, заранее заданные изменения терапии, интерпретация в рамках модели.

Сопоставить `rho ↔ k`, `D ↔ d`, normalized density, carrying capacity, mm, days, Gy и CT dose units. Не присваивать TCC единицы «клетки» до подтверждения формулы и carrying capacity. До этого допустим интеграл normalized burden в mm³. Пороговый volume — отдельная метрика с явным threshold; не выдавать его за измеренный MRI volume.

Fidelity F1: максимальная по output times относительная ошибка TCC ≤ 1e−3; F2: normalized field RMSE ≤ 1e−4 на каждом контрольном кадре. Near-zero denominator: использовать declared scale из carrying capacity и абсолютный допуск, замороженный до сравнения. Проверить одинаковые shape/affine/time/events; не использовать spatial registration outputs друг к другу ради прохождения F2. Если авторский solver недетерминирован, документировать повторные запуски и объяснить variance до study freeze.

Минимальные probes: logistic ODE с известным решением; отсутствие роста/лечения; чистая диффузия и mass balance в no-flux domain; treatment на начале/конце шага; совпадающие RT и CT времена; отсутствие повторной фракции при разбиении интервала; cutoff, empty domain и nonfinite input. Известные saturation свойства PIRT считать модельным выбором, а не автоматически ошибкой [S07].

Convergence pilot: dt, dt/2, dt/4 на одном физическом случае; хотя бы две пространственные сетки в общей физической области с сопоставимой initialization. Уточнение сетки отделять от изменения исходной физической массы. Вычислять endpoint errors и stability of pairwise ranking. Самая мелкая сетка — reference approximation, не точное решение. Study freeze фиксирует численные допуски и unresolved policy. Нельзя ослабить F1/F2 или ranking epsilon после просмотра основной серии.

## 9. Лицензии и локальная подготовка

UT Austin Research License закрепленного upstream разрешает определенные академические/исследовательские применения и ограничивает коммерческое использование и передачу кода; производные работы также оговорены [S03]. Написать `LICENSE_AND_DATA_USE.md` с точными ссылками и применением к локальному запуску, нашему адаптеру, demo data, exports и предполагаемому hosting. Это инженерная проверка ограничений, не окончательное юридическое заключение.

Без установленных прав не включать upstream code/volumes в свой публичный репозиторий или archive. Собственный source и разрешенные метаданные готовятся отдельно. Не писать авторам автоматически. Если hosting остается неясным, продолжать разрешенную локальную разработку и считать public deployment отдельным незавершенным расширением, а не останавливать все ТЗ.

Не скачивать CFB-GBM, Burdenko или атлас ради lab startup. Подготовка author case выполняется явным CLI с whitelisted source/ref/files и receipt. Выводить expected bytes до загрузки. Пользовательские файлы при checksum mismatch не затирать. Нет сети — доступны small fixtures, UI states и orchestration tests; full engine acceptance остается pending до реального результата.

## 10. Ресурсы и хранение

Эталон — один Windows ПК, CPU mode, concurrency=1; GPU и Linux runtime не являются обязательной пользовательской зависимостью. Python 3.11 для pinned engine, frontend Node 24 согласно CI; фактические совместимые versions фиксируются в CP02. Не менять пользовательское окружение молча, создавать отдельный engine environment в разрешенном workspace.

Начальные engineering limits, подлежащие только документированному изменению до основных исследований: runtime storage 8 GiB без environments; 2 GiB обязательного свободного места; ≤1 GiB output на run; ≤21 полных density frames; scalar series отдельно; ≤256 queued child tasks на один submit; concurrency=1. Окружения и raw assets имеют отдельную оценку размера и отображаются в storage overview. Значения лимитов не являются оценкой фактической стоимости TumorTwin; CP03 измеряет ее.

Peak RAM и wall time заранее неизвестны. Pilot измеряет их, ставит per-run timeout, max memory budget и допустимый размер study. Политика процесса не должна завершать чужие приложения. При превышении disk quota worker останавливает запись и завершает run с disk_limit; не удаляет старые publication artifacts. При невозможности точного RAM-limit на платформе честно объявить soft monitoring и проверить timeout/cancellation.

Frames streaming или selected-time solve не должны сохранять всю 4D trajectory без учета RAM. Диагностировать реальные capabilities pinned solver; при необходимости adapter сохраняет только selected frames без изменения научного интегрирования. Компрессия и mesh decimation не меняют raw metrics. Preview/downsampling маркируются и не заменяют научный массив.

Очистка: только явно выбранные regenerable artifacts в LAB_ROOT с разрешенным resolved path; dry-run и dependency check обязательны. Active, frozen publication и source inputs защищены. После удаления frames metrics/manifest остаются с availability flag. Автоочистка по умолчанию выключена. Backups и exports тоже учитываются в disk budget. Скачать удаленные patient datasets для исправления ошибки запрещено.

## 11. API и ошибки

Все новые endpoints в `/api/lab`. Тяжелая операция возвращает 202; GET не запускает download/calibration/simulation. Pagination cursor/limit применяется к спискам. UUID/version проверяются; неизвестный ресурс — 404. Ошибка имеет `code`, `message_ru`, `field_errors`, `retryable`, `request_id`, `details_ref`; raw traceback не показывается основным UI.

| Endpoint | Контракт |
|---|---|
| GET /capabilities | lab readiness независимо от CFB; engine/case/storage причины |
| GET /engines, /engines/{id} | supported controls, source/version/use status |
| GET /cases, /cases/{id}/versions/{v} | manifest summary, available/missing/corrupt, geometry |
| POST /scenarios/validate | canonical validated preview или 422 field errors |
| POST /scenarios | immutable version, 201; parent и baseline references |
| GET /scenarios/{id}/versions/{v} | точный snapshot |
| POST /plans/preview | counts, bytes estimate, budget feasibility; без queue |
| POST /runs | 202; Idempotency-Key; immutable server-side plan |
| GET /runs, /runs/{id} | state, phase, progress, warnings, attempts, refs |
| POST /runs/{id}/cancel | 202 requested или idempotent terminal response |
| POST /runs/{id}/retry | новый attempt; terminal old preserved |
| GET /runs/{id}/metrics | endpoint schema/units, actual scalar times |
| GET /runs/{id}/frames | только saved frame descriptors |
| GET /runs/{id}/frames/{idx}/slice | axis/index/window/layers, validated bounds |
| GET /runs/{id}/frames/{idx}/scene3d | bounded mesh с geometry/time metadata |
| POST /comparisons | paired refs и compatibility policy, 201 или 409 |
| POST /studies | draft immutable protocol version; synthetic_forecast принимает allowed fit visits и cutoff, evaluator targets не передаются worker fit |
| POST /studies/{id}/freeze | hash protocol/sample matrix, validates completeness |
| POST /studies/{id}/run | 202, child matrix и budgets; повтор idempotent |
| POST /studies/{id}/cancel | cancel remaining active children, preserve complete |
| GET /studies/{id}/results | denominator и incomplete/failure handling |
| POST /exports | 202 если нужен packaging; artifact ID после готовности |
| GET /exports/{id} | разрешенный готовый архив; download без повторной сборки |
| POST /imports/validate, /imports | bounded data validation, затем registration |
| GET /storage | measured sizes, pinned/active info |
| POST /storage/cleanup-preview, /storage/cleanup | exact selection token, protected artifacts |

409: immutable conflict, incompatible comparison или idempotency conflict. 422: invalid input/unsupported control. 503: engine unavailable; readiness объясняет восстановление. Resource rejection использует 409 с resource_budget_exceeded и измеренной оценкой, не ложный 500. Timeout/OOM/worker error представлены в RunAttempt, запрос polling при этом возвращает 200 с terminal state. OpenAPI и TypeScript генерировать или проверять contract tests; единицы и optional values согласовать.

## 12. Интерфейс и экранные контракты

Общий shell существующего проекта сохранить. Продукт по умолчанию открывает «Лаборатория», даже если нет CFB. В навигации: «Случаи», «Сценарии», «Запуски», «Сравнение», «Исследования», «Хранилище», «Методика». Чувствительность и виртуальные когорты — виды исследования, не дублирующие независимые executors. Старое пространство «Данные пациентов» доступно отдельно. Нереализованные экраны до принятия checkpoint скрыты; отсутствующие ресурсы реализованного экрана представлены честным empty state.

Верхняя строка показывает текущий workspace и research label. Технические SHA, schema и worker identity доступны в раскрываемой «Диагностике» и экспорте; не занимают основные действия. Красный цвет — ошибка, желтый — оговорка, нейтральный — queued, зеленый — проверенное программное завершение; зеленый не обозначает клиническую эффективность.

### 12.1. Экран случаев

Карточка: название, synthetic label, source/citation, доступность, размер, supported engine и кнопка «Открыть». При missing data — текст «Файлы случая не подготовлены» и конкретная команда/ссылка на локальную подготовку. Существующий author baseline read-only. Детали показывают доступные модальности, dates, physical geometry и разрешенные наблюдения; fitted и generative parameters подписаны отдельно. Поиск и сортировка не запускают обработку данных.

### 12.2. Редактор сценария

Секции: исходный случай; биологические параметры; RT; CT; расчет; сохранение результатов. Поля генерируются из engine capabilities, но display text на русском задается приложением. Каждый numeric control содержит единицу, значение, допустимые границы и источник default; scientific notation доступна. Слайдер — дополнение к точному вводу. При вводе запятой поддержать нормализацию локали или объяснимую ошибку без тихого изменения величины.

Расписание — таблица событий с временем от origin, modality, dose и unit; add/delete row, stable sort. RT+CT в одно время допустимы, повтор одного modality события требует явной семантики. Интеграционный dt и scalar/frame output interval — разные controls. Horizon ограничен plan validation. «Сбросить» возвращает значения baseline, «Сохранить копию» создает новую версию, «Запустить» доступно после server preview. Во время POST кнопка блокирована, но idempotency обеспечена сервером.

### 12.3. Экран запуска

Шапка: name, case, scenario/version, status, elapsed time, действия «Отменить», «Повторить», «Сравнить», «Экспорт». Действия видны по допустимому состоянию. Фазы: queued, preparing, solving, writing, validating; проценты показываются только при известном denominator. ETA появляется только из measured pilot и помечен оценкой. Failed/interrupted содержит причину и безопасное следующее действие. Отдельная панель показывает partial outputs; они не называются complete.

### 12.4. Просмотр

График с осью days, endpoint/unit и treatment markers. Выбор кадра — по действительному saved time; доступен keyboard slider и previous/next. 2D: axial/coronal/sagittal при подтвержденной orientation, slice index и physical location, window/level для MRI и отдельная density color scale. Не ставить L/R без проверки affine. 3D — secondary view, layer toggles, reset camera, loading/error, ограниченный mesh. На low-capability/WebGL failure работают график и 2D. Нет поверхности при выбранном threshold — текст, а не ошибка всей страницы.

### 12.5. Сравнение

Две панели с одинаковыми camera/slice/time и общей шкалой по умолчанию. Sync можно отключить явно. Таблица diff перечисляет все измененные scientific inputs. На графике видны обе trajectories и paired delta. Несовпадающие saved times не интерполируются молча; политика scalar interpolation фиксируется, поля выбираются по exact common times или помечаются nearest. Endpoint epsilon и unresolved status отображаются рядом с предпочтением. Слова «лучшее лечение» не использовать; «меньший расчетный endpoint в заданной модели» допустимо.

### 12.6. Исследования

Wizard: вопрос/тип → case/scenarios → factors/distributions → endpoints → sampling/budget → preview → freeze → run. Frozen version read-only; изменение создает новый draft и новую научную серию. Сводка показывает requested/completed/failed/paired counts, seed, range assumptions и output retention. Morris chart не выдает rank без uncertainty display/методики. Когорты показывают row-level parameters, paired outcomes и missing reasons. Нельзя выбирать победивший вариант и скрывать failures кнопкой фильтра: фильтр влияет на просмотр, но primary summary остается по протоколу.

### 12.7. Общие UX требования

Каждый экран имеет loading, empty, ready, error и unavailable состояния. Keyboard navigation, focus indicator, labels для controls, текстовое обозначение статуса помимо цвета. После ошибки submit данные черновика не теряются. Back navigation сохраняет draft с предупреждением о несохраненных изменениях. Layout проверяется на 1366×768 и 1920×1080; узкий экран 1024 px остается usable, мобильный medical viewer не входит в обязательный объем. Основные действия не уходят за горизонтальный scroll; длинные таблицы допускают собственную прокрутку. Browser smoke проверяет реальный сценарий через API.

## 13. Алгоритмы и научные метрики

### 13.1. Outcomes

Primary endpoint первого robustness study — нормированный интеграл burden по времени на одинаковом horizon: J = AUC(B)/(T × B0), где B0 — общий положительный initial burden, T — общий horizon. J безразмерен, меньшее значение предпочтительнее в рамках модели. При B0=0 такой study отклоняется до freeze. Изменение primary требует новой версии протокола до evaluation. Secondary: final burden/TCC, peak burden и thresholded volume с fixed threshold. Нельзя после результатов поменять primary на более выгодный. При unsupported carrying capacity публиковать normalized burden, а не TCC с выдуманными единицами.

Интеграл по времени считать trapezoidal rule на scalar outputs с реальными times. Стабильность scalar sampling проверить отдельно от solver dt. В spatial integral использовать physical voxel volume; при общем affine учитывать determinant, а не предполагать axis-aligned geometry без проверки. Relative change при нулевом baseline undefined с reason; не заменять на 0. Порог progression, если используется, считается модельным surrogate; никакой реальной выживаемости из него не выводится.

### 13.2. Local sensitivity

Для smooth endpoint J и interior p: central finite difference `[J(p+h)−J(p−h)]/(2h)`; выполнить h и h/2, зафиксировать error indicator. При p=0/range-boundary — documented one-sided stencil. Нормирование `p/J` используется только при ненулевых scales; иначе declared parameter range и endpoint scale. Perturbations не меняют другие factors, geometry и schedules. Пороговые endpoints могут быть негладкими: это обозначается, проверяется step-dependence и не интерпретируется как отсутствие влияния.

### 13.3. Morris

Использовать проверенную pinned реализацию SALib либо обоснованный эквивалент; не писать новый метод с нуля ради релиза [S10]. До run сохранить factor names/order, bounds/transform, levels, trajectories, seed и sample matrix. Для k независимых факторов базовый design требует r(k+1) evaluations до cache reuse. mu_star и sigma интерпретируются как screening в заданных ranges, не Sobol indices и не parameter identifiability. Correlated inputs не объявлять независимыми; v1 поддерживает independent design с явной оговоркой. Discrete schedule factors исследовать отдельным predefined scenario comparison, не передавать как непрерывные Morris factors без методики.

### 13.4. Cohort и парные различия

Default generator: seeded Latin hypercube для ≤4 continuous factors с явными independent bounded distributions; uniform — исследовательское допущение, не популяционная частота. При положительных log-scale factors transform фиксируется. Initial case geometry общая, seed одинаков для всех сценариев subject. В публикации различать number of geometries, parameter realizations и observation replicates. Если несколько шумовых реализаций на одной truth geometry, bootstrap группируется на уровне исходной независимой единицы или явно интерпретируется как Monte Carlo uncertainty, а не clinical population CI.

Для lower-is-better endpoint: `delta_AB=J_A−J_B`; A preferable при delta < −epsilon, B при delta > epsilon, иначе unresolved/tie по frozen numerical policy. Для каждого subject считать paired delta. Report включает all planned subjects и denominators. Доля preference/rank reversal относится к выбранной virtual distribution. Индивидуальная вероятность клинической пользы из нее не следует.

## 14. Исследовательский протокол и две статьи

### 14.1. Статья A

Contribution: lifecycle of reproducible experiments around pinned engine, verifiable fidelity, durable execution и bounded storage. Минимальная benchmark matrix: direct upstream vs adapter на identical inputs; повтор deterministic CPU; два клиента и idempotency; cancel/timeout; restart/retry; hash corruption; compact export/replay; disk budget. Измерять wall time с раздельными preprocessing/solve/write/render, peak RAM, disk bytes и повторяемость endpoints. Не объявлять ускорение, пока matched benchmark его не показал. UI usability claims требуют отдельной user study; без нее ограничиться correctness и task completion browser tests.

Deliverables: manuscript outline с заполненными methods/results, architecture figure, fidelity/convergence table, reliability matrix, reproducibility receipt, limitations и вклад автора/AI-assisted development. Научное утверждение должно иметь ссылку на immutable experiment artifact. Источник software design criteria — [S12], не требование подать в конкретный журнал.

### 14.2. Статья B

Question: устойчивость сравнительного предпочтения predefined RT scenarios к параметрическим и численным возмущениям в фиксированной модели. Это scoped computational study, не новый клинический оптимизатор. В первой серии CT сохраняется как авторский background, если capability faithful CT подтверждена. Для RT comparisons сохранять одинаковые total dose и fraction count, варьировать заранее определенное распределение времен; все schedules проходят engine constraints. Не выдавать tumor-only comparison за оценку normal-tissue toxicity.

Scenario registry фиксирует baseline и два поддерживаемых comparator schedules. Конкретные времена определяются CP03 на основе author schedule и capabilities, без просмотра comparative outcomes основной серии. Если schedule не меняется физически значимо, нельзя подбирать варианты до получения желательного reversal; зарегистрировать нулевой эффект как результат.

Uncertainty blocks: U1 continuous model parameters с literature/author ranges; U2 numerical dt и scalar output sampling; U3 initial-state observation perturbation — bounded synthetic variation отдельно от U1. U3 включать в основную серию только если оно определено в protocol и сохраняет finite/physical constraints; иначе оформить отдельным обязательным малым diagnostic study, не заявлять full segmentation UQ. Пространственную geometry менять только в convergence block.

Design: pilot set seed=1105, analysis development seed=2205, locked evaluation seed=3305. Наборы не переиспользуются для настройки ранжирования. Их независимость условна относительно одной модели/geometry; это не external clinical validation. Размер фиксируется feasibility rule ниже. Результат на evaluation не используется для изменения ranges/candidates/epsilon. Любое последующее изменение — новый protocol version и отдельная работа.

Primary pair — baseline против первого заранее зарегистрированного comparator; второй comparator и остальные пары являются secondary. Для lower-is-better J определим c(delta): −1 при delta < −epsilon, +1 при delta > epsilon, 0 иначе. c0 рассчитывается для замороженных nominal parameters. При c0≠0 primary statistic — доля запланированных subjects с c_i=−c0. При c0=0 primary outcome — «номинальное ранжирование не разрешено», statistic undefined; не выбирать другую primary pair после этого результата. Дополнительно представить mean/median paired delta, quantiles, unresolved proportion, complete-pair fraction и sensitivity ranks. Pilot сравнительные результаты не входят в locked evaluation.

При R наблюдаемых reversals, M subjects с missing primary outcome и N запланированных subjects report primary reversal fraction interval [R/N, (R+M)/N] как границы из-за missingness. Это не confidence interval. Complete-case R/(N−M) допустим как дополнительный условный показатель. Не смешивать missing, unresolved и no-reversal в одно доказательство устойчивости. Sampling intervals, если рассчитаны, показываются отдельно от missingness bounds.

Numerical epsilon определяется из independent convergence pilot и научной шкалы endpoint: документировать абсолютную и относительную компоненты, rule `epsilon=max(epsilon_abs, epsilon_rel*scale, numerical_error_bound)`. Numerical_error_bound — измеренная оценка для declared regime, не универсальная теорема. Если пары попадают в unresolved, не принуждать ranking. Не считать count of unresolved как устойчивую победу baseline.

### 14.3. Ограниченный вычислительный план

Pilot: ≤12 полноразмерных forward solves, предварительно оценить memory/disk. Целевой study budget после пилота — ≤12 h wall time и ≤4 GiB новых outputs; это бюджет исследования на машине автора, а не обещание длительности. Формула количества solves учитывает scenarios × subjects × numerical settings × replicates, calibration solves отдельно. Режим full fields только для baseline и заранее выбранных demonstration subjects; остальные outputs scalar-only и ограниченные checkpoints.

Feasibility ladder фиксируется до main study: k≤4, Morris r из {12,8,4}, cohort N из {64,32,16}, максимум три scenarios. Выбрать максимальный design, который укладывается в измеренный budget с 30% запасом; использовать верхнюю измеренную стоимость pilot, а не среднюю лучшего запуска. Если minimum N=16/r=4 не помещается, выполнить ограниченный feasibility report, сохранить pipeline и зафиксировать scientific checkpoint как incomplete. Не объявлять publishable robustness conclusion на произвольных двух samples. Увеличение бюджета требует отдельного согласования, не запускается автоматически.

Resampling/bootstrap uncertainty: при использовании указать estimand, sampling design, unit и число replicates (default 2000, seed frozen). Для LHS обычный iid bootstrap может быть приближением; предпочтительно report independent randomized design repeats либо честная descriptive interval без claim coverage. Нельзя заменять computational uncertainty на confidence clinical prediction. Не вводить p-value как единственный критерий; primary conclusions основывать на effect sizes и numerical resolution.

### 14.4. Failures и независимость

Failed tasks не удаляются из denominator. Если primary paired summary требует complete pairs, одновременно представить all-planned count и worst/best bounded sensitivity либо отказ от утверждения при неограниченных missing outcomes. Failures с доменными причинами могут зависеть от параметров; complete-case conclusion обозначается conditional. Повтор transient error использует ту же sample row и candidate; replacement subject запрещен. Stopping rule — budget/failure thresholds из freeze, а не появление красивой кривой. Threshold failures для scientific analysis устанавливается CP09 до evaluation; инфраструктурный smoke требует 100% expected tasks.

### 14.5. Продольные МРТ

В обязательный lab релиз входят author synthetic MRI visits и честное описание их использования. Новая клиническая серия не является скрытой зависимостью. Для будущих утверждений о реальной MRI forecasting accuracy нужен отдельный clinical protocol, selective acquisition и patient-level external validation. Сохранить старые negative CFB results как background, не смешивать с новой synthetic evaluation. Отсутствие реальных данных не компенсировать созданием фиктивных пациентских записей.

## 15. Нефункциональные требования и приемка

На small fixture без тяжелого solver: startup и первый capabilities response ≤3 s после готовности процесса; p95 lightweight API ≤500 ms на localhost без active solve; во время solve UI status response p95 ≤1 s. Измерять 30 запросов после warmup, hardware manifest и payload sizes. Эти targets обязательны для fixture; full case latency измеряется в pilot и фиксируется в acceptance profile. Если single-machine contention нарушает targets, ограничить CPU threads worker до изменения frontend.

UI: cancel feedback после POST ≤1 s; supervisor дает до 2 s на cooperative stop, затем при необходимости завершает собственное process tree с общим пределом ≤10 s от принятого cancel. Если host не позволяет гарантировать termination, зафиксировать failed acceptance и platform limitation, а не бесконечный spinner. Совпадающий repeated cancel idempotent. Frame/slice rendering cache использует result/frame/geometry/render settings; визуальные caches можно очистить без потери scientific truth. Large render выполняется вне event loop либо bounded thread/process policy; перегрузка возвращает объяснимый ответ.

Безопасность локальной версии: bind localhost по умолчанию, ограниченные CORS origins, отсутствие произвольного запуска кода из imports, safe serialization, ограниченные запросы и disk paths. Публичный hosting, authentication и multi-tenant isolation требуют отдельного design/security review. Не объявлять локальный research server готовым к открытой сети. Использовать `.env.example` без secrets; логи не содержат чужие absolute paths в публикационном экспорте.

Поддерживаемость: typed contracts, разделение domain/transport/engine, bounded modules с ответственностью; ориентир review при module >500 строк, а не жесткое требование механически дробить. Dependency lock для app и engine отдельно; Node lock сохраняется. Для сохраненных scientific results записывать exact resolved versions и hardware; cache version меняется при численно значимом изменении.

## 16. Проверки

Уровни: pure unit (schemas, hashes, statistics, transitions); integration (SQLite/filesystem/real API/controlled worker); numerical analytic fixtures; pinned engine fidelity; browser (реальные API); scientific freeze/replay. Mock engine используется только для управляемых сбоев и fast pipeline tests. Полный author engine проверяется отдельно и не скачивает gigabytes в обычном CI.

Обязательные browser paths: no-CFB startup, edit/validation, run/result/time change, cancel, restart page/retry, pair comparison, study preview/freeze, export и storage preview. Проверить race быстрого frame switching и error recovery. Accessibility smoke: tab order, visible focus, labels и no color-only states. Не добавлять сотни тестов, которые повторяют implementation details: каждая проверка должна закрывать риск или acceptance condition.

На каждой стадии — targeted checks; при изменении domain/API — полная Python suite перед приемкой; при UI — lint/build и соответствующие browser tests. Перед release — full suite, exact-commit CI, pinned engine result, export/replay и scientific analysis reproducibility. Зависимые warnings классифицировать, не скрывать. Baseline 571 не является целевым количеством тестов: оно может меняться обоснованно.

## 17. Контрольные точки

Каждый checkpoint выполняется небольшими атомарными задачами из приложения требований. Ниже указано, какое evidence разрешает переход. Формат evidence: commit, requirement IDs, changed files, commands, exit codes, artifact paths/hashes, result, known limits, next checkpoint. Утверждение «готово» без evidence не принимается.

| CP | Результат | Зависимости | Свидетельство выхода |
|---|---|---|---|
| CP00 | Инвентаризация и принятие единой спецификации | — | BASELINE.md, protected files list, нет изменения equations/data |
| CP01 | Актуальность и самостоятельный вклад | CP00 | PRIMARY_SOURCE_MATRIX.md, full-text comparison ближайших работ, statement of need и допустимые claims |
| CP02 | Лицензии, pinned source и точное окружение | CP01 | LICENSE_AND_DATA_USE.md, source/env manifests, case preparation receipt |
| CP03 | Прямой upstream и adapter fidelity, ресурсный pilot | CP02 | REFERENCE_RESULT.md, F1/F2, convergence diagnostics и measured budget profile |
| CP04 | Domain contracts, SQLite и immutable storage | CP03 | migrations, transition/hash/corruption tests, API contracts |
| CP05 | Durable worker, cancel/restart/idempotency | CP04 | failure matrix с controlled worker и один реальный run |
| CP06 | Сквозной UI case → scenario → run → frames | CP05 | browser evidence без CFB, real trajectory и времена |
| CP07 | Парное сравнение, export/replay, storage | CP06 | matched pair, fresh workspace replay, cleanup protection |
| CP08 | Local/Morris/cohort через один executor | CP07 | analytic sensitivity tests, seeded matrices, real bounded mini-series |
| CP09 | Два frozen study protocols и публикационный план | CP08 | S-A/S-B protocols, ranges/epsilon/budget/failures/seeds, protocol hashes |
| CP10 | Измерения статьи A и robustness series B | CP09 | all-planned outcomes, analysis outputs, отрицательные результаты сохранены |
| CP11 | Материалы двух статей и методика | CP10 | methods/results drafts, figures/tables и claim→artifact links |
| CP12 | Release и независимое воспроизведение | CP11 | clean workspace run, exact CI, acceptance matrix, changelog и known limits |

CP01 не требует доказывать всемирную новизну. Требуется честно исключить найденные дубликаты, сузить вклад и записать limitations. При сильном overlap сохранить engineering scope; глобальный pivot темы выносится пользователю конкретным предложением, а не делается молча. CP02 hosting rights могут остаться pending при разрешенной локальной работе; CP03 engine fidelity pending блокирует scientific claims, но не controlled-worker тесты. CP10 negative outcome не блокирует CP11/CP12, если протокол выполнен и результат проверяем.

## 18. Определение завершения

Проект v1 закончен, когда все MUST требования приняты, CP00–CP12 имеют evidence, новый workspace выполняет основной путь без CFB, реальные upstream/adapter fidelity подтверждены, durable runs и storage gates работают, sensitivity/cohort воспроизводятся, два исследования имеют честные материалы и ни один защищенный patient outcome не раскрыт. Статья B может закончиться выводом об отсутствии установленной смены ранжирования или недостаточной numerical resolution; это корректный результат при выполненном дизайне.

Не требуются публикация/принятие журналом, клиническая эффективность, победа над persistence, готовность к публичному hosting или реализация LATER. Нельзя закрыть MUST ссылкой на красивый UI, исторический test run, mock-only output или будущий roadmap. Если full study не помещается в согласованный budget, software release допускается только с явно отдельным статусом scientific study incomplete; весь проект по этому ТЗ завершенным не объявлять.

## 19. Риски и решения

| Риск | Признак | Обязательное действие |
|---|---|---|
| Повтор существующего вклада | У ближайшей работы те же question/methods/outputs | Уточнить claim на CP01 до большой разработки |
| Adapter отличается от author workflow | F1/F2 не пройдены, CT/cropping/version mismatch | Диагностировать по одному фактору, не снижать допуски |
| Не хватает диска | Estimate превышает quota/free reserve | Scalar-first, selected frames, explicit cleanup; без auto-download |
| Слишком дорогая серия | Minimum design не проходит pilot budget | Feasibility report, независимые работы, согласовать бюджет |
| Численная ошибка меняет ranking | Effect внутри epsilon | Unresolved conclusion, refinement по frozen policy |
| Непроверенные биологические ranges | Нет источника | Явно assumption; не называть population distribution |
| Загрязнение evaluation | Изменение candidates после outputs | Новая версия, старые results сохраняются, никакой ретроспективной победы |
| Queue остается running навсегда | Stale lease, потерян worker | interrupted/retry; ownership проверяется |
| Продолжение анатомических дебрей | Изменяются registration/atlas вместо lab | Прекратить unrelated scope, вернуться к текущему CP |
| Заявление clinical correctness по синтетике | UI/manuscript говорит об эффективности лечения | Исправить claim до release |

## 20. Изменения и передача следующей нейросети

Текущее поручение — подготовка ТЗ. Оно не является поручением реализовать или опубликовать систему прямо сейчас. При последующем поручении реализации использовать [04_AGENT_START.md](04_AGENT_START.md) и [05_PROGRESS_TEMPLATE.md](05_PROGRESS_TEMPLATE.md).

При запуске нового рабочего чата: прочитать ТЗ, progress, requirements; проверить Git и существующие пользовательские изменения; выбрать первый непринятый CP; выполнить минимальный сквозной результат; запустить нужные проверки; обновить evidence и progress; перейти к следующему CP. Завершенные задачи не выполнять заново без новой причины. Промежуточные отчеты сообщают факты и следующий проверяемый результат, а не повторяют весь roadmap.

ADR нужен для изменения очереди/хранилища/engine interfaces/численной семантики; не для каждого имени функции. Change request нужен для изменения обязательного scope, модели, dataset cohort, scientific thresholds, budgets или release target. Содержит причину, affected IDs, alternatives, verification и влияние на статьи. Научные protocol changes после freeze всегда получают новый ID/hash.

Следующее приложение является нормативным реестром атомарных требований. Буквенные префиксы групп: GOV управление, SRC источники, ENG движок, DAT данные, DOM контракты, JOB выполнение, STO хранение, API transport, UI интерфейс, NUM численная корректность, ANA анализ, SCI исследование, NFR качество, TST проверки, PUB публикационные материалы. Идентификатор остается стабильным при уточнении текста; удаление фиксируется changelog.


## 21. Атомарный порядок внедрения для исполнителя

Каждая задача ниже завершается reviewable diff и свидетельством, а не описанием намерений. До CP00 проект не изменять. Пакет требований подготовлен 06.11.2026; актуальность источников проверялась 05–06.11.2026. Точный final scope привязан к версиям, не к плавающему latest.

### CP00. Baseline и единая точка входа

- CP00.1. Проверить cwd, status/branch/HEAD, instructions. Записать paths и локальные differences. Не предполагать наличие старых data/results.
- CP00.2. Составить inventory существующих reusable components и protected scientific files. Сравнить с разделом 3 этого ТЗ.
- CP00.3. Разместить принятый пакет в docs/lab, связать README и старое ТЗ. Сохранить historical protocols.
- CP00.4. Запустить baseline checks в совместимом окружении. Отдельно зарегистрировать pre-existing failures и infrastructure errors.
- Выход: BASELINE.md, PROTECTED_ARTIFACTS.md, initialized progress; никакого lab solver/UI пока не требуется.

### CP01. Актуальность до новой большой разработки

- CP01.1. Открыть первоисточники S01, S04 и полный текст S05; проверить близкие references/citing works по доступным поисковым средствам. Сохранить query log.
- CP01.2. Заполнить comparison matrix по функциям, данным, model assumptions, uncertainty, reproducibility, budget и experimental claims.
- CP01.3. Для каждого proposed claim записать аналог, проверяемое отличие и конкретную таблицу/эксперимент.
- CP01.4. Зафиксировать две статьи с самостоятельными questions и таблицами; исключить claims о новом PDE, первенстве UQ и доказанной клинической эффективности.
- Выход: PRIMARY_SOURCE_MATRIX.md, CONTRIBUTION_MATRIX.md, PUBLICATION_PLAN.md. Если novelty остается uncertain, это явно записано; software implementation не объявляется новым математическим методом.

### CP02. Движок и данные без тяжелой коллекции

- CP02.1. Проверить сохраненные environments автора до новой установки. Создать изолированное engine environment только при необходимости.
- CP02.2. Зафиксировать source, license/use status и фактические resolved packages. Установку CPU/GPU выбирать по pinned requirements и измеримым ресурсам.
- CP02.3. Реализовать preparation CLI с dry-run, whitelist, expected bytes, interrupted receipt и checksum verification.
- CP02.4. Подготовить только HGG_demo_001. Разделить data source, author baseline и observation roles. Не включать licensed volumes в deliverable archive.
- Выход: engine descriptor, environment/source manifests, prepared case receipt. UI каталог может оставаться только тестовой fixture до CP06.

### CP03. Faithful adapter и pilot

- CP03.1. Выполнить direct author workflow с точными preprocessing/RT/CT/solver settings и записать baseline metrics.
- CP03.2. Реализовать новый adapter, передающий все необходимые semantics; не расширять старый CFB adapter несовместимыми параметрами.
- CP03.3. Сравнить actual trajectory на common frames по F1/F2 и geometry. Разбирать mismatch отдельно: версии → preprocessing → units → events → precision → solver.
- CP03.4. Выполнить analytic/event tests, time/spatial pilot и storage/RAM measurement. Зафиксировать budget profile и feasible output times.
- CP03.5. Записать exact adapter API и full author reproduction limitations. Не запускать main scientific series.
- CP03.6. Подготовить synthetic forecast contract: первые пять author visits разрешены для fit, последующие — только evaluator; проверить доступность pinned optimizer. Полный демонстрационный расчет выполняется на CP10 после freeze.
- Выход: REFERENCE_RESULT.md, measured artifacts и PILOT_PROFILE.json. Если F1/F2 не пройдены, отметить CP03 pending; продолжать только независимые controlled-worker tasks.

### CP04. Контракты и storage

- CP04.1. Добавить typed domain models и validation: engine/case/scenario/plan/result/study.
- CP04.2. Реализовать canonical identity, normalized units и mutation tests. Проверить hash stability вне local absolute paths.
- CP04.3. Создать SQLite migrations, repositories и atomic result writer/loader. Добавить crash/corruption tests.
- CP04.4. Добавить lightweight endpoints и capability readiness без CFB. Согласовать OpenAPI/TypeScript types.
- Выход: domain/storage/API tests; еще не показывать недоступные функции как готовые.

### CP05. Надежное выполнение

- CP05.1. Реализовать transactional claim/lease и bounded supervisor с concurrency=1.
- CP05.2. Добавить idempotent submit, cancellation, timeout, retry и interrupted recovery. Ownership проверять token, не PID alone.
- CP05.3. Проверить два clients, duplicate submit, stale heartbeat, forceful stop своего process tree и late update race.
- CP05.4. Подключить реальный adapter и завершить один validated run через новый executor.
- Выход: JOB_FAILURE_MATRIX.md и реальный run receipt. Не создавать отдельный executor для будущего Morris/cohort.

### CP06. Первый законченный пользовательский путь

- CP06.1. Отделить lab startup от App patient fetch. Добавить доступный каталог и honest empty/error states.
- CP06.2. Реализовать exact-value scenario editor, immutable save, diff/validation/estimate preview.
- CP06.3. Реализовать submit/status/cancel/retry page. Обработать draft preservation и request races.
- CP06.4. Подключить scalar graph, saved-time 2D и 3D с общим frame identity; WebGL fallback.
- CP06.5. Выполнить browser smoke на реальном backend без CFB. Проверить 1366×768 и keyboard path.
- Выход: пользователь реально получает и просматривает несколько времен рассчитанного случая. Далее улучшать только дефекты этого пути, не создавать новый визуальный shell.

### CP07. Сравнение и воспроизведение

- CP07.1. Реализовать compatibility checker и paired metrics со знаком delta и epsilon.
- CP07.2. Сделать synchronized comparison views и полный scientific diff.
- CP07.3. Реализовать compact export, bounded import и fresh-workspace replay. Данные upstream готовятся отдельно по источнику.
- CP07.4. Реализовать storage overview, quota enforcement, cleanup preview и pinned protection.
- Выход: сравнение двух реальных scenarios и воспроизведение вне первоначального workspace. Никакой claims об ускорении без matched measurement.

### CP08. Чувствительность и виртуальные subjects

- CP08.1. Реализовать local differences с h/h2 и analytic reference. Выделить warnings для nonsmooth endpoints.
- CP08.2. Интегрировать pinned Morris sampler/analyzer. Sample matrix immutable до вычислений.
- CP08.3. Реализовать seeded subject generator, common scenarios per subject и all-planned outcomes table.
- CP08.4. Подключить единый Study wizard и progress. Сначала controlled small fixtures, затем ограниченная real-engine mini-series.
- Выход: actual metrics и reproducible seeded matrices. Autograd, Sobol и adaptive sampling не добавлять в эту стадию.

### CP09. Протоколы перед основными результатами

- CP09.1. Зафиксировать S-A engineering benchmark и S-B robustness question/endpoint/candidates/ranges/epsilon/failures.
- CP09.2. Заполнить scientific protocol template; все required fields должны иметь значения и units, а assumptions — labels.
- CP09.3. Выбрать design по feasibility ladder с 30% cost reserve. Сохранить планируемые calls и disk bytes.
- CP09.4. Проверить leakage boundaries и subjects seed split. В frozen protocol включить resolved sample matrices.
- CP09.5. Сохранить protocol hashes и evidence до evaluation outputs. После freeze не менять rules в этой версии.
- Выход: два validated frozen protocols. Числа, полученные в pilot/development, не входят в locked evaluation estimate.

### CP10. Выполнение исследования

- CP10.1. Запустить S-A reliability/performance measurements, сохранить hardware и все попытки.
- CP10.2. Выполнить S-B по frozen matrix; retry transient errors без замены subjects/candidates.
- CP10.3. Проверить full denominators, missing outcomes, unresolved rankings и source hashes.
- CP10.4. Выполнить deterministic analysis command и получить figures/tables. Нулевой эффект не является причиной нового sweep.
- CP10.5. Выполнить один заранее заданный longitudinal synthetic forecast с fit по первым пяти visits и оценкой последующих; сохранить persistence и author-fixed-parameter comparators без настройки по будущим outcomes.
- Выход: STUDY_A_RESULT.md, STUDY_B_RESULT.md, immutable rows и analysis provenance. При нарушенном protocol записать invalid/incomplete, не success.

### CP11. Публикационные материалы

- CP11.1. Подготовить структуру и заполненные Methods/Results A с matched benchmark tables и software limitations.
- CP11.2. Подготовить структуру и заполненные Methods/Results B с primary estimand, actual effects и uncertainty interpretation.
- CP11.3. Создать claim→artifact map, citations, figure captions, contribution/AI disclosure и code/data availability.
- CP11.4. Проверить независимость двух работ и отсутствие переписывания старого clinical negative result.
- Выход: проверяемые research materials. Выбор журнала и submission не выполняются автоматически.

### CP12. Release

- CP12.1. Пройти новый workspace setup и end-to-end baseline/replay по пользовательской инструкции.
- CP12.2. Выполнить meaningful full checks: Python, lint, frontend build, browser, pinned engine, scientific analysis.
- CP12.3. Проверить GitHub Actions точного commit, licenses/assets, protected files diff, acceptance matrix.
- CP12.4. Создать versioned release package, changelog, known limits и final progress. Не включать raw upstream assets без прав.
- Выход: accepted software и accepted research evidence либо честно раздельные статусы. Публикация в журнале не симулируется статусом release.

## 22. Поля редактора и точные правила

Таблица задает контракт UX/validation. Author baseline values получаются из проверенного case/setup, не выдаются за неизвестные generative truth. Значения k=0.05/day и D=0.025 mm²/day из tutorial являются author setup, пока не доказан иной origin.

| Поле | Тип и единица | Правило | Поведение при ошибке |
|---|---|---|---|
| Название | UTF-8 1–120 символов | Trim внешних пробелов, scientific hash не меняется | Ошибка у поля |
| Комментарий | UTF-8 ≤2000 символов | Plain text, без HTML execution | Escaped display |
| Case/version | Registry ref | Только prepared compatible version | Run blocked, missing assets |
| rho/k | finite float, 1/day | ≥0, upper bound из engine+resource profile | 422 parameter field |
| D/d | finite float, mm²/day | ≥0, upper bound из engine+resource profile | 422 parameter field |
| alpha_RT | finite float, 1/Gy | ≥0, поддержанное engine значение | 422 parameter field |
| alpha/beta | finite float, Gy | >0; beta вычисляется/передается по engine contract | 422 parameter field |
| CT sensitivity | finite float, engine unit | Только при verified CT capability | Control hidden/unavailable |
| CT decay | finite float, 1/day если подтверждено | >0 по pinned contract | No silent unit conversion |
| Event time | finite float, days | В [0,horizon], sorted; origin виден | Ошибка row/time |
| Event dose | finite positive float | Unit зависит от modality, RT=Gy | Ошибка row/dose |
| Horizon | finite float, days | >0 и ≤profile max | Preview blocked |
| Solver dt | finite positive float, days | Engine supported, не равен нулю после conversion | Preview blocked |
| Scalar interval | finite positive float, days | Start/end включены, total point count bounded | Estimate объясняет limit |
| Dense frames | список finite times | Unique, sorted, [0,horizon], default ≤21 | Ошибка конкретного index |
| Seed | uint32 | Сохраняется в plan; stochastic components используют явно | Ошибка поля |
| Device/precision | enum | Только descriptor supported values | Unsupported rejected |
| Endpoint | enum+unit+direction | Supported metric; threshold явно задан при необходимости | Freeze blocked |
| Resource limits | integers bytes/seconds | Server caps сильнее client values | budget error |

Frontend показывает не только min/max, но и тип ограничения: mathematical, engine-supported, numerical или engineering budget. Допустимый диапазон UI не называется доверительным интервалом биологии. Установка default не является литературной оценкой.

## 23. Пример контрактов без фиктивных результатов

Ниже illustrations будущего API. Они не являются готовыми действующими endpoints текущего репозитория. Значения case_id и hash placeholders иллюстративны и проходят реальную регистрацию при реализации.

```json
{
  "case_id": "HGG_demo_001",
  "case_version": "verified-version",
  "engine_id": "tumortwin-pinned",
  "mode": "scenario_simulation",
  "name": "Копия авторского сценария",
  "parameter_overrides": {"rho_per_day": 0.05},
  "treatment_ref": "author-baseline-events",
  "horizon_days": 225.0,
  "solver": {"method": "rk4", "dt_days": 0.5},
  "outputs": {"scalar_interval_days": 0.5, "field_times_days": [0, 45, 90, 135, 180, 225]},
  "seed": 1105
}
```

Server canonical plan дополняет все defaults explicit values, resolves treatment_ref в exact event table и сохраняет hashes. Нельзя восстановить научный результат по ссылке на изменяемый «текущий baseline».

```json
{
  "code": "resource_budget_exceeded",
  "message_ru": "Планируемые кадры превышают лимит хранения запуска",
  "field_errors": [{"field": "outputs.field_times_days", "message_ru": "Уменьшите число сохраняемых кадров"}],
  "retryable": false,
  "request_id": "server-generated-id",
  "details_ref": "diagnostic-reference"
}
```

Данные в error response должны отражать конкретное измерение/оценку. Не копировать текст ошибки quota при иной причине. Если расчет already failed, polling возвращает RunAttempt с code/reason, а не невалидный HTTP response.

## 24. Приемочные сценарии Given When Then

**AC01 No CFB:** Given CFB_ROOT и ATLAS_ROOT отсутствуют; When открыта лаборатория; Then каталог и preparation state доступны, а patient/atlas loader не вызван.

**AC02 Invalid field:** Given baseline draft; When rho=NaN или dt=0; Then server validation возвращает 422, очередь пуста, draft сохранен.

**AC03 Idempotency:** Given один valid plan; When два клиента одновременно submit с одинаковым key; Then существует ровно одна попытка и оба получают один ID.

**AC04 Cancel race:** Given running task; When cancel запрошен одновременно с поздним worker progress; Then terminal cancelled/interrupted сохраняется и succeeded не появляется без допустимого transition.

**AC05 Restart:** Given worker потерян при restart; When lease stale; Then attempt interrupted и retry имеет новый ID/attempt, старый log доступен.

**AC06 Time race:** Given frame t=0 показан; When запрошены t=45 затем t=90 и ответы пришли в обратном порядке; Then виден t=90, старый ответ игнорируется.

**AC07 Corruption:** Given succeeded artifact; When frame bytes изменены; Then loader сообщает checksum error, cache не считается verified и повторный run не получает corrupt reuse.

**AC08 Disk:** Given free space ниже reserve; When начата запись; Then run завершается disk_limit, старые publication results не удалены.

**AC09 Pair compatibility:** Given два разных initial state hashes; When обычное treatment comparison запрошено; Then 409 и объяснение; пользователь не получает ложную paired delta.

**AC10 Export/replay:** Given compact archive без restricted assets; When новый workspace подготовил те же licensed inputs и повторил plan; Then replay report сверяет endpoints с frozen tolerances.

**AC11 Missing pair:** Given один failed child из N subjects; When primary summary рассчитана; Then planned N, complete-pair N и reason присутствуют, replacement subject не создан.

**AC12 Negative result:** Given evaluation не выявил resolved reversals; When анализ завершен; Then сохранен нулевой/неопределенный результат по заранее заданному rule без нового parameter sweep.

**AC13 Frozen protocol:** Given frozen S-B; When UI меняет range; Then создается новый draft, прежний execution immutable и не пересчитывается как та же серия.

**AC14 3D fallback:** Given WebGL unavailable; When result открыт; Then scalar graph и 2D работают, 3D объясняет ограничение.

**AC15 Legacy protection:** Given lab smoke и старые frozen configs; When новый release собран; Then protected hashes/semantics сохранены и закрытые outcomes не прочитаны.

## 25. Макет основного рабочего экрана

```text
GBM Research Lab        Случай HGG_demo_001       Синтетический исследовательский случай
Случаи                 Сценарий Авторский baseline v1       Расчет завершен
Сценарии               [Создать копию] [Сравнить] [Экспорт]
Запуски                -----------------------------------------------------------
Сравнение              График расчетного burden       Единица и метод     [i]
Исследования           RT/CT события                  Выбран день 90
Хранилище              -----------------------------------------------------------
Методика               [Назад] [Play] [Вперед]    Сохраненные кадры 0 ... 225 дней
                       -----------------------------------------------------------
Данные пациентов       [2D срезы и плотность]           [3D / состояние fallback]
                       Plane | Slice | Location         Layers | Reset camera
                       -----------------------------------------------------------
                       Метрики | Сценарий | Допущения | Диагностика
```

Это схема информационной структуры, а не поручение заменить существующий дизайн. Воспроизвести привычные поверхности, размеры и цвета проекта, обеспечив читаемость. Пример не разрешает выводить вымышленные scalar values или статус завершения без реального run.


## 26. Нормативный реестр атомарных требований

Всего **256 MUST требований**. Каждому соответствует AT-ID и evidence target. В этом пакете все пункты имеют статус pending: здесь создана спецификация, реализация и приемочные тесты будущей лаборатории не выполнены. IDs являются заданиями для тестов/проверок, а не утверждением о наличии одноименных тестовых функций.

### GOV Управление и исходное состояние

**GOV-001 — Зафиксировать фактические HEAD, ветку и dirty status перед изменениями.**

Checkpoint: CP00. Приоритет: MUST. Проверка: manual.

Приемка AT-GOV-001: BASELINE.md содержит значения из Git и время проверки.

Свидетельство: `CP00/evidence/GOV-001`; command/result/hash либо manual review record.

**GOV-002 — Прочитать применимые AGENTS.md до реализации.**

Checkpoint: CP00. Приоритет: MUST. Проверка: manual.

Приемка AT-GOV-002: BASELINE.md перечисляет прочитанные файлы и применимые ограничения.

Свидетельство: `CP00/evidence/GOV-002`; command/result/hash либо manual review record.

**GOV-003 — Составить список защищенных старых протоколов и результатов.**

Checkpoint: CP00. Приоритет: MUST. Проверка: manual.

Приемка AT-GOV-003: PROTECTED_ARTIFACTS.md перечисляет frozen configs и scientific reports.

Свидетельство: `CP00/evidence/GOV-003`; command/result/hash либо manual review record.

**GOV-004 — Сохранить пользовательские изменения при внедрении ТЗ.**

Checkpoint: CP00. Приоритет: MUST. Проверка: manual.

Приемка AT-GOV-004: Diff не удаляет и не перезаписывает unrelated changes.

Свидетельство: `CP00/evidence/GOV-004`; command/result/hash либо manual review record.

**GOV-005 — Связать старое ТЗ с версией 2.0 без удаления истории.**

Checkpoint: CP00. Приоритет: MUST. Проверка: manual.

Приемка AT-GOV-005: Старый документ содержит ссылку на действующую спецификацию.

Свидетельство: `CP00/evidence/GOV-005`; command/result/hash либо manual review record.

**GOV-006 — Инвентаризировать оставшиеся локальные данные без загрузки коллекций.**

Checkpoint: CP00. Приоритет: MUST. Проверка: manual.

Приемка AT-GOV-006: В BASELINE.md отдельно отмечены absent, present и unverified assets.

Свидетельство: `CP00/evidence/GOV-006`; command/result/hash либо manual review record.

**GOV-007 — Зарегистрировать audit baseline отдельно от новых результатов.**

Checkpoint: CP00. Приоритет: MUST. Проверка: manual.

Приемка AT-GOV-007: Исторический прогон 571 теста не обозначен приемкой лаборатории.

Свидетельство: `CP00/evidence/GOV-007`; command/result/hash либо manual review record.

**GOV-008 — Использовать первый непринятый checkpoint как текущую задачу.**

Checkpoint: CP00. Приоритет: MUST. Проверка: manual.

Приемка AT-GOV-008: Progress содержит один current_checkpoint и его зависимости.

Свидетельство: `CP00/evidence/GOV-008`; command/result/hash либо manual review record.

**GOV-009 — Сохранять историю принятия и изменений требований.**

Checkpoint: CP12. Приоритет: MUST. Проверка: manual.

Приемка AT-GOV-009: Для каждого изменения есть version, affected IDs и причина.

Свидетельство: `CP12/evidence/GOV-009`; command/result/hash либо manual review record.

**GOV-010 — Не открывать защищенные reserve/holdout при lab tests.**

Checkpoint: CP12. Приоритет: MUST. Проверка: integration.

Приемка AT-GOV-010: Regression spy фиксирует ноль вызовов загрузчика закрытых cohorts.

Свидетельство: `CP12/evidence/GOV-010`; command/result/hash либо manual review record.

### SRC Источники и самостоятельный вклад

**SRC-001 — Зафиксировать поисковые запросы и дату литературной проверки.**

Checkpoint: CP01. Приоритет: MUST. Проверка: manual.

Приемка AT-SRC-001: SEARCH_LOG содержит запрос, источник и результат поиска.

Свидетельство: `CP01/evidence/SRC-001`; command/result/hash либо manual review record.

**SRC-002 — Разобрать опубликованный TumorTwin как ближайшую software работу.**

Checkpoint: CP01. Приоритет: MUST. Проверка: manual.

Приемка AT-SRC-002: Матрица содержит проверенные capabilities и границу собственного вклада.

Свидетельство: `CP01/evidence/SRC-002`; command/result/hash либо manual review record.

**SRC-003 — Разобрать полную работу о risk-aware HGG twin 2023 года.**

Checkpoint: CP01. Приоритет: MUST. Проверка: manual.

Приемка AT-SRC-003: Матрица сопоставляет cohort, uncertainty и treatment comparison.

Свидетельство: `CP01/evidence/SRC-003`; command/result/hash либо manual review record.

**SRC-004 — Проверить полный текст Pash et al. до окончательного novelty claim.**

Checkpoint: CP01. Приоритет: MUST. Проверка: manual.

Приемка AT-SRC-004: В матрице указан full-text status; недоступное содержание отмечено unknown.

Свидетельство: `CP01/evidence/SRC-004`; command/result/hash либо manual review record.

**SRC-005 — Привязать каждое заявленное отличие к проверяемому эксперименту.**

Checkpoint: CP01. Приоритет: MUST. Проверка: manual.

Приемка AT-SRC-005: CONTRIBUTION_MATRIX содержит claim, baseline и artifact target.

Свидетельство: `CP01/evidence/SRC-005`; command/result/hash либо manual review record.

**SRC-006 — Ограничить выводы клинического характера доступными данными.**

Checkpoint: CP01. Приоритет: MUST. Проверка: manual.

Приемка AT-SRC-006: Claims ledger не содержит доказанной клинической эффективности по синтетике.

Свидетельство: `CP01/evidence/SRC-006`; command/result/hash либо manual review record.

**SRC-007 — Разделить основные результаты статей A и B.**

Checkpoint: CP01. Приоритет: MUST. Проверка: manual.

Приемка AT-SRC-007: PUBLICATION_PLAN перечисляет самостоятельные questions и primary tables.

Свидетельство: `CP01/evidence/SRC-007`; command/result/hash либо manual review record.

**SRC-008 — Записать statement of need для исследователя.**

Checkpoint: CP01. Приоритет: MUST. Проверка: manual.

Приемка AT-SRC-008: Документ объясняет задачу, alternatives и причину отдельной среды.

Свидетельство: `CP01/evidence/SRC-008`; command/result/hash либо manual review record.

**SRC-009 — Описать условия использования upstream кода и demo assets.**

Checkpoint: CP02. Приоритет: MUST. Проверка: manual.

Приемка AT-SRC-009: LICENSE_AND_DATA_USE содержит источники и разрешенные способы использования.

Свидетельство: `CP02/evidence/SRC-009`; command/result/hash либо manual review record.

**SRC-010 — Отделить публичный hosting от приемки локальной среды.**

Checkpoint: CP02. Приоритет: MUST. Проверка: manual.

Приемка AT-SRC-010: Неясный hosting status не запрещает разрешенный local workflow.

Свидетельство: `CP02/evidence/SRC-010`; command/result/hash либо manual review record.

### ENG Движок и эталон

**ENG-001 — Закрепить upstream commit в engine descriptor.**

Checkpoint: CP02. Приоритет: MUST. Проверка: unit.

Приемка AT-ENG-001: Descriptor содержит bedf90a6d47ba48cf5cdb25901967d84730061d1.

Свидетельство: `CP02/evidence/ENG-001`; command/result/hash либо manual review record.

**ENG-002 — Проверять фактический source fingerprint установленного движка.**

Checkpoint: CP02. Приоритет: MUST. Проверка: integration.

Приемка AT-ENG-002: Изменение source при неизменном marker обнаруживается проверкой.

Свидетельство: `CP02/evidence/ENG-002`; command/result/hash либо manual review record.

**ENG-003 — Сохранять точные версии resolved engine dependencies.**

Checkpoint: CP02. Приоритет: MUST. Проверка: integration.

Приемка AT-ENG-003: Environment manifest содержит Python, Torch, NumPy и solver versions.

Свидетельство: `CP02/evidence/ENG-003`; command/result/hash либо manual review record.

**ENG-004 — Изолировать engine environment от основного backend.**

Checkpoint: CP02. Приоритет: MUST. Проверка: integration.

Приемка AT-ENG-004: Backend imports работают без установленного Torch в app environment.

Свидетельство: `CP02/evidence/ENG-004`; command/result/hash либо manual review record.

**ENG-005 — Публиковать поддерживаемые параметры через descriptor.**

Checkpoint: CP02. Приоритет: MUST. Проверка: unit.

Приемка AT-ENG-005: Unsupported key отклоняется до queue и отсутствует в editor controls.

Свидетельство: `CP02/evidence/ENG-005`; command/result/hash либо manual review record.

**ENG-006 — Публиковать поддерживаемые treatment modalities.**

Checkpoint: CP02. Приоритет: MUST. Проверка: engine.

Приемка AT-ENG-006: CT нельзя silently omit при faithful reproduction с CT input.

Свидетельство: `CP02/evidence/ENG-006`; command/result/hash либо manual review record.

**ENG-007 — Получить эталон отдельным прямым upstream запуском.**

Checkpoint: CP03. Приоритет: MUST. Проверка: engine.

Приемка AT-ENG-007: Reference receipt содержит отдельную команду и независимые output hashes.

Свидетельство: `CP03/evidence/ENG-007`; command/result/hash либо manual review record.

**ENG-008 — Воспроизвести author preprocessing в reproduction режиме.**

Checkpoint: CP03. Приоритет: MUST. Проверка: engine.

Приемка AT-ENG-008: Сравнение фиксирует те же visits, cropping и initial density.

Свидетельство: `CP03/evidence/ENG-008`; command/result/hash либо manual review record.

**ENG-009 — Возвращать trajectory с фактическими временами.**

Checkpoint: CP03. Приоритет: MUST. Проверка: engine.

Приемка AT-ENG-009: Adapter outputs содержат более одного distinct time и соответствующие fields.

Свидетельство: `CP03/evidence/ENG-009`; command/result/hash либо manual review record.

**ENG-010 — Сохранять полную физическую геометрию author case.**

Checkpoint: CP03. Приоритет: MUST. Проверка: engine.

Приемка AT-ENG-010: Origin и orientation не заменены diagonal spacing-only affine.

Свидетельство: `CP03/evidence/ENG-010`; command/result/hash либо manual review record.

**ENG-011 — Запускать CPU mode без требования GPU.**

Checkpoint: CP03. Приоритет: MUST. Проверка: engine.

Приемка AT-ENG-011: Author case завершается на документированном CPU environment.

Свидетельство: `CP03/evidence/ENG-011`; command/result/hash либо manual review record.

**ENG-012 — Измерить peak memory и wall time pilot.**

Checkpoint: CP03. Приоритет: MUST. Проверка: engine.

Приемка AT-ENG-012: PILOT_PROFILE содержит hardware и measured resource values.

Свидетельство: `CP03/evidence/ENG-012`; command/result/hash либо manual review record.

**ENG-013 — Отделять unsupported gradient capability от finite differences.**

Checkpoint: CP03. Приоритет: MUST. Проверка: unit.

Приемка AT-ENG-013: Descriptor сообщает autograd=false при detached adapter.

Свидетельство: `CP03/evidence/ENG-013`; command/result/hash либо manual review record.

**ENG-014 — Запускать worker через разрешенные argv без shell execution.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-ENG-014: Пользовательский executable/module не принимается API.

Свидетельство: `CP05/evidence/ENG-014`; command/result/hash либо manual review record.

**ENG-015 — Поддержать pinned upstream optimizer для author longitudinal case.**

Checkpoint: CP03. Приоритет: MUST. Проверка: engine.

Приемка AT-ENG-015: Проверка fit contract использует первые пять visits и не требует новой матмодели.

Свидетельство: `CP03/evidence/ENG-015`; command/result/hash либо manual review record.

### DAT Подготовка данных

**DAT-001 — Подготавливать только явно выбранный author case.**

Checkpoint: CP02. Приоритет: MUST. Проверка: integration.

Приемка AT-DAT-001: Acquisition receipt не содержит CFB, Burdenko или atlas files.

Свидетельство: `CP02/evidence/DAT-001`; command/result/hash либо manual review record.

**DAT-002 — Показывать expected download size перед загрузкой.**

Checkpoint: CP02. Приоритет: MUST. Проверка: integration.

Приемка AT-DAT-002: CLI dry-run выводит whitelisted files и total bytes либо unknown reason.

Свидетельство: `CP02/evidence/DAT-002`; command/result/hash либо manual review record.

**DAT-003 — Создавать immutable manifest подготовленного случая.**

Checkpoint: CP02. Приоритет: MUST. Проверка: integration.

Приемка AT-DAT-003: Повтор записи иной версии не изменяет старый manifest.

Свидетельство: `CP02/evidence/DAT-003`; command/result/hash либо manual review record.

**DAT-004 — Проверять checksum каждого подготовленного файла.**

Checkpoint: CP02. Приоритет: MUST. Проверка: integration.

Приемка AT-DAT-004: Измененный fixture переводит case в corrupt и блокирует run.

Свидетельство: `CP02/evidence/DAT-004`; command/result/hash либо manual review record.

**DAT-005 — Сохранять provenance исходного case.**

Checkpoint: CP02. Приоритет: MUST. Проверка: unit.

Приемка AT-DAT-005: Manifest содержит source URI, pinned ref и acquisition timestamp.

Свидетельство: `CP02/evidence/DAT-005`; command/result/hash либо manual review record.

**DAT-006 — Различать fitted, assumed и generative parameters.**

Checkpoint: CP02. Приоритет: MUST. Проверка: unit.

Приемка AT-DAT-006: Case metadata сохраняет origin каждого известного parameter.

Свидетельство: `CP02/evidence/DAT-006`; command/result/hash либо manual review record.

**DAT-007 — Проверять согласованность shapes связанных volumes.**

Checkpoint: CP02. Приоритет: MUST. Проверка: unit.

Приемка AT-DAT-007: Несовпадающая маска отклоняется до model execution.

Свидетельство: `CP02/evidence/DAT-007`; command/result/hash либо manual review record.

**DAT-008 — Проверять nonsingular affine и physical units.**

Checkpoint: CP02. Приоритет: MUST. Проверка: unit.

Приемка AT-DAT-008: Singular affine и unknown units требуют явного разрешенного преобразования.

Свидетельство: `CP02/evidence/DAT-008`; command/result/hash либо manual review record.

**DAT-009 — Оставлять incomplete download недоступным для расчетов.**

Checkpoint: CP02. Приоритет: MUST. Проверка: integration.

Приемка AT-DAT-009: Прерванная подготовка не создает available case.

Свидетельство: `CP02/evidence/DAT-009`; command/result/hash либо manual review record.

**DAT-010 — Не затирать пользовательский файл при hash mismatch.**

Checkpoint: CP02. Приоритет: MUST. Проверка: integration.

Приемка AT-DAT-010: Оригинальный файл сохраняется, ошибка указывает путь и expected hash.

Свидетельство: `CP02/evidence/DAT-010`; command/result/hash либо manual review record.

**DAT-011 — Различать synthetic case и реальные пациентские записи.**

Checkpoint: CP06. Приоритет: MUST. Проверка: unit.

Приемка AT-DAT-011: HGG_demo_001 не получает фиктивный CFB patient_id.

Свидетельство: `CP06/evidence/DAT-011`; command/result/hash либо manual review record.

**DAT-012 — Сохранять список visits использованных author reproduction.**

Checkpoint: CP03. Приоритет: MUST. Проверка: engine.

Приемка AT-DAT-012: Отчет содержит observation roles и предупреждение о retrospective reproduction.

Свидетельство: `CP03/evidence/DAT-012`; command/result/hash либо manual review record.

**DAT-013 — Применять observation cutoff в заявленном forecast experiment.**

Checkpoint: CP09. Приоритет: MUST. Проверка: integration.

Приемка AT-DAT-013: Spy evaluator target не читается initialization/calibration кодом.

Свидетельство: `CP09/evidence/DAT-013`; command/result/hash либо manual review record.

**DAT-014 — Открывать lab при полностью отсутствующих CFB directories.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-DAT-014: Browser smoke достигает case catalog без patient loader calls.

Свидетельство: `CP06/evidence/DAT-014`; command/result/hash либо manual review record.

**DAT-015 — Определять forecast crop без future observation arrays.**

Checkpoint: CP09. Приоритет: MUST. Проверка: integration.

Приемка AT-DAT-015: Spy тест обнаруживает ноль чтений future ADC/ROI при crop/init/fit.

Свидетельство: `CP09/evidence/DAT-015`; command/result/hash либо manual review record.

### DOM Доменные контракты

**DOM-001 — Создавать серверный immutable snapshot научного сценария.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-DOM-001: Изменение draft после POST не меняет существующий RunPlan.

Свидетельство: `CP04/evidence/DOM-001`; command/result/hash либо manual review record.

**DOM-002 — Присваивать новую версию при scientific edit.**

Checkpoint: CP04. Приоритет: MUST. Проверка: unit.

Приемка AT-DOM-002: Старый ScenarioVersion byte-identical после редактирования.

Свидетельство: `CP04/evidence/DOM-002`; command/result/hash либо manual review record.

**DOM-003 — Вычислять canonical scientific hash независимо от display name.**

Checkpoint: CP04. Приоритет: MUST. Проверка: unit.

Приемка AT-DOM-003: Изменение name сохраняет scientific hash.

Свидетельство: `CP04/evidence/DOM-003`; command/result/hash либо manual review record.

**DOM-004 — Менять scientific hash при изменении dose или timing.**

Checkpoint: CP04. Приоритет: MUST. Проверка: unit.

Приемка AT-DOM-004: Mutation fixture получает другой hash.

Свидетельство: `CP04/evidence/DOM-004`; command/result/hash либо manual review record.

**DOM-005 — Учитывать input geometry digest в научной идентичности.**

Checkpoint: CP04. Приоритет: MUST. Проверка: unit.

Приемка AT-DOM-005: Иной affine меняет scientific hash при том же array shape.

Свидетельство: `CP04/evidence/DOM-005`; command/result/hash либо manual review record.

**DOM-006 — Учитывать численно значимые engine и solver versions.**

Checkpoint: CP04. Приоритет: MUST. Проверка: unit.

Приемка AT-DOM-006: Иная numerical version исключает exact cache reuse.

Свидетельство: `CP04/evidence/DOM-006`; command/result/hash либо manual review record.

**DOM-007 — Разделять scientific hash и execution/output identity.**

Checkpoint: CP04. Приоритет: MUST. Проверка: unit.

Приемка AT-DOM-007: Изменение retention policy отражается в execution identity.

Свидетельство: `CP04/evidence/DOM-007`; command/result/hash либо manual review record.

**DOM-008 — Отклонять NaN и Inf во всех научных numeric inputs.**

Checkpoint: CP04. Приоритет: MUST. Проверка: unit.

Приемка AT-DOM-008: Schema test покрывает parameters, times и doses.

Свидетельство: `CP04/evidence/DOM-008`; command/result/hash либо manual review record.

**DOM-009 — Запрещать запись NaN и Inf как валидного результата.**

Checkpoint: CP04. Приоритет: MUST. Проверка: unit.

Приемка AT-DOM-009: Writer завершает проверку ошибкой и не публикует result.

Свидетельство: `CP04/evidence/DOM-009`; command/result/hash либо manual review record.

**DOM-010 — Сохранять event units отдельно от отображаемой подписи.**

Checkpoint: CP04. Приоритет: MUST. Проверка: unit.

Приемка AT-DOM-010: Unit mapping test обнаруживает несовместимую CT/RT единицу.

Свидетельство: `CP04/evidence/DOM-010`; command/result/hash либо manual review record.

**DOM-011 — Различать solver step и output sampling.**

Checkpoint: CP04. Приоритет: MUST. Проверка: unit.

Приемка AT-DOM-011: Изменение frame interval не изменяет заданный solver dt.

Свидетельство: `CP04/evidence/DOM-011`; command/result/hash либо manual review record.

**DOM-012 — Сохранять события RT и CT в одно время.**

Checkpoint: CP04. Приоритет: MUST. Проверка: unit.

Приемка AT-DOM-012: Validator не удаляет cross-modality simultaneous events.

Свидетельство: `CP04/evidence/DOM-012`; command/result/hash либо manual review record.

**DOM-013 — Отклонять unsupported combination до постановки в очередь.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-DOM-013: API возвращает field error и не создает RunAttempt.

Свидетельство: `CP04/evidence/DOM-013`; command/result/hash либо manual review record.

**DOM-014 — Хранить UTC timestamps и отдельную научную ось времени.**

Checkpoint: CP04. Приоритет: MUST. Проверка: unit.

Приемка AT-DOM-014: Serialization round-trip сохраняет origin и days_from_origin.

Свидетельство: `CP04/evidence/DOM-014`; command/result/hash либо manual review record.

### JOB Очередь и выполнение

**JOB-001 — Возвращать run_id до выполнения тяжелого solver.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-001: Controlled slow worker не задерживает POST до завершения.

Свидетельство: `CP05/evidence/JOB-001`; command/result/hash либо manual review record.

**JOB-002 — Ограничивать default concurrency одним worker.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-002: Три queued задачи никогда не создают два active workers.

Свидетельство: `CP05/evidence/JOB-002`; command/result/hash либо manual review record.

**JOB-003 — Захватывать queued attempt атомарно.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-003: Два supervisors получают только один valid claim на одну задачу.

Свидетельство: `CP05/evidence/JOB-003`; command/result/hash либо manual review record.

**JOB-004 — Требовать ownership token для worker state updates.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-004: Update с чужим token не изменяет статус.

Свидетельство: `CP05/evidence/JOB-004`; command/result/hash либо manual review record.

**JOB-005 — Сохранять terminal state при позднем heartbeat.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-005: Поздний running update после cancelled отклоняется.

Свидетельство: `CP05/evidence/JOB-005`; command/result/hash либо manual review record.

**JOB-006 — Возвращать прежний run по одинаковому idempotency key.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-006: Два concurrent POST создают один attempt.

Свидетельство: `CP05/evidence/JOB-006`; command/result/hash либо manual review record.

**JOB-007 — Отклонять новый payload со старым idempotency key.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-007: API возвращает 409 и сохраняет первый plan.

Свидетельство: `CP05/evidence/JOB-007`; command/result/hash либо manual review record.

**JOB-008 — Отменять queued задачу без запуска worker.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-008: Контролируемый worker для отмененной queued задачи не вызывается.

Свидетельство: `CP05/evidence/JOB-008`; command/result/hash либо manual review record.

**JOB-009 — Отменять running задачу через cancel_requested.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-009: В event log присутствует корректный переход к cancelled.

Свидетельство: `CP05/evidence/JOB-009`; command/result/hash либо manual review record.

**JOB-010 — Ограничивать termination деревом процессов данного запуска.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-010: Unrelated sentinel process остается жив после cancel.

Свидетельство: `CP05/evidence/JOB-010`; command/result/hash либо manual review record.

**JOB-011 — Завершать timeout отдельной диагностируемой причиной.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-011: Slow worker получает timed_out с сохраненным elapsed time.

Свидетельство: `CP05/evidence/JOB-011`; command/result/hash либо manual review record.

**JOB-012 — Обнаруживать stale lease после restart.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-012: Задача не остается running без живого владельца.

Свидетельство: `CP05/evidence/JOB-012`; command/result/hash либо manual review record.

**JOB-013 — Не восстанавливать ownership только по совпавшему PID.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-013: Reused PID без token не признается принадлежащим run.

Свидетельство: `CP05/evidence/JOB-013`; command/result/hash либо manual review record.

**JOB-014 — Создавать новый attempt при retry.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-014: Старый failed attempt и error log остаются доступны.

Свидетельство: `CP05/evidence/JOB-014`; command/result/hash либо manual review record.

**JOB-015 — Публиковать succeeded после artifact validation.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-015: Поврежденный output worker не приводит к succeeded.

Свидетельство: `CP05/evidence/JOB-015`; command/result/hash либо manual review record.

**JOB-016 — Сохранять этапы и подтвержденные счетчики прогресса.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-016: Unknown total отображается как indeterminate, не fake percentage.

Свидетельство: `CP05/evidence/JOB-016`; command/result/hash либо manual review record.

**JOB-017 — Продолжать supervisor heartbeat во время долгого solver step.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-017: Длительный controlled solve не объявляется stale при живом supervisor.

Свидетельство: `CP05/evidence/JOB-017`; command/result/hash либо manual review record.

**JOB-018 — Использовать один executor для runs и study children.**

Checkpoint: CP08. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-018: Concurrency limit соблюдается при одновременных run и cohort.

Свидетельство: `CP08/evidence/JOB-018`; command/result/hash либо manual review record.

**JOB-019 — Переиспользовать завершенные child tasks по проверенному identity.**

Checkpoint: CP08. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-019: Retry study не пересчитывает verified completed rows без явного rerun.

Свидетельство: `CP08/evidence/JOB-019`; command/result/hash либо manual review record.

**JOB-020 — Сохранять соответствие child result строке sample matrix.**

Checkpoint: CP08. Приоритет: MUST. Проверка: integration.

Приемка AT-JOB-020: Изменение порядка completion не меняет порядок outcomes.

Свидетельство: `CP08/evidence/JOB-020`; command/result/hash либо manual review record.

### STO Хранение и экспорт

**STO-001 — Применять versioned database migrations.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-001: Новая установка и upgrade fixture дают одинаковую schema version.

Свидетельство: `CP04/evidence/STO-001`; command/result/hash либо manual review record.

**STO-002 — Включать foreign key checks в SQLite connections.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-002: Удаление referenced immutable entity отклоняется.

Свидетельство: `CP04/evidence/STO-002`; command/result/hash либо manual review record.

**STO-003 — Публиковать result directory атомарно.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-003: Crash до rename не дает читателю complete result.

Свидетельство: `CP04/evidence/STO-003`; command/result/hash либо manual review record.

**STO-004 — Проверять payload hashes при загрузке артефакта.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-004: Corrupted frame не обслуживается как verified field.

Свидетельство: `CP04/evidence/STO-004`; command/result/hash либо manual review record.

**STO-005 — Сверять completeness и expected frames при cache hit.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-005: Неполный result не переиспользуется.

Свидетельство: `CP04/evidence/STO-005`; command/result/hash либо manual review record.

**STO-006 — Обнаруживать orphan temporary files при startup.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-006: Reconciliation report перечисляет temp без auto-success.

Свидетельство: `CP04/evidence/STO-006`; command/result/hash либо manual review record.

**STO-007 — Запрещать выход artifact path за LAB_ROOT.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-007: Traversal и junction fixture отклоняются до file operation.

Свидетельство: `CP04/evidence/STO-007`; command/result/hash либо manual review record.

**STO-008 — Считать runtime output quota до запуска.**

Checkpoint: CP07. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-008: Plan выше 1 GiB per-run default rejected с budget reason.

Свидетельство: `CP07/evidence/STO-008`; command/result/hash либо manual review record.

**STO-009 — Сохранять reserve свободного места во время записи.**

Checkpoint: CP07. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-009: Low-disk fixture завершает run с disk_limit без удаления старых файлов.

Свидетельство: `CP07/evidence/STO-009`; command/result/hash либо manual review record.

**STO-010 — Хранить scalar series независимо от dense frames.**

Checkpoint: CP07. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-010: Удаление разрешенных frames не удаляет metrics.csv.

Свидетельство: `CP07/evidence/STO-010`; command/result/hash либо manual review record.

**STO-011 — Защищать publication-pinned artifacts от cleanup.**

Checkpoint: CP07. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-011: Cleanup выбранного pinned result rejected.

Свидетельство: `CP07/evidence/STO-011`; command/result/hash либо manual review record.

**STO-012 — Защищать active-run files от cleanup.**

Checkpoint: CP07. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-012: Cleanup active attempt rejected при существующей lease.

Свидетельство: `CP07/evidence/STO-012`; command/result/hash либо manual review record.

**STO-013 — Предварительно показывать точный состав cleanup.**

Checkpoint: CP07. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-013: Preview token соответствует списку и размерам удаляемых files.

Свидетельство: `CP07/evidence/STO-013`; command/result/hash либо manual review record.

**STO-014 — Удалять только проверенные элементы cleanup selection.**

Checkpoint: CP07. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-014: Измененный selection token требует нового preview.

Свидетельство: `CP07/evidence/STO-014`; command/result/hash либо manual review record.

**STO-015 — Отмечать недоступность удаленных кадров в manifest metadata.**

Checkpoint: CP07. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-015: UI не предлагает загрузить удаленный frame как available.

Свидетельство: `CP07/evidence/STO-015`; command/result/hash либо manual review record.

**STO-016 — Создавать consistent backup SQLite через backup mechanism.**

Checkpoint: CP07. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-016: Restore test восстанавливает committed rows при active WAL.

Свидетельство: `CP07/evidence/STO-016`; command/result/hash либо manual review record.

**STO-017 — Исключать restricted upstream assets из compact export.**

Checkpoint: CP07. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-017: Archive inspection не содержит source/volumes с запрещенной передачей.

Свидетельство: `CP07/evidence/STO-017`; command/result/hash либо manual review record.

**STO-018 — Проверять import size и пути до распаковки.**

Checkpoint: CP07. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-018: Zip traversal и decompression limit fixture rejected.

Свидетельство: `CP07/evidence/STO-018`; command/result/hash либо manual review record.

**STO-019 — Импортировать пакеты как данные без исполнения кода.**

Checkpoint: CP07. Приоритет: MUST. Проверка: integration.

Приемка AT-STO-019: Payload с script/pickle не исполняется и rejected по schema.

Свидетельство: `CP07/evidence/STO-019`; command/result/hash либо manual review record.

**STO-020 — Выполнять replay в новом workspace по export plan.**

Checkpoint: CP07. Приоритет: MUST. Проверка: engine.

Приемка AT-STO-020: Replay report содержит сравнение endpoints и hashes allowed inputs.

Свидетельство: `CP07/evidence/STO-020`; command/result/hash либо manual review record.

### API API

**API-001 — Публиковать отдельные lab capabilities.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-API-001: CFB unavailable не делает lab unavailable при готовом author case.

Свидетельство: `CP04/evidence/API-001`; command/result/hash либо manual review record.

**API-002 — Не запускать вычисления в GET endpoints.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-API-002: GET suite не вызывает worker/download/calibration.

Свидетельство: `CP04/evidence/API-002`; command/result/hash либо manual review record.

**API-003 — Возвращать field_errors для невалидного сценария.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-API-003: 422 body указывает точное поле и понятную русскую причину.

Свидетельство: `CP04/evidence/API-003`; command/result/hash либо manual review record.

**API-004 — Возвращать 404 для неизвестного UUID.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-API-004: Ответ не раскрывает traceback или произвольный file path.

Свидетельство: `CP04/evidence/API-004`; command/result/hash либо manual review record.

**API-005 — Возвращать 409 для несовместимого сравнения.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-API-005: Ответ содержит mismatch fields.

Свидетельство: `CP04/evidence/API-005`; command/result/hash либо manual review record.

**API-006 — Ограничивать pagination списков.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-API-006: Limit выше server maximum rejected либо явно capped по контракту.

Свидетельство: `CP04/evidence/API-006`; command/result/hash либо manual review record.

**API-007 — Согласовать OpenAPI и TypeScript enums.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-API-007: Contract test обнаруживает неизвестный terminal status.

Свидетельство: `CP04/evidence/API-007`; command/result/hash либо manual review record.

**API-008 — Сохранять request_id в ошибке и диагностическом журнале.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-API-008: ID связывает response и server log entry.

Свидетельство: `CP05/evidence/API-008`; command/result/hash либо manual review record.

**API-009 — Передавать только запрошенный slice/frame descriptor.**

Checkpoint: CP06. Приоритет: MUST. Проверка: integration.

Приемка AT-API-009: Один запрос 2D не передает всю 4D trajectory.

Свидетельство: `CP06/evidence/API-009`; command/result/hash либо manual review record.

**API-010 — Проверять bounds slice и frame index.**

Checkpoint: CP06. Приоритет: MUST. Проверка: integration.

Приемка AT-API-010: Out-of-range request возвращает 422 без тяжелой обработки.

Свидетельство: `CP06/evidence/API-010`; command/result/hash либо manual review record.

**API-011 — Помечать время и geometry каждого view response.**

Checkpoint: CP06. Приоритет: MUST. Проверка: integration.

Приемка AT-API-011: Response metadata связывает изображение с run/frame.

Свидетельство: `CP06/evidence/API-011`; command/result/hash либо manual review record.

**API-012 — Упаковывать большой export фоновой задачей.**

Checkpoint: CP07. Приоритет: MUST. Проверка: integration.

Приемка AT-API-012: Download GET не пересобирает archive.

Свидетельство: `CP07/evidence/API-012`; command/result/hash либо manual review record.

### UI Интерфейс

**UI-001 — Открывать лабораторию независимо от selectedPatientId.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-001: No-CFB browser startup показывает lab catalog.

Свидетельство: `CP06/evidence/UI-001`; command/result/hash либо manual review record.

**UI-002 — Скрывать еще не реализованные navigation actions.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-002: До capability нет активной кнопки с пустым обработчиком.

Свидетельство: `CP06/evidence/UI-002`; command/result/hash либо manual review record.

**UI-003 — Показывать synthetic label на карточке и result page.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-003: Label виден без открытия technical diagnostics.

Свидетельство: `CP06/evidence/UI-003`; command/result/hash либо manual review record.

**UI-004 — Показывать источник и цитирование case.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-004: Case details содержит доступный source link.

Свидетельство: `CP06/evidence/UI-004`; command/result/hash либо manual review record.

**UI-005 — Объяснять missing case data конкретным действием.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-005: Empty state содержит preparation command и размер/оценку.

Свидетельство: `CP06/evidence/UI-005`; command/result/hash либо manual review record.

**UI-006 — Делать baseline read-only.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-006: Изменение baseline открывает копию с новым identity.

Свидетельство: `CP06/evidence/UI-006`; command/result/hash либо manual review record.

**UI-007 — Сохранять точный numeric input помимо slider.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-007: Ввод scientific notation round-trip сохраняет значение.

Свидетельство: `CP06/evidence/UI-007`; command/result/hash либо manual review record.

**UI-008 — Показывать единицу у каждого numeric parameter.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-008: Editor labels содержат descriptor unit.

Свидетельство: `CP06/evidence/UI-008`; command/result/hash либо manual review record.

**UI-009 — Показывать источник default parameter.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-009: Author, assumed и fitted различаются в editor info.

Свидетельство: `CP06/evidence/UI-009`; command/result/hash либо manual review record.

**UI-010 — Обрабатывать десятичную запятую явно.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-010: Ввод 0,01 либо корректно нормализован, либо объяснимо rejected.

Свидетельство: `CP06/evidence/UI-010`; command/result/hash либо manual review record.

**UI-011 — Показывать validation error рядом с полем.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-011: Invalid value не приводит к общей бессодержательной ошибке.

Свидетельство: `CP06/evidence/UI-011`; command/result/hash либо manual review record.

**UI-012 — Предотвращать запуск invalid scenario.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-012: Кнопка недоступна до успешной server validation.

Свидетельство: `CP06/evidence/UI-012`; command/result/hash либо manual review record.

**UI-013 — Показывать scientific diff перед запуском.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-013: Измененная доза или параметр видны в preview.

Свидетельство: `CP06/evidence/UI-013`; command/result/hash либо manual review record.

**UI-014 — Разделять интеграционный шаг и время сохранения кадров.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-014: Два controls имеют разные подписи и independent values.

Свидетельство: `CP06/evidence/UI-014`; command/result/hash либо manual review record.

**UI-015 — Редактировать treatment events таблично.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-015: Add/delete изменяют только выбранную draft row.

Свидетельство: `CP06/evidence/UI-015`; command/result/hash либо manual review record.

**UI-016 — Сохранять draft при ошибке сети.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-016: После failed submit значения остаются в редакторе.

Свидетельство: `CP06/evidence/UI-016`; command/result/hash либо manual review record.

**UI-017 — Обозначать несохраненный draft при уходе.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-017: Navigation предоставляет возможность вернуться без потери ввода.

Свидетельство: `CP06/evidence/UI-017`; command/result/hash либо manual review record.

**UI-018 — Блокировать повторный submit до ответа.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-018: Double click не создает два видимых независимых запуска.

Свидетельство: `CP06/evidence/UI-018`; command/result/hash либо manual review record.

**UI-019 — Показывать truthful state при неизвестном прогрессе.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-019: Unknown denominator дает spinner и phase без процентов.

Свидетельство: `CP06/evidence/UI-019`; command/result/hash либо manual review record.

**UI-020 — Показывать elapsed time отдельно от ETA.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-020: ETA отсутствует без measured cost profile.

Свидетельство: `CP06/evidence/UI-020`; command/result/hash либо manual review record.

**UI-021 — Обновлять status без ручного reload.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-021: Polling отображает terminal state и прекращается после завершения.

Свидетельство: `CP06/evidence/UI-021`; command/result/hash либо manual review record.

**UI-022 — Показывать actionable failed/interrupted state.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-022: Result page содержит reason и допустимый retry action.

Свидетельство: `CP06/evidence/UI-022`; command/result/hash либо manual review record.

**UI-023 — Отображать partial outputs с отдельным статусом.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-023: Partial не имеет подписи complete result.

Свидетельство: `CP06/evidence/UI-023`; command/result/hash либо manual review record.

**UI-024 — Выбирать только фактически сохраненные frame times.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-024: Slider labels совпадают с frames endpoint.

Свидетельство: `CP06/evidence/UI-024`; command/result/hash либо manual review record.

**UI-025 — Синхронизировать график и пространственные views по frame.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-025: Выбранный time одинаков в graph marker, slice metadata и 3D metadata.

Свидетельство: `CP06/evidence/UI-025`; command/result/hash либо manual review record.

**UI-026 — Игнорировать устаревшие frame responses.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-026: Быстрое переключение оставляет последний выбранный frame.

Свидетельство: `CP06/evidence/UI-026`; command/result/hash либо manual review record.

**UI-027 — Не подписывать старое изображение новым временем при loading.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-027: Во время pending response виден loading с прежним frame identity.

Свидетельство: `CP06/evidence/UI-027`; command/result/hash либо manual review record.

**UI-028 — Проигрывать только сохраненную trajectory.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-028: Play меняет saved index без fake solver progress.

Свидетельство: `CP06/evidence/UI-028`; command/result/hash либо manual review record.

**UI-029 — Предоставлять управление slice с клавиатуры.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-029: Arrow keys меняют разрешенный slice index.

Свидетельство: `CP06/evidence/UI-029`; command/result/hash либо manual review record.

**UI-030 — Отображать physical location и plane.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-030: Plane name и координата получены из geometry.

Свидетельство: `CP06/evidence/UI-030`; command/result/hash либо manual review record.

**UI-031 — Разделять MRI window и density color scale.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-031: Изменение MRI window не меняет scientific threshold.

Свидетельство: `CP06/evidence/UI-031`; command/result/hash либо manual review record.

**UI-032 — Показывать L/R только после orientation validation.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-032: Fixture с неподтвержденной orientation не показывает произвольные L/R.

Свидетельство: `CP06/evidence/UI-032`; command/result/hash либо manual review record.

**UI-033 — Оставлять график и 2D доступными при WebGL failure.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-033: Ошибка 3D не блокирует прочие вкладки.

Свидетельство: `CP06/evidence/UI-033`; command/result/hash либо manual review record.

**UI-034 — Объяснять отсутствие isosurface при threshold.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-034: Пустой mesh дает текст без общей ошибки run.

Свидетельство: `CP06/evidence/UI-034`; command/result/hash либо manual review record.

**UI-035 — Предоставлять reset camera.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-035: Кнопка возвращает воспроизводимый initial view.

Свидетельство: `CP06/evidence/UI-035`; command/result/hash либо manual review record.

**UI-036 — Использовать общую density scale в paired view по умолчанию.**

Checkpoint: CP07. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-036: Одинаковая density имеет одинаковый цвет в обеих панелях.

Свидетельство: `CP07/evidence/UI-036`; command/result/hash либо manual review record.

**UI-037 — Показывать различия параметров paired scenarios.**

Checkpoint: CP07. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-037: Diff table перечисляет все scientific mismatches.

Свидетельство: `CP07/evidence/UI-037`; command/result/hash либо manual review record.

**UI-038 — Обозначать политику несовпадающих времен.**

Checkpoint: CP07. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-038: Nearest/interpolated scalar value подписан явно.

Свидетельство: `CP07/evidence/UI-038`; command/result/hash либо manual review record.

**UI-039 — Показывать unresolved вместо принудительного победителя.**

Checkpoint: CP07. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-039: Delta внутри epsilon не получает positive winner badge.

Свидетельство: `CP07/evidence/UI-039`; command/result/hash либо manual review record.

**UI-040 — Показывать расчетный характер preference.**

Checkpoint: CP07. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-040: Result text не содержит клинического назначения лечения.

Свидетельство: `CP07/evidence/UI-040`; command/result/hash либо manual review record.

**UI-041 — Показывать размер и тип export до скачивания.**

Checkpoint: CP07. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-041: Compact/full options имеют состав и asset restrictions.

Свидетельство: `CP07/evidence/UI-041`; command/result/hash либо manual review record.

**UI-042 — Показывать storage usage по категориям.**

Checkpoint: CP07. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-042: Overview разделяет raw data, outputs, cache и environment estimate.

Свидетельство: `CP07/evidence/UI-042`; command/result/hash либо manual review record.

**UI-043 — Подтверждать cleanup после dependency preview.**

Checkpoint: CP07. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-043: Удаление требует выбора конкретного набора artifacts.

Свидетельство: `CP07/evidence/UI-043`; command/result/hash либо manual review record.

**UI-044 — Проводить study setup через последовательный wizard.**

Checkpoint: CP08. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-044: Пропуск обязательного endpoint/seed не позволяет freeze.

Свидетельство: `CP08/evidence/UI-044`; command/result/hash либо manual review record.

**UI-045 — Показывать число evaluations до запуска study.**

Checkpoint: CP08. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-045: Число совпадает с замороженной execution matrix.

Свидетельство: `CP08/evidence/UI-045`; command/result/hash либо manual review record.

**UI-046 — Оставлять frozen protocol read-only.**

Checkpoint: CP08. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-046: Изменение settings создает новый draft version.

Свидетельство: `CP08/evidence/UI-046`; command/result/hash либо manual review record.

**UI-047 — Показывать requested/completed/failed/paired counts.**

Checkpoint: CP08. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-047: Counts сверяются с child table, failures не скрыты.

Свидетельство: `CP08/evidence/UI-047`; command/result/hash либо manual review record.

**UI-048 — Отличать viewport filter от primary scientific summary.**

Checkpoint: CP08. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-048: Фильтр плохих rows не меняет frozen primary aggregate.

Свидетельство: `CP08/evidence/UI-048`; command/result/hash либо manual review record.

**UI-049 — Отображать assumptions распределения виртуальных subjects.**

Checkpoint: CP08. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-049: Cohort page не называет uniform samples реальной популяцией.

Свидетельство: `CP08/evidence/UI-049`; command/result/hash либо manual review record.

**UI-050 — Показывать метод и диапазоны sensitivity chart.**

Checkpoint: CP08. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-050: Chart subtitle содержит endpoint, parameter ranges и sample count.

Свидетельство: `CP08/evidence/UI-050`; command/result/hash либо manual review record.

**UI-051 — Иметь labels и видимый focus для interactive controls.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-051: Keyboard smoke проходит основной путь без мыши.

Свидетельство: `CP06/evidence/UI-051`; command/result/hash либо manual review record.

**UI-052 — Передавать статус текстом помимо цвета.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-052: Color-disabled screenshot сохраняет смысл queued/failed/succeeded.

Свидетельство: `CP06/evidence/UI-052`; command/result/hash либо manual review record.

**UI-053 — Сохранять основной путь на 1366×768.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-053: Основные actions видны, body не требует горизонтального scroll.

Свидетельство: `CP06/evidence/UI-053`; command/result/hash либо manual review record.

**UI-054 — Обрабатывать unavailable и error отдельно.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-UI-054: Missing engine и network failure имеют разные сообщения.

Свидетельство: `CP06/evidence/UI-054`; command/result/hash либо manual review record.

### NUM Численная корректность

**NUM-001 — Пройти fidelity TCC на всех контрольных временах.**

Checkpoint: CP03. Приоритет: MUST. Проверка: engine.

Приемка AT-NUM-001: Max relative TCC error ≤1e−3 по declared near-zero policy.

Свидетельство: `CP03/evidence/NUM-001`; command/result/hash либо manual review record.

**NUM-002 — Пройти fidelity normalized fields.**

Checkpoint: CP03. Приоритет: MUST. Проверка: engine.

Приемка AT-NUM-002: RMSE/carrying-capacity scale ≤1e−4 на каждом контрольном кадре.

Свидетельство: `CP03/evidence/NUM-002`; command/result/hash либо manual review record.

**NUM-003 — Проверить logistic ODE против аналитического решения.**

Checkpoint: CP03. Приоритет: MUST. Проверка: numerical.

Приемка AT-NUM-003: Уменьшение dt дает ожидаемую convergence и recorded error.

Свидетельство: `CP03/evidence/NUM-003`; command/result/hash либо manual review record.

**NUM-004 — Проверить mass balance чистой no-flux диффузии.**

Checkpoint: CP03. Приоритет: MUST. Проверка: numerical.

Приемка AT-NUM-004: Mass error укладывается в dtype-specific declared tolerance.

Свидетельство: `CP03/evidence/NUM-004`; command/result/hash либо manual review record.

**NUM-005 — Применять fraction на границе один раз.**

Checkpoint: CP03. Приоритет: MUST. Проверка: numerical.

Приемка AT-NUM-005: Сегментированный и цельный расчет имеют одинаковый event count.

Свидетельство: `CP03/evidence/NUM-005`; command/result/hash либо manual review record.

**NUM-006 — Сопоставить RT/CT semantics с pinned upstream.**

Checkpoint: CP03. Приоритет: MUST. Проверка: engine.

Приемка AT-NUM-006: Same-time events дают совпадающий direct/adapter result.

Свидетельство: `CP03/evidence/NUM-006`; command/result/hash либо manual review record.

**NUM-007 — Измерить time convergence на dt, dt/2 и dt/4.**

Checkpoint: CP03. Приоритет: MUST. Проверка: numerical.

Приемка AT-NUM-007: Report содержит endpoint differences на одном physical case.

Свидетельство: `CP03/evidence/NUM-007`; command/result/hash либо manual review record.

**NUM-008 — Измерить spatial convergence при сопоставимой initialization.**

Checkpoint: CP03. Приоритет: MUST. Проверка: numerical.

Приемка AT-NUM-008: Report содержит initial physical mass и endpoint errors для двух grids.

Свидетельство: `CP03/evidence/NUM-008`; command/result/hash либо manual review record.

**NUM-009 — Отделить scalar sampling error от integration error.**

Checkpoint: CP03. Приоритет: MUST. Проверка: numerical.

Приемка AT-NUM-009: Изменение scalar interval сравнивается при fixed solver dt.

Свидетельство: `CP03/evidence/NUM-009`; command/result/hash либо manual review record.

**NUM-010 — Не менять frozen legacy equations ради lab fidelity.**

Checkpoint: CP03. Приоритет: MUST. Проверка: manual.

Приемка AT-NUM-010: Diff protected model files проверен; любое изменение обособлено и обосновано.

Свидетельство: `CP03/evidence/NUM-010`; command/result/hash либо manual review record.

**NUM-011 — Зафиксировать ranking epsilon до evaluation.**

Checkpoint: CP09. Приоритет: MUST. Проверка: science.

Приемка AT-NUM-011: Frozen protocol содержит abs/rel/numerical components и scale.

Свидетельство: `CP09/evidence/NUM-011`; command/result/hash либо manual review record.

**NUM-012 — Отмечать сравнение внутри numerical resolution как unresolved.**

Checkpoint: CP09. Приоритет: MUST. Проверка: unit.

Приемка AT-NUM-012: Synthetic near-tie fixture не порождает ложного уверенного ranking.

Свидетельство: `CP09/evidence/NUM-012`; command/result/hash либо manual review record.

### ANA Анализ

**ANA-001 — Проверять одинаковое initial state при ordinary paired comparison.**

Checkpoint: CP07. Приоритет: MUST. Проверка: unit.

Приемка AT-ANA-001: Разные initial_state hashes отклоняются как incompatible.

Свидетельство: `CP07/evidence/ANA-001`; command/result/hash либо manual review record.

**ANA-002 — Рассчитывать paired delta с документированным знаком.**

Checkpoint: CP07. Приоритет: MUST. Проверка: unit.

Приемка AT-ANA-002: Lower-is-better fixture дает delta_AB=J_A−J_B.

Свидетельство: `CP07/evidence/ANA-002`; command/result/hash либо manual review record.

**ANA-003 — Считать AUC по фактическим scalar times.**

Checkpoint: CP07. Приоритет: MUST. Проверка: unit.

Приемка AT-ANA-003: Nonuniform analytic trajectory совпадает с trapezoid reference.

Свидетельство: `CP07/evidence/ANA-003`; command/result/hash либо manual review record.

**ANA-004 — Считать spatial integral в физических единицах.**

Checkpoint: CP07. Приоритет: MUST. Проверка: unit.

Приемка AT-ANA-004: Affine-volume fixture совпадает с determinant-based reference.

Свидетельство: `CP07/evidence/ANA-004`; command/result/hash либо manual review record.

**ANA-005 — Обрабатывать нулевой denominator как undefined.**

Checkpoint: CP07. Приоритет: MUST. Проверка: unit.

Приемка AT-ANA-005: API возвращает reason вместо 0/NaN/Inf.

Свидетельство: `CP07/evidence/ANA-005`; command/result/hash либо manual review record.

**ANA-006 — Считать local central differences для interior factors.**

Checkpoint: CP08. Приоритет: MUST. Проверка: numerical.

Приемка AT-ANA-006: Analytic smooth fixture совпадает в declared tolerance.

Свидетельство: `CP08/evidence/ANA-006`; command/result/hash либо manual review record.

**ANA-007 — Повторять local sensitivity на h/2.**

Checkpoint: CP08. Приоритет: MUST. Проверка: numerical.

Приемка AT-ANA-007: Report содержит step-sensitivity/error estimate.

Свидетельство: `CP08/evidence/ANA-007`; command/result/hash либо manual review record.

**ANA-008 — Применять объявленную one-sided formula на boundary.**

Checkpoint: CP08. Приоритет: MUST. Проверка: numerical.

Приемка AT-ANA-008: Boundary fixture не создает invalid negative parameter.

Свидетельство: `CP08/evidence/ANA-008`; command/result/hash либо manual review record.

**ANA-009 — Выбирать корректное нормирование при zero nominal.**

Checkpoint: CP08. Приоритет: MUST. Проверка: unit.

Приемка AT-ANA-009: Normalized sensitivity использует declared scale без деления на ноль.

Свидетельство: `CP08/evidence/ANA-009`; command/result/hash либо manual review record.

**ANA-010 — Показывать негладкость threshold endpoint.**

Checkpoint: CP08. Приоритет: MUST. Проверка: numerical.

Приемка AT-ANA-010: Step-dependent fixture получает warning вместо ложного zero influence.

Свидетельство: `CP08/evidence/ANA-010`; command/result/hash либо manual review record.

**ANA-011 — Сохранять Morris sample matrix до выполнения.**

Checkpoint: CP08. Приоритет: MUST. Проверка: integration.

Приемка AT-ANA-011: Digest matrix существует до первого child solve.

Свидетельство: `CP08/evidence/ANA-011`; command/result/hash либо manual review record.

**ANA-012 — Воспроизводить Morris design по seed и pinned sampler.**

Checkpoint: CP08. Приоритет: MUST. Проверка: unit.

Приемка AT-ANA-012: Повтор дает ту же matrix в зарегистрированном environment.

Свидетельство: `CP08/evidence/ANA-012`; command/result/hash либо manual review record.

**ANA-013 — Проверять r(k+1) evaluations в independent Morris design.**

Checkpoint: CP08. Приоритет: MUST. Проверка: unit.

Приемка AT-ANA-013: Plan preview совпадает с matrix rows до reuse.

Свидетельство: `CP08/evidence/ANA-013`; command/result/hash либо manual review record.

**ANA-014 — Возвращать mu, mu_star и sigma с методическими labels.**

Checkpoint: CP08. Приоритет: MUST. Проверка: unit.

Приемка AT-ANA-014: Result schema не называет их Sobol indices или identifiability.

Свидетельство: `CP08/evidence/ANA-014`; command/result/hash либо manual review record.

**ANA-015 — Не подавать discrete schedules как continuous factors.**

Checkpoint: CP08. Приоритет: MUST. Проверка: unit.

Приемка AT-ANA-015: Morris validation отклоняет unsupported discrete factor.

Свидетельство: `CP08/evidence/ANA-015`; command/result/hash либо manual review record.

**ANA-016 — Сохранять immutable subject table виртуальной когорты.**

Checkpoint: CP08. Приоритет: MUST. Проверка: unit.

Приемка AT-ANA-016: Seeded LHS repeat дает исходный table hash.

Свидетельство: `CP08/evidence/ANA-016`; command/result/hash либо manual review record.

**ANA-017 — Использовать одинаковые subject parameters во всех scenarios.**

Checkpoint: CP08. Приоритет: MUST. Проверка: integration.

Приемка AT-ANA-017: Pair matrix имеет общую subject row для каждого comparator.

Свидетельство: `CP08/evidence/ANA-017`; command/result/hash либо manual review record.

**ANA-018 — Учитывать неполные пары в denominators.**

Checkpoint: CP08. Приоритет: MUST. Проверка: unit.

Приемка AT-ANA-018: Failure fixture показывает planned N и меньший complete-pair N.

Свидетельство: `CP08/evidence/ANA-018`; command/result/hash либо manual review record.

**ANA-019 — Различать geometry count и parameter realization count.**

Checkpoint: CP08. Приоритет: MUST. Проверка: unit.

Приемка AT-ANA-019: Report содержит оба значения и не называет N samples пациентами.

Свидетельство: `CP08/evidence/ANA-019`; command/result/hash либо manual review record.

**ANA-020 — Рассчитать forecast normalized density RMSE на future frames.**

Checkpoint: CP10. Приоритет: MUST. Проверка: unit.

Приемка AT-ANA-020: Analytic fixture подтверждает формулу и единый carrying-capacity scale.

Свидетельство: `CP10/evidence/ANA-020`; command/result/hash либо manual review record.

### SCI Научный протокол

**SCI-001 — Зафиксировать question и primary endpoint статьи A.**

Checkpoint: CP09. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-001: Protocol S-A содержит hypothesis/measurements и benchmark matrix.

Свидетельство: `CP09/evidence/SCI-001`; command/result/hash либо manual review record.

**SCI-002 — Зафиксировать question и primary statistic статьи B.**

Checkpoint: CP09. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-002: Protocol S-B содержит однозначный estimand и undefined policy.

Свидетельство: `CP09/evidence/SCI-002`; command/result/hash либо manual review record.

**SCI-003 — Зафиксировать schedules до основной серии.**

Checkpoint: CP09. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-003: Protocol hash включает baseline и два comparator event tables.

Свидетельство: `CP09/evidence/SCI-003`; command/result/hash либо manual review record.

**SCI-004 — Обосновать ranges каждого factor.**

Checkpoint: CP09. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-004: Для bounds указан primary source или explicit assumption.

Свидетельство: `CP09/evidence/SCI-004`; command/result/hash либо manual review record.

**SCI-005 — Разделить pilot, development и evaluation seeds.**

Checkpoint: CP09. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-005: Freeze включает 1105, 2205 и 3305 либо обоснованную новую версию до запуска.

Свидетельство: `CP09/evidence/SCI-005`; command/result/hash либо manual review record.

**SCI-006 — Выбрать design по measured feasibility rule.**

Checkpoint: CP09. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-006: Budget worksheet содержит solves, upper cost estimate и 30% reserve.

Свидетельство: `CP09/evidence/SCI-006`; command/result/hash либо manual review record.

**SCI-007 — Зафиксировать failure/missing-data policy до evaluation.**

Checkpoint: CP09. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-007: Протокол определяет retry, denominators и допустимость conclusion.

Свидетельство: `CP09/evidence/SCI-007`; command/result/hash либо manual review record.

**SCI-008 — Зафиксировать output retention для всей серии.**

Checkpoint: CP09. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-008: Full-field subjects выбраны до outcomes; остальные scalar policy.

Свидетельство: `CP09/evidence/SCI-008`; command/result/hash либо manual review record.

**SCI-009 — Фиксировать protocol hash до первого evaluation solve.**

Checkpoint: CP09. Приоритет: MUST. Проверка: integration.

Приемка AT-SCI-009: Timestamp и hash существуют в execution receipt до результата.

Свидетельство: `CP09/evidence/SCI-009`; command/result/hash либо manual review record.

**SCI-010 — Сохранять все запланированные evaluation rows.**

Checkpoint: CP10. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-010: Outcomes содержит failed/cancelled rows с reason без замены subject.

Свидетельство: `CP10/evidence/SCI-010`; command/result/hash либо manual review record.

**SCI-011 — Не использовать evaluation outputs для tuning.**

Checkpoint: CP10. Приоритет: MUST. Проверка: manual.

Приемка AT-SCI-011: Изменение candidates требует нового protocol_id и отдельного result set.

Свидетельство: `CP10/evidence/SCI-011`; command/result/hash либо manual review record.

**SCI-012 — Вычислять rank reversal с учетом epsilon.**

Checkpoint: CP10. Приоритет: MUST. Проверка: unit.

Приемка AT-SCI-012: Analytic paired fixture покрывает nominal tie, reversal и unresolved.

Свидетельство: `CP10/evidence/SCI-012`; command/result/hash либо manual review record.

**SCI-013 — Различать model uncertainty и Monte Carlo uncertainty.**

Checkpoint: CP10. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-013: Report labels обозначают sampling design и estimand intervals.

Свидетельство: `CP10/evidence/SCI-013`; command/result/hash либо manual review record.

**SCI-014 — Сохранять отрицательные результаты исследования.**

Checkpoint: CP10. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-014: Вывод no established effect доступен при нулевом reversal без подбора нового endpoint.

Свидетельство: `CP10/evidence/SCI-014`; command/result/hash либо manual review record.

**SCI-015 — Не называть synthetic evaluation clinical validation.**

Checkpoint: CP10. Приоритет: MUST. Проверка: manual.

Приемка AT-SCI-015: Generated report содержит context of use и data kind.

Свидетельство: `CP10/evidence/SCI-015`; command/result/hash либо manual review record.

**SCI-016 — Разделять CT background и изменяемые RT candidates.**

Checkpoint: CP10. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-016: Scenario diff подтверждает одинаковые CT inputs в первой RT study.

Свидетельство: `CP10/evidence/SCI-016`; command/result/hash либо manual review record.

**SCI-017 — Учитывать равенство dose constraints при treatment comparison.**

Checkpoint: CP10. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-017: Total RT dose и fraction count сопоставляются до результатов.

Свидетельство: `CP10/evidence/SCI-017`; command/result/hash либо manual review record.

**SCI-018 — Зафиксировать synthetic forecast cutoff на пятом author visit.**

Checkpoint: CP09. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-018: Frozen forecast protocol перечисляет первые пять fit visits и future evaluation visits.

Свидетельство: `CP09/evidence/SCI-018`; command/result/hash либо manual review record.

**SCI-019 — Сохранить synthetic forecast fields до чтения future targets.**

Checkpoint: CP10. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-019: Prediction seal timestamp и execution log предшествуют evaluator decoding.

Свидетельство: `CP10/evidence/SCI-019`; command/result/hash либо manual review record.

**SCI-020 — Сравнить forecast с persistence последнего доступного состояния.**

Checkpoint: CP10. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-020: Отчет содержит одни future targets для model и persistence.

Свидетельство: `CP10/evidence/SCI-020`; command/result/hash либо manual review record.

**SCI-021 — Сохранить author fixed-parameter comparator в forecast demo.**

Checkpoint: CP10. Приоритет: MUST. Проверка: science.

Приемка AT-SCI-021: Comparator использует тот же cutoff/horizon без fit по future visits.

Свидетельство: `CP10/evidence/SCI-021`; command/result/hash либо manual review record.

### NFR Нефункциональные свойства

**NFR-001 — Использовать localhost binding по умолчанию.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-NFR-001: Remote interface не включен default config.

Свидетельство: `CP04/evidence/NFR-001`; command/result/hash либо manual review record.

**NFR-002 — Ограничивать CORS configured local origins.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-NFR-002: Unlisted origin не получает permissive response.

Свидетельство: `CP04/evidence/NFR-002`; command/result/hash либо manual review record.

**NFR-003 — Не принимать произвольный код из API payload.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-NFR-003: Executable/module/pickle inputs rejected.

Свидетельство: `CP04/evidence/NFR-003`; command/result/hash либо manual review record.

**NFR-004 — Соблюдать статусный API latency во время solve.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-NFR-004: На fixture p95 ≤1 s по 30 запросам после warmup.

Свидетельство: `CP05/evidence/NFR-004`; command/result/hash либо manual review record.

**NFR-005 — Соблюдать lightweight API latency без solve.**

Checkpoint: CP04. Приоритет: MUST. Проверка: integration.

Приемка AT-NFR-005: На fixture p95 ≤500 ms с hardware receipt.

Свидетельство: `CP04/evidence/NFR-005`; command/result/hash либо manual review record.

**NFR-006 — Подтверждать cancel в UI быстро.**

Checkpoint: CP05. Приоритет: MUST. Проверка: browser.

Приемка AT-NFR-006: После успешного POST visible cancel_requested ≤1 s.

Свидетельство: `CP05/evidence/NFR-006`; command/result/hash либо manual review record.

**NFR-007 — Ограничивать прекращение собственного worker по времени.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-NFR-007: Controlled worker stopped ≤10 s после cancel при declared mechanism.

Свидетельство: `CP05/evidence/NFR-007`; command/result/hash либо manual review record.

**NFR-008 — Учитывать default runtime storage limit 8 GiB.**

Checkpoint: CP07. Приоритет: MUST. Проверка: integration.

Приемка AT-NFR-008: Quota test считает tmp и exports вместе с outputs.

Свидетельство: `CP07/evidence/NFR-008`; command/result/hash либо manual review record.

**NFR-009 — Ограничивать default dense frames числом 21.**

Checkpoint: CP07. Приоритет: MUST. Проверка: unit.

Приемка AT-NFR-009: Plan с большим числом требует explicit allowed config change.

Свидетельство: `CP07/evidence/NFR-009`; command/result/hash либо manual review record.

**NFR-010 — Ограничивать submit числом 256 queued children.**

Checkpoint: CP08. Приоритет: MUST. Проверка: integration.

Приемка AT-NFR-010: Oversized batch rejected до создания частичной очереди.

Свидетельство: `CP08/evidence/NFR-010`; command/result/hash либо manual review record.

**NFR-011 — Фиксировать точные app и engine environments отдельно.**

Checkpoint: CP12. Приоритет: MUST. Проверка: manual.

Приемка AT-NFR-011: Release содержит lock/constraints и environment manifests.

Свидетельство: `CP12/evidence/NFR-011`; command/result/hash либо manual review record.

**NFR-012 — Обновить cache version при численно значимом изменении.**

Checkpoint: CP12. Приоритет: MUST. Проверка: unit.

Приемка AT-NFR-012: Regression fixture старого cache не переиспользуется новым solver contract.

Свидетельство: `CP12/evidence/NFR-012`; command/result/hash либо manual review record.

### TST Проверки

**TST-001 — Хранить реальный engine fidelity test отдельно от fast CI.**

Checkpoint: CP03. Приоритет: MUST. Проверка: manual.

Приемка AT-TST-001: Smoke job документирует необходимые assets и не скачивает полную коллекцию.

Свидетельство: `CP03/evidence/TST-001`; command/result/hash либо manual review record.

**TST-002 — Проверять crash/retry через controlled worker.**

Checkpoint: CP05. Приоритет: MUST. Проверка: integration.

Приемка AT-TST-002: Failure matrix покрывает fail, timeout, cancel и interrupted.

Свидетельство: `CP05/evidence/TST-002`; command/result/hash либо manual review record.

**TST-003 — Проверить browser path через реальный backend.**

Checkpoint: CP06. Приоритет: MUST. Проверка: browser.

Приемка AT-TST-003: Smoke проходит edit→run→saved frame без подмены API static JSON.

Свидетельство: `CP06/evidence/TST-003`; command/result/hash либо manual review record.

**TST-004 — Проверить export/replay вне исходного workspace.**

Checkpoint: CP07. Приоритет: MUST. Проверка: engine.

Приемка AT-TST-004: Fresh-directory receipt содержит matched results и input preparation instructions.

Свидетельство: `CP07/evidence/TST-004`; command/result/hash либо manual review record.

**TST-005 — Воспроизводить analysis из сохраненных outcomes.**

Checkpoint: CP10. Приоритет: MUST. Проверка: science.

Приемка AT-TST-005: Один analysis command дает те же tables и figures по immutable inputs.

Свидетельство: `CP10/evidence/TST-005`; command/result/hash либо manual review record.

**TST-006 — Пройти полную Python suite на итоговом commit.**

Checkpoint: CP12. Приоритет: MUST. Проверка: integration.

Приемка AT-TST-006: Release receipt содержит command, environment, count и exit code 0.

Свидетельство: `CP12/evidence/TST-006`; command/result/hash либо manual review record.

**TST-007 — Пройти frontend lint и build на итоговом commit.**

Checkpoint: CP12. Приоритет: MUST. Проверка: integration.

Приемка AT-TST-007: Release receipt содержит оба exit code 0.

Свидетельство: `CP12/evidence/TST-007`; command/result/hash либо manual review record.

**TST-008 — Подтвердить GitHub CI для точного итогового commit.**

Checkpoint: CP12. Приоритет: MUST. Проверка: manual.

Приемка AT-TST-008: Ссылка на run совпадает с release SHA, не с предыдущим green run.

Свидетельство: `CP12/evidence/TST-008`; command/result/hash либо manual review record.

**TST-009 — Проверить no-CFB путь в чистом workspace.**

Checkpoint: CP12. Приоритет: MUST. Проверка: browser.

Приемка AT-TST-009: Release smoke не использует старые patient caches или atlas.

Свидетельство: `CP12/evidence/TST-009`; command/result/hash либо manual review record.

**TST-010 — Закрыть каждый MUST evidence ссылкой.**

Checkpoint: CP12. Приоритет: MUST. Проверка: manual.

Приемка AT-TST-010: Acceptance matrix не содержит pass без artifact/test receipt.

Свидетельство: `CP12/evidence/TST-010`; command/result/hash либо manual review record.

### PUB Публикационные материалы

**PUB-001 — Подготовить методы и результаты статьи A по фактическим измерениям.**

Checkpoint: CP11. Приоритет: MUST. Проверка: manual.

Приемка AT-PUB-001: Каждая quantitative claim связана с immutable benchmark artifact.

Свидетельство: `CP11/evidence/PUB-001`; command/result/hash либо manual review record.

**PUB-002 — Подготовить методы и результаты статьи B по frozen protocol.**

Checkpoint: CP11. Приоритет: MUST. Проверка: manual.

Приемка AT-PUB-002: Primary statistic и failures совпадают с S-B, включая negative outcomes.

Свидетельство: `CP11/evidence/PUB-002`; command/result/hash либо manual review record.

**PUB-003 — Сгенерировать publication figures из analysis script.**

Checkpoint: CP11. Приоритет: MUST. Проверка: science.

Приемка AT-PUB-003: Figure provenance содержит source table hash и rendering settings.

Свидетельство: `CP11/evidence/PUB-003`; command/result/hash либо manual review record.

**PUB-004 — Разделить опубликованные аналоги и собственный вклад.**

Checkpoint: CP11. Приоритет: MUST. Проверка: manual.

Приемка AT-PUB-004: Related work не приписывает TumorTwin features автору проекта.

Свидетельство: `CP11/evidence/PUB-004`; command/result/hash либо manual review record.

**PUB-005 — Раскрыть AI assistance и проверки корректности по правилам выбранного журнала.**

Checkpoint: CP11. Приоритет: MUST. Проверка: manual.

Приемка AT-PUB-005: AUTHORSHIP_AND_AI.md содержит реальные роли и verification, без фиктивных авторов.

Свидетельство: `CP11/evidence/PUB-005`; command/result/hash либо manual review record.

**PUB-006 — Указать ограничения моделей и данных в обеих статьях.**

Checkpoint: CP11. Приоритет: MUST. Проверка: manual.

Приемка AT-PUB-006: Limitations перечисляет synthetic geometry, assumptions и отсутствие clinical proof.

Свидетельство: `CP11/evidence/PUB-006`; command/result/hash либо manual review record.

**PUB-007 — Подготовить quickstart для нового исследователя.**

Checkpoint: CP12. Приоритет: MUST. Проверка: manual.

Приемка AT-PUB-007: Fresh user может подготовить case и повторить baseline по инструкции.

Свидетельство: `CP12/evidence/PUB-007`; command/result/hash либо manual review record.

**PUB-008 — Подготовить changelog и known limitations release.**

Checkpoint: CP12. Приоритет: MUST. Проверка: manual.

Приемка AT-PUB-008: Документы различают implemented, measured, unverified и LATER.

Свидетельство: `CP12/evidence/PUB-008`; command/result/hash либо manual review record.

**PUB-009 — Подготовить compact reproduction archive без запрещенных assets.**

Checkpoint: CP12. Приоритет: MUST. Проверка: integration.

Приемка AT-PUB-009: Архив содержит manifests, scripts/config refs, metrics и hashes.

Свидетельство: `CP12/evidence/PUB-009`; command/result/hash либо manual review record.

**PUB-010 — Сохранить статус исследования отдельно от статуса ПО.**

Checkpoint: CP12. Приоритет: MUST. Проверка: manual.

Приемка AT-PUB-010: Если study incomplete, project не помечен fully complete.

Свидетельство: `CP12/evidence/PUB-010`; command/result/hash либо manual review record.

**PUB-011 — Указать synthetic longitudinal forecasting limitations.**

Checkpoint: CP11. Приоритет: MUST. Проверка: manual.

Приемка AT-PUB-011: Результат не называется проверкой прогноза на реальных пациентах.

Свидетельство: `CP11/evidence/PUB-011`; command/result/hash либо manual review record.


## 27. Сводная прослеживаемость

| Checkpoint | MUST требований | Граница приемки |
|---|---:|---|
| CP00 | 8 | Все назначенные IDs и evidence выхода раздела 17 |
| CP01 | 8 | Все назначенные IDs и evidence выхода раздела 17 |
| CP02 | 18 | Все назначенные IDs и evidence выхода раздела 17 |
| CP03 | 20 | Все назначенные IDs и evidence выхода раздела 17 |
| CP04 | 32 | Все назначенные IDs и evidence выхода раздела 17 |
| CP05 | 23 | Все назначенные IDs и evidence выхода раздела 17 |
| CP06 | 45 | Все назначенные IDs и evidence выхода раздела 17 |
| CP07 | 30 | Все назначенные IDs и evidence выхода раздела 17 |
| CP08 | 25 | Все назначенные IDs и evidence выхода раздела 17 |
| CP09 | 14 | Все назначенные IDs и evidence выхода раздела 17 |
| CP10 | 13 | Все назначенные IDs и evidence выхода раздела 17 |
| CP11 | 7 | Все назначенные IDs и evidence выхода раздела 17 |
| CP12 | 13 | Все назначенные IDs и evidence выхода раздела 17 |

CSV [02_REQUIREMENTS.csv](02_REQUIREMENTS.csv) содержит тот же реестр; [07_ACCEPTANCE_TRACKER.csv](07_ACCEPTANCE_TRACKER.csv) — начальный журнал статусов. После реализации статусы изменяются только в tracker/progress и evidence; нормативный текст требования не переписывается ради результата.

## 28. Указатель источников

Полные библиографические сведения, уровень доступа и ограничения анализа: [03_RESEARCH_BASIS.md](03_RESEARCH_BASIS.md).

- [S01](https://link.springer.com/article/10.1186/s12911-026-03520-2)
- [S02](https://oncologymodelinggroup.github.io/TumorTwin/tutorials/HGG_Demo/)
- [S03](https://github.com/OncologyModelingGroup/TumorTwin/blob/bedf90a6d47ba48cf5cdb25901967d84730061d1/LICENSE.md)
- [S04](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2023.1222612/full)
- [S05](https://arxiv.org/abs/2505.08927)
- [S06](https://ohsu.elsevierpure.com/en/publications/mri-based-bayesian-personalization-of-a-tumor-growth-model/)
- [S07](https://pmc.ncbi.nlm.nih.gov/articles/PMC3784027/)
- [S08](https://ascopubs.org/doi/abs/10.1200/JCO.23.01059)
- [S09](https://www.cancerimagingarchive.net/collection/cfb-gbm/)
- [S10](https://salib.readthedocs.io/en/stable/api/SALib.sample.morris.html)
- [S11](https://www.sqlite.org/wal.html)
- [S12](https://joss.readthedocs.io/en/latest/review_criteria.html)
