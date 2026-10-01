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

## Текущее научное состояние после Stage 9

Stage 9 подтвердил, что delayed post-radiotherapy state полезен как
mechanistic direction, но текущая однокомпартментная семантика недостаточна.

На 24 уже раскрытых development patients Stage 9 v2 улучшил mean Dice
относительно exact Stage 8 control с `0.667942` до `0.681404` и особенно
улучшил regression subgroup. При этом mean delta vs persistence остаётся
отрицательным (`-0.011792`), а две catastrophic failures сохраняются.

Ключевой диагностический результат: half-life `60 -> 90 -> 120` дней давал
монотонное улучшение, а `120 d` был выбран во всех 24 leave-one-out folds.
По заранее заданному stop rule этот поиск нельзя продолжать в сторону
`180/240/365 d`.

Это означает, что текущий damaged compartment нельзя трактовать как найденную
биологическую константу clearance. В существующей модели один параметр
одновременно управляет:

- исчезновением MRI-visible damaged burden;
- освобождением logistic carrying capacity.

Следующий приоритет predictive core — **развязать visible clearance и
post-treatment occupancy/growth suppression**. Для этого Stage 10 проверяет
минимальное расширение с отдельным MRI-invisible inert occupancy state на тех
же уже раскрытых development patients.

До завершения этого mechanistic diagnostic нельзя расходовать новые reserve
patients или untouched holdout.

## Reference-first checkpoint

После Stage 9 v2 проект временно остановил наращивание собственных latent
treatment states и провёл benchmark против опубликованной реализации
TumorTwin на тех же 24 уже раскрытых development patients.

Reference benchmark v1 дал:

- persistence mean Dice: `0.693196`;
- Stage 9 v2 mean Dice: около `0.681404`;
- TumorTwin frozen-kinetics mean Dice: `0.629097`;
- TumorTwin LM mean Dice: `0.637488`;
- TumorTwin frozen catastrophic failures: `5`;
- TumorTwin LM catastrophic failures: `5`.

Следовательно, простая замена собственного solver или grid/refinement
calibration на опубликованные TumorTwin ReactionDiffusion3D + LM не решает
текущую задачу при том же GTV-derived observation state.

Benchmark v1 не был полной репликацией HGG workflow, поэтому был выполнен
предварительно зарегистрированный **Reference Fidelity v2** на тех же уже
раскрытых 24 development patients.

Результат Reference Fidelity v2:

- ROI-cropped TumorTwin LM, 24 patients:
  mean Dice = `0.636752`, mean delta vs persistence = `-0.056445`,
  catastrophic failures = `5`;
- ROI-GTV на paired ADC subset, 9 patients:
  mean Dice = `0.575452`, catastrophic failures = `3`;
- TumorTwin-style ADC-derived enhancing cellularity на тех же 9 patients:
  mean Dice = `0.393779`, mean delta vs persistence = `-0.253006`,
  catastrophic failures = `5`.

ROI cropping не улучшил опубликованный reference относительно benchmark v1,
а ADC-derived branch в текущей постановке существенно ухудшил paired result.
Следовательно, ни один из двух заранее заданных критериев перехода к
calibration/observation rework не выполнен.

По pre-specified decision rule **Stage 10 теперь является следующим
development-only mechanistic diagnostic**. Он реализован как decoupling
MRI-visible damaged burden и MRI-invisible inert occupancy и использует только
те же 24 уже раскрытых development patients.

Stage 10 обязан:

- бит-в-бит воспроизвести sealed Stage 9 v2 control;
- проверить только заранее заданные half-life `14/30/60 d`;
- сохранить D/rho и radiobiology замороженными;
- продвигать decoupled candidate только при уменьшении catastrophic failures,
  улучшении regression subgroup и отсутствии material global/growth
  degradation.

Reference Fidelity v2 использовал ADC только на t0+t1 для пациентов
`25, 45, 65, 70, 76, 99, 112, 120, 214`. t2 ADC не загружался, raw FLAIR
не thresholded.

Reserve patients, untouched CFB holdout и Burdenko external-validation cohort
остаются закрыты до завершения Stage 10 и заморозки следующей структуры.

Stage 10 checkpoint автоматически формирует sealed JSON/CSV/SHA-256 и
human-readable `STAGE10_RESULT.md`. Если решение равно
`no_decoupled_candidate_advanced`, дальнейшее добавление RT compartments
останавливается. Следующий цикл заранее ограничен observation-layer работой,
описанной в `docs/OBSERVATION_MODEL_NEXT_CYCLE.md`: pre-t2 multimodal audit,
defensible FLAIR representation, ADC только как дополнительная информация и
uncertainty из near-optimal t0→t1 calibration solutions.

Если Stage 10 candidate проходит gate, сначала фиксируется структура модели и
пишется reserve-validation plan; новые reserve outcomes до этого не открываются.

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
