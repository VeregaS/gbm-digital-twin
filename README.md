# GBM Digital Twin

Исследовательское программное средство для моделирования роста опухоли, сценарных экспериментов и работы с продольными МРТ. Основная ветка — `main`.

## С чего начать

- [Действующее ТЗ лаборатории 2.0](docs/lab/01_TECHNICAL_SPEC.md): 256 требований, 16 use cases и 13 checkpoints.
- [Гайд нейросети исполнителя](docs/lab/04_AGENT_START.md) и [фактический прогресс](docs/lab/PROGRESS.md).
- [Навигация по документации](docs/README.md).
- [Существующее пространство пациентов и завершенные исследования](docs/patients/README.md).
- [Отчет об уборке и оптимизации](docs/REPOSITORY_CLEANUP.md).

## Фактическое состояние

В репозитории есть Python-модели, калибровка, freeze/reveal workflows, FastAPI и React-интерфейс для сохраненных patient-specific результатов. Новая лаборатория TumorTwin — следующий этап по ТЗ; постоянная lab queue, scenarios и studies еще не реализованы.

Последняя внутренняя проверка Stage 10 не пройдена: mean Dice 0.7084 против 0.7426 у persistence на 16 пациентах. [Исходный отчет](docs/STAGE10_VALIDATION_RESULT.md) и frozen configs сохранены. Результат не подтверждает клиническое преимущество модели.

Пользователь удалил тяжелые данные пациентов. Исходный код и тесты не требуют полного скачивания коллекции. Patient workspace без данных остается недоступным; это ожидаемое состояние. Новое ТЗ предусматривает небольшой авторский synthetic HGG case и явную подготовку необходимых файлов.

## Установка и проверки

Python 3.11+; для pinned TumorTwin окружение создается отдельно по ТЗ.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest -q
```

Frontend использует Node 24 в CI:

```powershell
cd frontend
npm ci
npm run lint
npm run build
npm run dev
```

Backend:

```powershell
uvicorn gbm_twin.api.app:app --reload
```

Настройка CFB-путей, старых artifacts и atlas — в [patient workspace guide](docs/patients/README.md). Не скачивать их для подготовки лабораторного кода.

## Структура

```text
src/gbm_twin/   модели, данные, API, CLI и научные workflows
frontend/src/  api, components/layout, components/viewer,
               components/anatomy, components/workbench, styles
configs/       зафиксированные настройки datasets и исследований
docs/lab/      действующее ТЗ, приемка, progress и архив версии 1
docs/patients/ сохраненное руководство patient workspace
scripts/       запускаемые команды и служебные инструменты
experiments/   воспроизводимые диагностические и исторические эксперименты
tests/         проверки моделей, контрактов, API и workflows
```

Research only: модельные сценарии не являются назначением лечения. Медицинские данные, generated results и restricted upstream assets не коммитятся. Перед реализацией прочитать [ТЗ](docs/lab/01_TECHNICAL_SPEC.md) и текущий progress; история экспериментов сохраняется.
