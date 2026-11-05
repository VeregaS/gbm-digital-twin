# Baseline интеграции ТЗ 2.0

Дата 06.11.2026. Исходная ветка feat/twin-protocol, исходный HEAD e6ccf399ceb85d37c891ce053f631e5706bbef6b; main был 3f20086e800be5f15c8c022efec36f6c9da7e953. Main является предком исследовательской ветки; merge сохраняет историю без force push.

ТЗ, реестры и шаблоны внесены в docs/lab. Пользователь поручил загрузить ТЗ, объединить ветки и провести безопасную уборку. Эта работа не начинает реализацию scientific lab и не открывает защищенные данные. Все новые checkpoint statuses остаются pending до отдельной приемки.

В копии аудита не было пользовательских изменений; применимых дополнительных AGENTS.md не обнаружено в repository и проверенных родительских каталогах. При следующем запуске проверить фактический Git заново. Тяжелые данные пользователя удалены; наличие старых результатов на его исходном диске не подтверждено.

## Реальные reusable paths после уборки

- frontend/src/components/viewer: MedicalViewerPanel, TriPlanarViewer, ThreeDViewer, TwinThreeDViewer, DeferredViewer.
- frontend/src/components/anatomy: AnatomicalWarningsPanel.
- frontend/src/components/layout: Sidebar, Topbar, FunctionalNavigation, navigation.
- frontend/src/components/workbench: patient/twin/cohort views.
- frontend/src/styles: существующие стили без изменения содержимого.
- src/gbm_twin/workflows: прежний public API с lazy package exports.
- source models, CLI, scripts/reference и scientific workflows сохранены.

## Проверки

Исторический baseline: 571 tests. После уборки: 573 tests (добавлены две проверки lazy imports/public export compatibility), Ruff, ESLint и build passed. Точные измерения и ограничения находятся в [отчете](../REPOSITORY_CLEANUP.md).

Полный pinned TumorTwin engine и авторский case в этом проходе не готовились. Lab queue/scenario/study endpoints по ТЗ еще не реализованы. Следующая работа по ТЗ начинается с CP00 review и CP01 literature/contribution gate, а не с повторного CFB расчета.
