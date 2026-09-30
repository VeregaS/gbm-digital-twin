from __future__ import annotations

import argparse
from pathlib import Path

from gbm_twin.workflows.stage10_report import (
    write_stage10_markdown_report,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Render a human-readable report "
            "from the sealed Stage 10 result."
        )
    )

    parser.add_argument(
        "--result-root",
        type=Path,
        default=Path(
            "results/cohort/"
            "stage10-decoupled-selection-v1"
        ),
    )

    args = parser.parse_args()

    path = (
        write_stage10_markdown_report(
            args.result_root
        )
    )

    print(
        "Stage 10 report:",
        path,
    )


if __name__ == "__main__":
    main()
