# Проверка актуальности и границ самостоятельного вклада

Пакет GBM Digital Twin Research Lab 2.0. Подготовлено 06.11.2026; поиск и проверка источников 05–06.11.2026. Это целевой обзор для проектирования исследования. Он не исчерпывает всю литературу и не доказывает отсутствие аналогов.

## Вывод

Задача актуальна как инженерно-исследовательская: нужны воспроизводимые эксперименты, проверка вычислений и объяснимая устойчивость выводов. Общая идея цифрового двойника, UQ, виртуальных когорт или сравнения лечения уже не является самостоятельной новизной. Ближайшие работы существенно пересекаются с прежним широким замыслом. Поэтому ТЗ требует на CP01 конкретную матрицу отличий, а затем два проверяемых результата: software lifecycle/fidelity и scoped robustness experiment. Утверждение о публикационной пригодности будет зависеть от фактических результатов и выбранного журнала.

## Первичные научные источники

### S01 TumorTwin 2026

Kapteyn et al. TumorTwin: a Python framework for patient-specific digital twins in oncology. BMC Medical Informatics and Decision Making 26, 237. DOI 10.1186/s12911-026-03520-2.

Источник: https://link.springer.com/article/10.1186/s12911-026-03520-2

Доступ: открыта страница публикации, abstract и описание software contributions. Работа уже предлагает modular/differentiable framework, patient data structures и parallel computations. Следствие для проекта: реализацию модели, калибровку и gradients нельзя приписывать новому UI. Авторская synthetic demonstration не является доказательством clinical effectiveness нашего средства.

### S02 Author HGG workflow и данные

Tutorial: https://oncologymodelinggroup.github.io/TumorTwin/tutorials/HGG_Demo/

Gradients: https://oncologymodelinggroup.github.io/TumorTwin/tutorials/HGG_Gradients/

Pinned case JSON: https://github.com/OncologyModelingGroup/TumorTwin/blob/bedf90a6d47ba48cf5cdb25901967d84730061d1/input_files/HGG_demo_001/HGG_demo_001.json

Доступ: просмотрены tutorial и JSON через GitHub connector. Case содержит longitudinal visits, RT и CT. Tutorial включает initialization, numerical solver, calibration, alternative treatment и gradient calculations. Следствие: полная trajectory и event semantics должны воспроизводиться; старый endpoint-only CFB adapter не является готовой faithful lab integration. Конкретные versions и defaults проверяются в pinned code на CP02–CP03.

### S03 UT Austin Research License

https://github.com/OncologyModelingGroup/TumorTwin/blob/bedf90a6d47ba48cf5cdb25901967d84730061d1/LICENSE.md

Доступ: прочитан полный текст через GitHub connector. Разделы 2–3 задают grant, ограничения использования/передачи и условия производных работ. Следствие: отдельное окружение не отменяет ограничений, публичное распространение engine/demo не предполагается разрешенным. В проекте требуется документировать способы использования; не выдавать этот обзор за юридическое заключение.

### S04 Risk-aware HGG twin 2023

Chaudhuri et al. Predictive digital twin for optimizing patient-specific radiotherapy regimens under uncertainty in high-grade gliomas. Frontiers in Artificial Intelligence 6:1222612. DOI 10.3389/frai.2023.1222612.

https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2023.1222612/full

Доступ: открыта полная страница, изучены abstract, formulation, uncertainty propagation и discussion. Работа включает Bayesian personalization и risk-based RT optimization на in silico cohort. Следствие: нельзя заявлять первенство учета неопределенности и сценарной терапии. ТЗ не пытается воспроизвести всю optimization методику; сравнение ее scope с нашим ограниченным study обязательно.

### S05 Пространственный twin и количественная неопределенность

Pash, Villa, Hormuth II, Yankeelov, Willcox. Predictive Digital Twins with Quantified Uncertainty for Patient-Specific Decision Making in Oncology. arXiv:2505.08927, 2025.

https://arxiv.org/abs/2505.08927

Доступ: проверены abstract и bibliographic record. Abstract описывает spatial reaction–diffusion, statistical inverse problem, sparse/noisy imaging и uncertainty propagation. Полный разбор methods не завершен в этом пакете; он обязателен перед окончательным novelty claim на CP01. Поисковый результат также указывает журнальную работу 2026 года; актуальные final bibliographic details нужно проверить, прежде чем цитировать ее как окончательную версию. Следствие: «учет неопределенности пространственного twin» слишком широк для самостоятельного вклада.

### S06 Идентифицируемость параметров

Lê et al. MRI Based Bayesian Personalization of a Tumor Growth Model. IEEE Transactions on Medical Imaging 35(10), 2329–2339, 2016. DOI 10.1109/TMI.2016.2561098.

https://ohsu.elsevierpure.com/en/publications/mri-based-bayesian-personalization-of-a-tumor-growth-model/

Доступ: проверена авторская институциональная запись и abstract. В работе обсуждаются uncertainty, parameter correlations и несколько допустимых modes. Следствие: уникальный минимум coarse grid не заменяет содержательную оценку неопределенности. Этот релиз не требует собственной Bayesian calibration, но обязан корректно называть используемые диагностические показатели.

### S07 Основания PI и PIRT

Rockne et al. A mathematical model for brain tumor response to radiation therapy. Journal of Mathematical Biology 58, 561–578, 2009. DOI 10.1007/s00285-008-0219-6.

