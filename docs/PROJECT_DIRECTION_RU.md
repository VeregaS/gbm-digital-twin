# Вектор проекта GBM Digital Twin

## Рабочая формулировка темы

**Разработка программно-алгоритмического средства на базе исследовательского цифрового двойника глиобластомы для моделирования динамики опухоли и прогнозирования ответа на терапию по продольным МРТ-данным.**

Короткое позиционирование проекта:

**GBM Digital Twin — исследовательская платформа для patient-specific in silico моделирования глиобластомы.**

Термин «исследовательский» принципиален: проект не позиционируется как клиническая система поддержки принятия решений и не должен делать клинических обещаний без отдельной внешней валидации.

## Что является основной целью

Главная цель проекта — не изобрести одну новую математическую модель с нуля, а создать **воспроизводимое программно-алгоритмическое средство**, которое объединяет:

- patient-specific математические модели динамики глиобластомы;
- продольные МРТ и данные лечения;
- калибровку индивидуальных параметров;
- assimilation последовательных наблюдений;
- прогноз будущего состояния;
- in silico эксперименты;
- сравнение семейств моделей и baseline-методов;
- строгий freeze/reveal evaluation без утечки t2;
- анализ чувствительности, неопределённости и failure modes;
- программный API и исследовательский GUI.

## Научное позиционирование

Работа является в первую очередь **инженерно-исследовательской**, а не чисто математической.

Ценность проекта должна строиться вокруг единой исследовательской платформы, в которой можно:

1. реализовывать и сравнивать существующие и новые mechanistic models;
2. персонализировать модели под конкретного пациента;
3. проводить воспроизводимые in silico эксперименты;
4. проверять модели относительно сильных baseline-методов;
5. анализировать, где и почему модель ошибается;
6. постепенно переходить от development к internal validation, untouched holdout и external validation.

Отрицательные результаты моделей должны сохраняться как полноценные научные результаты и использоваться для следующего mechanistic hypothesis, а не скрываться через post-hoc tuning.

## Что понимается под digital twin

Исследовательский цифровой двойник здесь — это связка:

**конкретный пациент + longitudinal observations + patient-specific state/parameters + assimilation + прогноз будущего состояния.**

Не следует называть текущую систему clinical digital twin или системой поддержки медицинских решений.

## Что понимается под in silico

**In silico** — это вычислительный эксперимент на модели.

«Виртуальный пациент» — возможный объект такого эксперимента, но эти термины не являются синонимами.

В перспективе:

population distributions → virtual patients → virtual cohort → in silico trial.

## Ключевые научные приоритеты

Приоритет №1 — доказать predictive value на новых пациентах относительно простых baseline-методов, прежде всего persistence.

Главные направления развития модели:

- delayed post-radiotherapy response;
- более корректный MRI observation model;
- multimodal MRI: T1Gd, FLAIR, ADC/DWI;
- spatial RTDOSE;
- uncertainty / ensemble prediction;
- sensitivity analysis;
- conservative gating между mechanistic twin и baseline;
- только после достаточной идентифицируемости — дополнительные treatment mechanisms, включая chemotherapy.

Нельзя добавлять patient-specific свободные параметры только ради улучшения уже раскрытого t2.

## Текущее научное состояние после Stage 10

Stage 10 завершил текущий development-only mechanistic cycle.

На тех же 24 уже раскрытых development patients exact Stage 9 v2 control
воспроизведён с mean Dice `0.681404`, mean delta vs persistence
`-0.011792` и двумя catastrophic failures.

Pre-specified decoupled candidates `14/30/60 d` все устранили catastrophic
failures. По заранее заданному ranking выбран:

`stage10-decoupled-half-life-60d`.

Его development metrics:

- mean Dice = `0.696845`;
- median Dice = `0.755809`;
- mean delta vs persistence = `+0.003649`;
- mean RVE = `0.663907`;
- mean HD95 = `11.0844 mm`;
- catastrophic failures = `0`;
- regression mean delta vs persistence = `+0.006040`;
- growth mean delta vs persistence = `+0.004390`.

Sealed selection SHA-256:

`2bff489685dd2d8ed9d28f8ce2abe55214475ade8ce287f73d0bc8e19f6b4326`.

Development evidence поддерживает гипотезу, что MRI-visible clearance и
persistent post-treatment occupancy не должны управляться одним latent state.
При этом `60 d` нельзя трактовать как подтверждённую биологическую константу:
это выбранный model-family setting. На новых reserve patients он не прошёл
validation gate, как описано ниже.

Два Stage 9 catastrophic cases — patients 108 и 205 — перестали быть
catastrophic under Stage 10. Это важный mechanistic signal, но он получен на
уже раскрытом development cohort и сам по себе не доказывает generalization.

## Завершённый checkpoint — reserve internal validation

2026-10-05 frozen модель прошла полный расчёт на исходных 16 reserve patients,
но **не прошла scientific validation gate**: mean Dice `0.708427` против
`0.742571` у persistence, mean delta `-0.034144`, catastrophic failures `2`
(patients `73`, `254`). Средние RVE и HD95 улучшились, median delta равен нулю,
но для advancement должны одновременно пройти все пять условий.

