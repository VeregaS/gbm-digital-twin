from gbm_twin.anatomy.bootstrap import (
    classify_functional_region,
)


def test_classifies_language_region() -> None:
    result = (
        classify_functional_region(
            
                "Left Inferior Frontal "
                "Gyrus, pars opercularis"
            
        )
    )

    assert result is not None

    category, note = (
        result
    )

    assert category == (
        "language-associated"
    )

    assert (
        "patient-specific"
        in note
    )


def test_classifies_motor_region() -> None:
    result = (
        classify_functional_region(
            "Right Precentral Gyrus"
        )
    )

    assert result is not None

    assert result[0] == (
        "motor-associated"
    )


def test_classifies_visual_region() -> None:
    result = (
        classify_functional_region(
            
                "Left Intracalcarine "
                "Cortex"
            
        )
    )

    assert result is not None

    assert result[0] == (
        "visual-associated"
    )


def test_classifies_memory_region() -> None:
    result = (
        classify_functional_region(
            "Left Hippocampus"
        )
    )

    assert result is not None

    assert result[0] == (
        "memory-associated"
    )


def test_ignores_nonrisk_region() -> None:
    result = (
        classify_functional_region(
            "Frontal Pole"
        )
    )

    assert result is None