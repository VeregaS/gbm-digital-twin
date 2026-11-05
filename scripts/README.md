# Запускаемые инструменты

- `twin/` — CLI wrappers для freeze, evaluation, selections и Stage 8–10; логика находится в `src/gbm_twin/cli` и workflows.
- `reference/` — pinned TumorTwin environment, worker и reference checkpoints.
- `anatomy/` — экспериментальная регистрация и ручная проверка; не является зависимостью новой лаборатории.
- `cohort/`, `treatment/`, `audit_cfb_dataset.py` — диагностика доступности и метаданных.

Существующие команды и пути оставлены совместимыми. Не удалять wrappers как дубликаты: они являются пользовательскими entry points. Новый lab CLI добавлять по действующему ТЗ после проверки текущего checkpoint.
