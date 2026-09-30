import json
from pathlib import Path

from gbm_twin.anatomy.atlas import (
    _load_region_definitions,
)


def test_manifest_accepts_legacy_label_value(
    tmp_path: Path,
) -> None:
    manifest = (
        tmp_path
        / "manifest.json"
    )

    manifest.write_text(
        json.dumps(
            {
                "atlas_name": "Legacy atlas",
                "regions": [
                    {
                        "label_value": 7,
                        "name": "Left Precentral Gyrus",
                        "category": "motor-associated",
                        "laterality": "left",
                        "functional_note": "Motor-associated cortex",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    name, regions = (
        _load_region_definitions(
            manifest
        )
    )

    assert name == "Legacy atlas"
    assert len(regions) == 1
    assert regions[0].label == 7
