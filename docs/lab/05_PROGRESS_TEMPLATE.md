# Шаблон состояния реализации

Версия ТЗ 2.0. Дата создания 06.11.2026. Скопировать в repository `docs/lab/PROGRESS.md` при старте реализации.

## Фактическое текущее состояние

- current_checkpoint: CP00
- audited_commit: e6ccf399ceb85d37c891ce053f631e5706bbef6b
- actual_commit: NOT_CHECKED_AT_IMPLEMENTATION_START
- actual_branch: NOT_CHECKED_AT_IMPLEMENTATION_START
- local_changes: NOT_CHECKED_AT_IMPLEMENTATION_START
- lab_software_status: NOT_IMPLEMENTED_BY_THIS_SPEC
- scientific_study_status: NOT_STARTED
- publication_materials_status: NOT_STARTED
- historical_baseline: 571 tests + lint/build passed in audit; not lab acceptance
- patient_data: user reports removed; inspect locally, no automatic download
- current_next_action: CP00.1 inspect Git/instructions/local assets

## Checkpoints

| CP | Статус | Evidence | Commit | Следующий конкретный результат |
|---|---|---|---|---|
| CP00 | pending | — | — | Baseline и protected list |
| CP01 | pending | — | — | Comparison и contribution matrix |
| CP02 | pending | — | — | Source/environment/case manifests |
| CP03 | pending | — | — | Fidelity и measured budget |
| CP04 | pending | — | — | Contracts/storage/API |
| CP05 | pending | — | — | Durable executor failure matrix |
| CP06 | pending | — | — | No-CFB browser vertical slice |
| CP07 | pending | — | — | Pair comparison/export/replay/storage |
| CP08 | pending | — | — | Local/Morris/cohort |
| CP09 | pending | — | — | Frozen protocols S-A/S-B |
| CP10 | pending | — | — | Immutable outcomes и analysis |
| CP11 | pending | — | — | Материалы двух статей |
| CP12 | pending | — | — | Clean-workspace release |

Allowed statuses: pending, in_progress, accepted, blocked_dependency, invalidated. Blocked_dependency содержит exact dependency и independent work; это не разрешение пропустить MUST. Accepted требует evidence. Изменение принятой зависимости может invalidated downstream CP; reviewer фиксирует что требуется перепроверить.

## Запись evidence

```text
checkpoint:
requirement_ids:
acceptance_ids:
commit:
timestamp_utc:
input_versions_hashes:
changed_files:
commands_and_exit_codes:
artifacts_and_sha256:
observed_result:
limits_and_warnings:
decision: accepted | pending | failed
next_action:
```

## Запись change request

```text
change_id:
reason:
affected_requirements:
old_behavior:
new_behavior:
alternatives:
scientific_effect:
resource_effect:
verification:
user_decision_if_required:
new_protocol_version_if_required:
```

## Claims ledger

| Claim | Тип engineering/scientific | Разрешенный контекст | Evidence hash | Статус |
|---|---|---|---|---|
| Adapter matches pinned upstream | engineering | author synthetic case | pending | unverified |
| Runs survive restart through interruption/retry | engineering | local executor | pending | unverified |
| Scenario ranking stability | scientific | frozen synthetic distribution | pending | unverified |
| Individual clinical prediction accuracy | scientific | real longitudinal patients | отсутствует | вне этого релиза |

## Защищенное наследие

Сохранить Stage 10 failed reserve result и configs. Не использовать 16 exposed reserve для tuning. Не открывать 32 reserve и 21 holdout. Наличие/отсутствие файлов не меняет этих правил. Любой новый clinical study требует отдельного согласованного протокола.