https://pmc.ncbi.nlm.nih.gov/articles/PMC3784027/

Доступ: открыта полная статья. Это первоисточник для семейства tumor growth/RT моделей. Следствие: PDE/RT являются существующей научной основой; изменения saturation semantics требуют нового model definition, а не скрытого исправления frozen experiments. Новый lab adapter должен проверять именно выбранный pinned engine, не смешивать различные treatment equations.

### S08 Ограничения оценки ответа по МРТ

Wen et al. RANO 2.0: Update to the Response Assessment in Neuro-Oncology Criteria for High- and Low-Grade Gliomas in Adults. JCO, 2023. DOI 10.1200/JCO.23.01059.

https://ascopubs.org/doi/abs/10.1200/JCO.23.01059

Доступ: проверены abstract/search record; прямой доступ к странице полного текста ограничен. Документ указывает на необходимость подтверждения progression в определенных post-RT условиях. Следствие: расчетный burden и MRI response не смешиваются с диагнозом и survival. Пакет не устанавливает клинический response classifier.

### S09 CFB-GBM

Официальная коллекция TCIA: https://www.cancerimagingarchive.net/collection/cfb-gbm/

DOI 10.7937/v9pn-2f72. Доступ: проверено описание version 4, состава imaging и metadata. Полная коллекция не требуется для первого laboratory release. Ее отсутствие на диске отражается как unavailable optional workspace, а не повод заново скачивать коллекцию. Новая clinical validation требует отдельного протокола.

## Первичные технические источники

### S10 Morris sampling

https://salib.readthedocs.io/en/stable/api/SALib.sample.morris.html

https://salib.readthedocs.io/en/stable/_modules/SALib/analyze/morris.html

Доступ: проверены официальная API документация и описание реализации. Для точного повторения фиксируются version, seed, levels и sample matrix. Morris используется как screening; оценка зависит от заданного пространства факторов. ТЗ не объявляет этот известный метод собственным новым алгоритмом.

### S11 SQLite

https://www.sqlite.org/wal.html

https://www.sqlite.org/atomiccommit.html

Доступ: проверены официальные материалы о WAL/atomic commit. Следствие: постоянная очередь и бэкап должны учитывать transactional state; копия единственного .db файла при active WAL не считается гарантированно согласованной копией. Технический выбор SQLite — инженерное решение локальной версии, а не научный вклад сам по себе.

### S12 Критерии исследовательского программного обеспечения

https://joss.readthedocs.io/en/latest/review_criteria.html

Доступ: открыта официальная документация. Она требует обоснования потребности/связи с аналогами, design choices, функциональных проверок и evidence research significance. Здесь она используется как ориентир software paper. Eligibility, licensing и требования конкретного журнала проверяются отдельно; подача в JOSS не входит в ТЗ.

## Внутренние проверенные материалы

- Рабочая версия: https://github.com/VeregaS/gbm-digital-twin/tree/e6ccf399ceb85d37c891ce053f631e5706bbef6b
- Предыдущее ТЗ: https://github.com/VeregaS/gbm-digital-twin/blob/e6ccf399ceb85d37c891ce053f631e5706bbef6b/docs/IN_SILICO_LAB_TECHNICAL_SPEC.md
- Progress: https://github.com/VeregaS/gbm-digital-twin/blob/e6ccf399ceb85d37c891ce053f631e5706bbef6b/docs/IN_SILICO_LAB_PROGRESS.md
- Negative validation: https://github.com/VeregaS/gbm-digital-twin/blob/e6ccf399ceb85d37c891ce053f631e5706bbef6b/docs/STAGE10_VALIDATION_RESULT.md
- Exact-commit CI: https://github.com/VeregaS/gbm-digital-twin/actions/runs/39030329421

Внутренние scientific reports прочитаны, но отсутствующие raw artifacts независимо не проверены. Локальные тесты и synthetic probes выполнены в предыдущей части текущего чата. Новые clinical calculations при подготовке ТЗ не запускались.

## Как обновлять обзор на CP01

Сохранить query strings: `glioblastoma digital twin reproducibility scenario uncertainty`, `TumorTwin sensitivity treatment comparison`, `radiotherapy ranking robustness numerical uncertainty`, плюс точные названия S01/S04/S05. Проверить ссылки и новые версии работ до даты реализации. Искать не только совпадающие слова, но и одинаковые questions/endpoints/baselines. Наличие абстрактного интереса к digital twins не является достаточным основанием публикационной заявки.

Минимальная comparison matrix: источник/version; полный текст проверен да/нет; disease/data; модель; personalization; scenarios; UQ method; numerical error; run provenance; reproducibility artifacts; resource budget; основной результат; отличие нашего claim; verification target. Unknown поля так и записывать. Не делать вывод об отсутствии функции из молчания abstract.

## Границы утверждений

Допустимо после выполнения: «Разработано и проверено средство…», «В заданной модели и virtual distribution обнаружено…», «При этих settings ranking не разрешается численно…». До эксперимента допустимо только «предлагается проверить». Недопустимо без отдельного доказательства: «улучшает лечение пациентов», «впервые учитывает неопределенность», «реалистичная виртуальная популяция», «доказанная точность реального индивидуального прогноза», «гарантирована публикация в ВАК/Scopus».
