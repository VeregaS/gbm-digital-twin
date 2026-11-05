import {
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Download,
} from "lucide-react";

import {
  fetchTwinCohortAnalysis,
  twinAnalysisCsvUrl,
  twinAnalysisJsonUrl,
} from "../../api/twin";

import type {
  TwinCohortAnalysis,
  TwinCohortPatientError,
  TwinCorrelation,
} from "../../api/twin";


type TwinCohortAnalysisTabProps = {
  selectedPatientId: number;
};


type AnalysisRequest =
  | {
      status: "success";
      analysis: TwinCohortAnalysis;
    }
  | {
      status: "error";
      error: string;
    };


type ScatterMode =
  | "horizon"
  | "growth"
  | "calibration";


type PatientFilter =
  | "all"
  | "qc"
  | "non_identifiable"
  | "boundary"
  | "worse_than_persistence";


function TwinCohortAnalysisTab({
  selectedPatientId,
}: TwinCohortAnalysisTabProps) {
  const [
    request,
    setRequest,
  ] = useState<
    AnalysisRequest | null
  >(null);

  const [
    scatterMode,
    setScatterMode,
  ] = useState<ScatterMode>(
    "horizon",
  );

  const [
    filter,
    setFilter,
  ] = useState<PatientFilter>(
    "all",
  );

  useEffect(() => {
    let cancelled = false;

    fetchTwinCohortAnalysis()
      .then((analysis) => {
        if (cancelled) {
          return;
        }

        setRequest({
          status: "success",
          analysis,
        });
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return;
        }

        setRequest({
          status: "error",
          error:
            error instanceof Error
              ? error.message
              : "Не удалось загрузить анализ когорты",
        });
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const analysis =
    request?.status === "success"
      ? request.analysis
      : null;

  const filteredPatients =
    useMemo(() => {
      if (analysis === null) {
        return [];
      }

      const selected =
        analysis.patients.filter(
          (patient) => {
            if (filter === "qc") {
              return (
                patient.qc_warning_codes.length
                > 0
              );
            }

            if (
              filter
              === "non_identifiable"
            ) {
              return !patient.calibration_identifiable;
            }

            if (filter === "boundary") {
              return (
                patient.diffusion_at_boundary
                || patient.proliferation_at_boundary
              );
            }

            if (
              filter
              === "worse_than_persistence"
            ) {
              return (
                patient.twin_minus_persistence_dice
                < 0
              );
            }

            return true;
          },
        );

      return [
        ...selected,
      ].sort(
        (first, second) =>
          first.twin_dice
          - second.twin_dice,
      );
    }, [
      analysis,
      filter,
    ]);

  if (request === null) {
    return (
      <section
        className="workspace-state"
      >
        <strong>
          Загружаем научный анализ когорты
        </strong>

        <span>
          Читаем зафиксированный error-analysis artifact…
        </span>
      </section>
    );
  }

  if (request.status === "error") {
    return (
      <section
        className="twin-analysis-missing"
      >
        <strong>
          Анализ когорты ещё не построен
        </strong>

        <p>
          Этот раздел читает отдельный воспроизводимый артефакт и не пересчитывает MRI при открытии страницы.
        </p>

        <code>
          python scripts\twin\analyze_cohort.py --repo-root .
        </code>

        <small>
          Backend ответил: {request.error}
        </small>
      </section>
    );
  }

  const loadedAnalysis = request.analysis;
  const summary = loadedAnalysis.summary;

  return (
    <div
      className="twin-analysis-stack"
    >
      <section
        className="twin-analysis-intro"
      >
        <div>
          <span>
            SCIENTIFIC ERROR ANALYSIS
          </span>

          <strong>
            Где цифровой двойник ошибается и с чем это связано
          </strong>

          <p>
            Это описательный анализ уже зафиксированных прогнозов. Корреляции помогают найти направления для следующей итерации модели, но сами по себе не доказывают причинность.
          </p>
        </div>

        <div
          className="twin-analysis-actions"
        >
          <a
            href={twinAnalysisJsonUrl}
            className="twin-export-link"
            download
          >
            <Download size={14} />
            JSON
          </a>

          <a
            href={twinAnalysisCsvUrl}
            className="twin-export-link"
            download
          >
            <Download size={14} />
            CSV
          </a>
        </div>
      </section>

      <section
        className="twin-analysis-summary-grid"
      >
        <SummaryCard
          label="Средний Dice"
          value={formatNumber(
            summary.mean_twin_dice,
            3,
          )}
          hint="качество Twin по всей когорте"
        />

        <SummaryCard
          label="Δ Dice к persistence"
          value={formatSigned(
            summary.mean_delta_vs_persistence,
          )}
          hint="среднее преимущество или проигрыш"
        />

        <SummaryCard
          label="QC-флаги"
          value={
            `${summary.qc_flagged_count}`
            + ` / ${summary.patient_count}`
          }
          hint="пациенты с geometry/mask предупреждениями"
        />

        <SummaryCard
          label="Неидентифицируемая калибровка"
          value={
            `${summary.calibration_non_identifiable_count}`
            + ` / ${summary.patient_count}`
          }
          hint="D и ρ недостаточно устойчиво различимы"
        />

        <SummaryCard
          label="Параметр на границе поиска"
          value={
            `${summary.calibration_boundary_count}`
            + ` / ${summary.patient_count}`
          }
          hint="возможный сигнал слишком узкой search grid"
        />
      </section>

      <section
        className="twin-analysis-panel"
      >
        <header
          className="twin-analysis-panel-header"
        >
          <div>
            <strong>
              Связь ошибок с характеристиками прогноза
            </strong>

            <span>
              Каждая точка — один пациент; по вертикали всегда Dice цифрового двойника.
            </span>
          </div>

          <div
            className="twin-chip-row"
          >
            <ScatterButton
              active={scatterMode === "horizon"}
              label="Горизонт прогноза"
              onClick={() =>
                setScatterMode("horizon")
              }
            />

            <ScatterButton
              active={scatterMode === "growth"}
              label="Изменение объёма t1→t2"
              onClick={() =>
                setScatterMode("growth")
              }
            />

            <ScatterButton
              active={scatterMode === "calibration"}
              label="Dice калибровки"
              onClick={() =>
                setScatterMode("calibration")
              }
            />
          </div>
        </header>

        <CohortScatterPlot
          patients={loadedAnalysis.patients}
          mode={scatterMode}
          selectedPatientId={selectedPatientId}
        />

        <CorrelationExplanation
          mode={scatterMode}
          correlation={
            correlationForMode(
              loadedAnalysis,
              scatterMode,
            )
          }
        />
      </section>

      <section
        className="twin-analysis-two-column"
      >
        <article
          className="twin-analysis-panel"
        >
          <header
            className="twin-analysis-panel-header"
          >
            <div>
              <strong>
                Худшие случаи
              </strong>

              <span>
                Приоритет для визуального разбора и проверки assumptions.
              </span>
            </div>
          </header>

          <PatientIdList
            title="Минимальный Twin Dice"
            patientIds={
              summary.worst_twin_dice_patient_ids
            }
            selectedPatientId={selectedPatientId}
          />

          <PatientIdList
            title="Наибольший проигрыш persistence"
            patientIds={
              summary.worst_delta_vs_persistence_patient_ids
            }
            selectedPatientId={selectedPatientId}
          />
        </article>

        <article
          className="twin-analysis-panel"
        >
          <header
            className="twin-analysis-panel-header"
          >
            <div>
              <strong>
                По траектории объёма t1→t2
              </strong>

              <span>
                Группировка использует порог стабильности из analysis config.
              </span>
            </div>
          </header>

          <div
            className="twin-analysis-trajectory-list"
          >
            {summary.trajectory_groups.map(
              (group) => (
                <div
                  key={group.trajectory}
                >
                  <span>
                    {trajectoryLabel(
                      group.trajectory,
                    )}
                  </span>

                  <strong>
                    n={group.patient_count}
                  </strong>

                  <small>
                    Dice {formatNumber(
                      group.mean_twin_dice,
                      3,
                    )}
                    {" · "}
                    Δ persistence {formatSigned(
                      group.mean_delta_vs_persistence,
                    )}
                  </small>
                </div>
              ),
            )}
          </div>
        </article>
      </section>

      <section
        className="twin-analysis-panel"
      >
        <header
          className="twin-analysis-panel-header twin-analysis-table-header"
        >
          <div>
            <strong>
              Пациенты для error analysis
            </strong>

            <span>
              Сортировка: худший Twin Dice сверху.
            </span>
          </div>

          <div
            className="twin-chip-row"
          >
            <FilterButton
              active={filter === "all"}
              label="Все"
              onClick={() => setFilter("all")}
            />

            <FilterButton
              active={filter === "worse_than_persistence"}
              label="Хуже persistence"
              onClick={() =>
                setFilter("worse_than_persistence")
              }
            />

            <FilterButton
              active={filter === "qc"}
              label="QC"
              onClick={() => setFilter("qc")}
            />

            <FilterButton
              active={filter === "non_identifiable"}
              label="Неидентифицируемые"
              onClick={() =>
                setFilter("non_identifiable")
              }
            />

            <FilterButton
              active={filter === "boundary"}
              label="Граница grid"
              onClick={() => setFilter("boundary")}
            />
          </div>
        </header>

        <div
          className="twin-analysis-table-wrap"
        >
          <table
            className="twin-analysis-table"
          >
            <thead>
              <tr>
                <th>Пациент</th>
                <th>Twin Dice</th>
                <th>Δ persistence</th>
                <th>Горизонт</th>
                <th>Δ объёма t1→t2</th>
                <th>D</th>
                <th>ρ</th>
                <th>Calibration Dice</th>
                <th>QC</th>
              </tr>
            </thead>

            <tbody>
              {filteredPatients.map(
                (patient) => (
                  <AnalysisPatientRow
                    key={patient.patient_id}
                    patient={patient}
                    selected={
                      patient.patient_id
                      === selectedPatientId
                    }
                  />
                ),
              )}
            </tbody>
          </table>
        </div>
      </section>

      <div
        className="twin-analysis-provenance"
      >
        <span>
          Analysis config SHA: {loadedAnalysis.analysis_config_sha256.slice(0, 12)}
        </span>
        <span>
          Evaluation SHA: {loadedAnalysis.source_evaluation_sha256.slice(0, 12)}
        </span>
        <span>
          Repo: {loadedAnalysis.repository.commit_sha.slice(0, 12)}
          {loadedAnalysis.repository.dirty ? " · dirty" : " · clean"}
        </span>
      </div>
    </div>
  );
}


type SummaryCardProps = {
  label: string;
  value: string;
  hint: string;
};


function SummaryCard({
  label,
  value,
  hint,
}: SummaryCardProps) {
  return (
    <article
      className="twin-analysis-summary-card"
    >
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{hint}</small>
    </article>
  );
}


type ButtonProps = {
  active: boolean;
  label: string;
  onClick: () => void;
};


function ScatterButton(props: ButtonProps) {
  return <SmallButton {...props} />;
}


function FilterButton(props: ButtonProps) {
  return <SmallButton {...props} />;
}


function SmallButton({
  active,
  label,
  onClick,
}: ButtonProps) {
  return (
    <button
      type="button"
      className={
        active
          ? "twin-chip active"
          : "twin-chip"
      }
      onClick={onClick}
    >
      {label}
    </button>
  );
}


type CohortScatterPlotProps = {
  patients: TwinCohortPatientError[];
  mode: ScatterMode;
  selectedPatientId: number;
};


function CohortScatterPlot({
  patients,
  mode,
  selectedPatientId,
}: CohortScatterPlotProps) {
  const width = 900;
  const height = 330;
  const left = 58;
  const right = 24;
  const top = 20;
  const bottom = 48;

  const points = patients
    .map((patient) => ({
      patient,
      x: scatterXValue(
        patient,
        mode,
      ),
    }))
    .filter(
      (
        item,
      ): item is {
        patient: TwinCohortPatientError;
        x: number;
      } => item.x !== null,
    );

  if (points.length === 0) {
    return (
      <div
        className="twin-tab-state"
      >
        Недостаточно данных для графика.
      </div>
    );
  }

  const xValues = points.map(
    (point) => point.x,
  );

  let xMin = Math.min(...xValues);
  let xMax = Math.max(...xValues);

  if (xMin === xMax) {
    xMin -= 0.5;
    xMax += 0.5;
  }

  const plotWidth =
    width - left - right;
  const plotHeight =
    height - top - bottom;

  function xPosition(value: number): number {
    return (
      left
      + (
        (value - xMin)
        / (xMax - xMin)
      ) * plotWidth
    );
  }

  function yPosition(dice: number): number {
    return (
      top
      + (1.0 - dice) * plotHeight
    );
  }

  const yTicks = [
    0,
    0.25,
    0.5,
    0.75,
    1,
  ];

  return (
    <div
      className="twin-analysis-scatter-wrap"
    >
      <svg
        className="twin-analysis-scatter"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="График ошибок цифрового двойника по когорте"
      >
        {yTicks.map((tick) => {
          const y = yPosition(tick);

          return (
            <g key={tick}>
              <line
                className="twin-analysis-grid-line"
                x1={left}
                x2={width - right}
                y1={y}
                y2={y}
              />

              <text
                className="twin-analysis-axis-text"
                x={left - 8}
                y={y + 4}
                textAnchor="end"
              >
                {tick.toFixed(2)}
              </text>
            </g>
          );
        })}

        {points.map(({ patient, x }) => {
          const selected =
            patient.patient_id
            === selectedPatientId;

          const flagged =
            patient.qc_warning_codes.length
            > 0;

          return (
            <circle
              key={patient.patient_id}
              className={
                selected
                  ? "twin-analysis-point selected"
                  : flagged
                    ? "twin-analysis-point flagged"
                    : "twin-analysis-point"
              }
              cx={xPosition(x)}
              cy={yPosition(
                patient.twin_dice,
              )}
              r={selected ? 7 : 5}
            >
              <title>
                {`Пациент ${patient.patient_id}: Dice ${patient.twin_dice.toFixed(3)}, x=${formatScatterX(x, mode)}`}
              </title>
            </circle>
          );
        })}

        <text
          className="twin-analysis-axis-label"
          x={left + plotWidth / 2}
          y={height - 8}
          textAnchor="middle"
        >
          {scatterAxisLabel(mode)}
        </text>

        <text
          className="twin-analysis-axis-label"
          x={16}
          y={top + plotHeight / 2}
          textAnchor="middle"
          transform={`rotate(-90 16 ${top + plotHeight / 2})`}
        >
          Twin Dice
        </text>
      </svg>

      <div
        className="twin-analysis-scatter-legend"
      >
        <span>
          <i className="normal" />
          пациент
        </span>
        <span>
          <i className="flagged" />
          QC warning
        </span>
        <span>
          <i className="selected" />
          выбранный пациент
        </span>
      </div>
    </div>
  );
}


type CorrelationExplanationProps = {
  mode: ScatterMode;
  correlation: TwinCorrelation;
};


function CorrelationExplanation({
  mode,
  correlation,
}: CorrelationExplanationProps) {
  if (
    correlation.pearson === null
    && correlation.spearman === null
  ) {
    return (
      <div
        className="twin-analysis-correlation-note"
      >
        Недостаточно вариативных наблюдений для устойчивой описательной корреляции (n={correlation.count}).
      </div>
    );
  }

  return (
    <div
      className="twin-analysis-correlation-note"
    >
      <strong>
        {correlationLabel(mode)}
      </strong>
      <span>
        Pearson {formatNumber(correlation.pearson, 3)} · Spearman {formatNumber(correlation.spearman, 3)} · n={correlation.count}
      </span>
      <small>
        Знак показывает направление совместного изменения, а не причинный эффект.
      </small>
    </div>
  );
}


type PatientIdListProps = {
  title: string;
  patientIds: number[];
  selectedPatientId: number;
};


function PatientIdList({
  title,
  patientIds,
  selectedPatientId,
}: PatientIdListProps) {
  return (
    <div
      className="twin-analysis-patient-id-list"
    >
      <span>{title}</span>
      <div>
        {patientIds.map((patientId) => (
          <b
            key={patientId}
            className={
              patientId === selectedPatientId
                ? "selected"
                : undefined
            }
          >
            P{patientId}
          </b>
        ))}
      </div>
    </div>
  );
}


type AnalysisPatientRowProps = {
  patient: TwinCohortPatientError;
  selected: boolean;
};


function AnalysisPatientRow({
  patient,
  selected,
}: AnalysisPatientRowProps) {
  const boundary = (
    patient.diffusion_at_boundary
    || patient.proliferation_at_boundary
  );

  return (
    <tr
      className={
        selected
          ? "selected"
          : undefined
      }
    >
      <td>
        <strong>
          P{patient.patient_id}
        </strong>
      </td>
      <td>{patient.twin_dice.toFixed(3)}</td>
      <td>{formatSigned(
        patient.twin_minus_persistence_dice,
      )}</td>
      <td>{
        patient.forecast_horizon_days === null
          ? "—"
          : `${patient.forecast_horizon_days.toFixed(0)} д`
      }</td>
      <td>{formatPercent(
        patient.volume_change_t1_t2,
      )}</td>
      <td>{patient.diffusion.toFixed(4)}</td>
      <td>{patient.proliferation.toFixed(4)}</td>
      <td>{patient.calibration_dice.toFixed(3)}</td>
      <td>
        <div
          className="twin-analysis-row-flags"
        >
          {patient.qc_warning_codes.length > 0 && (
            <span>QC {patient.qc_warning_codes.length}</span>
          )}
          {!patient.calibration_identifiable && (
            <span>ID?</span>
          )}
          {boundary && (
            <span>GRID</span>
          )}
          {patient.qc_warning_codes.length === 0
          && patient.calibration_identifiable
          && !boundary && (
            <span className="clear">OK</span>
          )}
        </div>
      </td>
    </tr>
  );
}


function scatterXValue(
  patient: TwinCohortPatientError,
  mode: ScatterMode,
): number | null {
  if (mode === "horizon") {
    return patient.forecast_horizon_days;
  }

  if (mode === "growth") {
    return patient.volume_change_t1_t2;
  }

  return patient.calibration_dice;
}


function scatterAxisLabel(
  mode: ScatterMode,
): string {
  if (mode === "horizon") {
    return "Горизонт прогноза, дни";
  }

  if (mode === "growth") {
    return "Относительное изменение объёма t1→t2";
  }

  return "Dice калибровки t0→t1";
}


function formatScatterX(
  value: number,
  mode: ScatterMode,
): string {
  if (mode === "horizon") {
    return `${value.toFixed(0)} д`;
  }

  if (mode === "growth") {
    return `${(value * 100).toFixed(1)}%`;
  }

  return value.toFixed(3);
}


function correlationForMode(
  analysis: TwinCohortAnalysis,
  mode: ScatterMode,
): TwinCorrelation {
  if (mode === "horizon") {
    return analysis.summary.forecast_horizon_vs_twin_dice;
  }

  if (mode === "growth") {
    return analysis.summary.volume_change_t1_t2_vs_twin_dice;
  }

  return analysis.summary.calibration_dice_vs_twin_dice;
}


function correlationLabel(
  mode: ScatterMode,
): string {
  if (mode === "horizon") {
    return "Горизонт прогноза ↔ Twin Dice";
  }

  if (mode === "growth") {
    return "Изменение объёма ↔ Twin Dice";
  }

  return "Качество калибровки ↔ Twin Dice";
}


function trajectoryLabel(
  trajectory: string,
): string {
  if (trajectory === "growth") {
    return "Рост";
  }

  if (trajectory === "regression") {
    return "Регрессия";
  }

  if (trajectory === "stable") {
    return "Стабильно";
  }

  return "Не определено";
}


function formatNumber(
  value: number | null,
  digits: number,
): string {
  return value === null
    ? "—"
    : value.toFixed(digits);
}


function formatSigned(
  value: number | null,
): string {
  if (value === null) {
    return "—";
  }

  return (
    value >= 0
      ? `+${value.toFixed(3)}`
      : value.toFixed(3)
  );
}


function formatPercent(
  value: number | null,
): string {
  if (value === null) {
    return "—";
  }

  return `${(value * 100).toFixed(1)}%`;
}


export default TwinCohortAnalysisTab;