Sealed result SHA-256:
`f565a0713de52666b3c5a7624486b8bfa32280cb45b69fd3816c809d89aa885a`.
Полный [результат](STAGE10_VALIDATION_RESULT.md) и
[разбор ошибок](STAGE10_RESERVE_FAILURE_ANALYSIS.md) сохранены.

Текущий научный этап — development failure analysis без reserve tuning.
Аудит текущего predictive core и порядок следующего accuracy cycle:
[MODEL_CODE_AUDIT.md](MODEL_CODE_AUDIT.md). Код исправлен в части входных
проверок, геометрии, sealed cohort и воспроизводимости кэша; преимущество модели
по точности этим не установлено. Новые dynamics/calibration/observation
проверяются только в отдельном development protocol.
Эти 16 пациентов теперь раскрыты; 32 оставшихся reserve patients и untouched
holdout остаются закрытыми. Frozen Stage 10 не допускается к holdout.
Новая модель требует отдельного development cycle и нового заранее заданного
evaluation protocol. Ниже сохранены исходные условия завершённого checkpoint.

До открытия reserve outcomes модель была полностью зафиксирована:

- exact Stage 10 selection artifact;
- model id `stage10-decoupled-half-life-60d`;
- visible-damage half-life `60 d`;
- full inert retention;
- Stage 8 radiobiology и proliferation survival;
- observation model;
- calibration protocol;
- validation cohort selection;
- validation pass/fail criteria.

Первый checkpoint использует deterministic stratified subset из `16` из
`48` unopened reserve patients. Selection строится только по sealed audit
metadata; t2 не читается до записи validation-plan artifact.

Для каждого reserve patient D/rho разрешено персонализировать только по
`t0→t1`. После freeze D/rho открывается t2 и считается forecast.

Validation проходит только если одновременно:

- mean delta vs persistence > `0`;
- median delta vs persistence >= `0`;
- catastrophic failures = `0`;
- mean RVE не хуже persistence;
- mean HD95 не хуже persistence.

Bootstrap 95% CI paired mean delta выводится как uncertainty diagnostic, но не
используется для post-hoc model selection.

Если validation проходит, следующий шаг — untouched CFB holdout без изменения
модели. Если validation не проходит, revealed reserve cases можно
анализировать, но нельзя использовать для подбора Stage 10 half-life или
других frozen global parameters.

Conditional observation-model protocol остаётся подготовленным как будущий
development path. Его нельзя запускать как скрытый post-hoc tuning на reserve
outcomes.

Reference Fidelity v2 и Stage 9 остаются важными отрицательными/диагностическими
результатами, но текущий frozen predictive candidate — Stage 10 60 d.

## Направления развития платформы

После стабилизации predictive core проект должен развиваться как исследовательская платформа.

### Sensitivity / uncertainty workspace

Пользователь должен иметь возможность менять диапазоны параметров и видеть:

- влияние D, rho и treatment-response параметров;
- чувствительность прогноза;
- диапазон возможных траекторий;
- uncertainty bands / ensemble predictions.

### Model comparison workspace

Для одного пациента интерфейс должен позволять сравнивать:

- persistence;
- volume extrapolation;
- RD / PI;
- PIRT;
- treatment-aware model families;
- последующие версии digital twin.

Сравнение должно включать MRI t0/t1, prediction t2, observed t2, Dice, HD95, volume error, centroid distance и uncertainty.

### Virtual cohorts

Формулировку «формирование виртуальной когорты» следует использовать как основную только после появления реального генератора виртуальных пациентов.

Целевая архитектура:

population parameter distributions → sampling virtual patients → simulation → virtual cohort → in silico trials.

Это перспективное направление, но оно не должно подменять основную текущую задачу predictive validation на реальных longitudinal данных.

## Критерий успеха модели

Сложная модель не считается полезной только потому, что она иногда даёт высокий Dice.

Минимально требуется показать на новых пациентах:

- mean Dice лучше persistence;
- median Dice лучше persistence;
- HD95 и volume error не деградируют;
- улучшение не создаётся одним-двумя outlier cases;
- отсутствуют новые catastrophic failures;
- механизм улучшает именно те trajectory groups, для которых он был введён.

До выполнения этих условий untouched holdout и внешнюю Burdenko cohort нельзя расходовать на частые итерации.

## Стратегический roadmap

1. Надёжный patient-specific predictive core.
2. Mechanistic model-family selection и failure analysis.
3. Internal validation на новых CFB patients.
4. Untouched CFB holdout.
5. External validation на Burdenko.
6. Sensitivity + uncertainty analysis.
7. Исследовательский GUI/model-comparison workspace.
8. Virtual cohort generator.
9. In silico trial orchestration.
10. Reproducible research release.

Все архитектурные решения следует оценивать по трём вопросам:

1. Улучшает ли это научную корректность или predictive accuracy?
2. Повышает ли это воспроизводимость и скорость экспериментов?
3. Укрепляет ли это проект именно как исследовательское программно-алгоритмическое средство?

Если изменение не помогает ни одному из этих направлений, оно не является приоритетным.
