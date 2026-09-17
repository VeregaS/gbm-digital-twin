import {
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";

import type {
  TwinMaskQC,
  TwinPatientQC,
} from "../../api/twin";


type TwinQCTabProps = {
  qc:
    TwinPatientQC | null;

  error:
    string | null;
};


function TwinQCTab({
  qc,
  error,
}: TwinQCTabProps) {
  if (
    error !== null
  ) {
    return (
      <div
        className="twin-tab-state error"
      >
        Контроль качества недоступен: {error}
      </div>
    );
  }

  if (qc === null) {
    return (
      <div
        className="twin-tab-state"
      >
        Загружаем технический контроль качества…
      </div>
    );
  }

  return (
    <div
      className="twin-tab-stack"
    >
      <section
        className={
          qc.warnings.length === 0
            ? "twin-qc-status clear"
            : "twin-qc-status warning"
        }
      >
        {qc.warnings.length === 0 ? (
          <CheckCircle2
            size={20}
          />
        ) : (
          <AlertTriangle
            size={20}
          />
        )}

        <div>
          <strong>
            {qc.warnings.length === 0
              ? "Автоматические геометрические проверки не нашли предупреждений"
              : `${qc.warnings.length} предупреждений технического контроля качества`}
          </strong>

          <span>
            Эти проверки описывают геометрию масок и их положение относительно маски мозга. Они не являются клинической оценкой качества данных.
          </span>
        </div>
      </section>

      {qc.warnings.length > 0 && (
        <section
          className="twin-qc-warning-list"
        >
          {qc.warnings.map(
            (warning) => (
              <article
                key={warning.code}
              >
                <AlertTriangle
                  size={16}
                />

                <div>
                  <strong>
                    {
                      warningTitle(
                        warning.code,
                      )
                    }
                  </strong>

                  <span>
                    {
                      warningMessage(
                        warning.code,
                        warning.message,
                      )
                    }
                  </span>
                </div>
              </article>
            ),
          )}
        </section>
      )}

      <section
        className="twin-qc-grid"
      >
        <MaskCard
          title="Реальная t2"
          qc={qc.observed}
        />

        <MaskCard
          title="Цифровой двойник"
          qc={qc.twin}
        />

        <MaskCard
          title="Без изменений"
          qc={qc.persistence}
        />

        <MaskCard
          title="Прогноз по объёму"
          qc={
            qc.volume_baseline
          }
        />
      </section>
    </div>
  );
}


type MaskCardProps = {
  title: string;
  qc: TwinMaskQC;
};


function MaskCard({
  title,
  qc,
}: MaskCardProps) {
  return (
    <article
      className="twin-qc-card"
    >
      <header>
        <strong>
          {title}
        </strong>

        <span>
          {qc.volume_cm3
          .toFixed(2)}
          {" см³"}
        </span>
      </header>

      <dl>
        <div>
          <dt>
            Связные компоненты
          </dt>

          <dd>
            {qc.component_count}
          </dd>
        </div>

        <div>
          <dt>
            Доля крупнейшей компоненты
          </dt>

          <dd>
            {
              qc
              .largest_component_fraction
              === null
                ? "—"
                : (
                  (
                    qc
                    .largest_component_fraction
                    * 100
                  ).toFixed(1)
                  + "%"
                )
            }
          </dd>
        </div>

        <div>
          <dt>
            За пределами мозга
          </dt>

          <dd>
            {
              qc
              .outside_brain_fraction
              === null
                ? "—"
                : (
                  (
                    qc
                    .outside_brain_fraction
                    * 100
                  ).toFixed(2)
                  + "%"
                )
            }
          </dd>
        </div>

        <div>
          <dt>
            Центр внутри мозга
          </dt>

          <dd>
            {
              qc
              .centroid_inside_brain
              === null
                ? "—"
                : qc
                  .centroid_inside_brain
                    ? "Да"
                    : "Нет"
            }
          </dd>
        </div>
      </dl>
    </article>
  );
}


function warningTitle(
  code: string,
): string {
  switch (code) {
    case "observed_empty":
      return "Реальная сегментация t2 пуста";
    case "observed_outside_brain":
      return "Реальная t2 выходит за маску мозга";
    case "observed_fragmented":
      return "Реальная t2 фрагментирована";
    case "twin_empty":
      return "Прогноз двойника пуст";
    case "twin_outside_brain":
      return "Прогноз двойника выходит за маску мозга";
    case "twin_fragmented":
      return "Прогноз двойника фрагментирован";
    case "persistence_outside_brain":
      return "Baseline «без изменений» выходит за маску мозга";
    case "volume_baseline_outside_brain":
      return "Прогноз по объёму выходит за маску мозга";
    default:
      return code.replaceAll(
        "_",
        " ",
      );
  }
}


function warningMessage(
  code: string,
  fallback: string,
): string {
  if (
    code.includes(
      "outside_brain"
    )
  ) {
    return (
      "Часть маски лежит вне вычислительной маски мозга. "
      + "Это может быть особенностью исходной сегментации, маски мозга, регистрации или ресемплинга."
    );
  }

  if (
    code.includes(
      "fragmented"
    )
  ) {
    return (
      "Маска состоит из нескольких раздельных областей. "
      + "Проверьте мелкие удалённые компоненты в режимах «Сравнение» и 3D."
    );
  }

  if (
    code.includes(
      "empty"
    )
  ) {
    return "Маска не содержит положительных вокселей.";
  }

  return fallback;
}


export default TwinQCTab;
