# Реорганизация репозитория и оптимизация загрузки

Дата 6 ноября 2026 года. База e6ccf399ceb85d37c891ce053f631e5706bbef6b. Работа объединяет актуальную исследовательскую ветку с основной и интегрирует ТЗ 2.0. Новая лаборатория по ТЗ не реализована этой уборкой.

## Документация

- В `docs/lab/` размещен полный проверенный пакет ТЗ: 256 требований, 54 UI requirements, 16 use cases, 13 checkpoints.
- Версия 1 и старый progress перемещены в `docs/lab/archive/`; прежние три пути оставлены небольшими совместимыми указателями.
- Полное прежнее README сохранено как `docs/patients/README.md` с корректными относительными ссылками.
- Корневое README стало точкой входа в актуальную работу. `docs/README.md` индексирует текущие документы и сохраненные исследования.
- Старые scientific reports, frozen configs и математические модели сохранены. Проверены SHA-256 49 защищенных файлов: содержимое не изменено.

## Код и директории

- MRI и 3D компоненты собраны в `frontend/src/components/viewer/`.
- Anatomy panel расположен в `components/anatomy/`, navigation — в `components/layout/`.
- Семь CSS-файлов собраны в `frontend/src/styles/` без изменения стилей.
- Удалены только неиспользуемые scaffold assets: `src/assets/hero.png` и `public/icons.svg`; ссылок в исходниках не было. Favicon и действующие icons сохранены.
- Исторические Python entry points, модели, tests и experiments не удалены: они используются публичными контрактами или воспроизведением исследований. Категории пояснены в `scripts/README.md` и `experiments/README.md`.
- Уточнены ignore rules для generated TypeScript и browser diagnostics.

## Измеренная оптимизация

3D viewers используют React lazy import, Suspense и локальную error boundary. VTK загружается при открытии 3D; ошибка загрузки не уничтожает остальные режимы. Raw entry JavaScript уменьшился с 1088.96 kB до 321.24 kB, примерно на 70.5%. Gzip entry: 300.11 → 93.85 kB. Полная совокупность chunks не уменьшена пропорционально: renderer по-прежнему нужен при открытии 3D. Предупреждение о крупном отложенном VTK chunk остается.

Public exports `gbm_twin.workflows` сохранены, но их модули импортируются по обращению через lazy export table. Независимая проверка сравнивает каждый публичный объект с исходным module symbol. Lightweight import больше не подгружает NumPy/SciPy/pandas/matplotlib автоматически.

Локальная проба Windows/Python 3.13, три новых процесса на вариант; время включает запуск Python:

| Импорт | До median s | После median s |
|---|---:|---:|
| workflows.repository | 0.8894 | 0.0868 |
| workflows | 0.9015 | 0.0472 |

Это измерение времени импорта на данной машине, не ускорение solver или доказательство улучшения научной точности.

## Зависимости

`npm audit fix --ignore-scripts` обновил 24 пакета в рамках существующих version ranges. Vite: 8.3.0 → 8.3.6. Четыре high предупреждения устранены. Audit production dependencies: 0 предупреждений. Полный dev audit оставляет 10 moderate предупреждений в ESLint/minimatch цепочке; предложенный npm force downgrade является несовместимым изменением, поэтому автоматически не применялся. Python numerical dependencies и frozen scientific settings не обновлялись.

## Проверки

- Полная Python suite: 573 passed, 57 dependency warnings.
- Ruff: passed.
- Frontend ESLint: passed.
- TypeScript и Vite production build: passed.
- Portable spec manifest и 256 пар requirement/acceptance: проверены.
- Сохранность 49 protected model/config/report files: проверена.
- CI нового PR должен пройти на точном опубликованном commit перед merge; статус проверяется в GitHub.

Клинические изображения и новые scientific studies не загружались и не запускались. Интерактивный viewer с реальными пациентскими данными этим проходом не проверен: локальных volumes нет. Сборка проверяет импорты и типы, но не заменяет будущий browser acceptance из ТЗ.
