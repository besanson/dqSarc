"""Verdict code evaluates PREREG thresholds mechanically (W4)."""

from __future__ import annotations

from benchmarks.verdicts import h2_verdict, pooled_detection


def _summary(detections: dict[str, dict[str, float]]) -> dict:
    # One rate cell per class with n_corrupted=100 so pooled == the given rate.
    matrix = {
        cls: {"0.20": {arm: {"detection_rate": d, "n_corrupted": 100} for arm, d in arms.items()}}
        for cls, arms in detections.items()
    }
    return {"matrix": matrix}


def test_pooled_detection_weights_by_n() -> None:
    s = {
        "matrix": {
            "stale_master_data": {
                "0.02": {"D": {"detection_rate": 0.0, "n_corrupted": 2}},
                "0.20": {"D": {"detection_rate": 1.0, "n_corrupted": 8}},
            }
        }
    }
    # pooled D = (0*2 + 1*8) / 10 = 0.8
    assert pooled_detection(s)["stale_master_data"]["D"] == 0.8


def test_h2_verdict_supported_when_predictions_hold() -> None:
    # Payload-visible C≈D; metadata-borne C low, D high -> H2 supported.
    s = _summary(
        {
            "cross_source_contradiction": {"C": 1.0, "D": 1.0},
            "duplicate_vendor_conflicting_terms": {"C": 0.9, "D": 0.95},
            "missing_mandatory_field": {"C": 0.9, "D": 1.0},
            "schema_drift": {"C": 0.9, "D": 1.0},
            "plausible_outlier": {"C": 0.0, "D": 0.9},
            "silent_unit_change": {"C": 0.05, "D": 0.85},
            "stale_master_data": {"C": 0.0, "D": 1.0},
            "superseded_golden_record": {"C": 0.1, "D": 0.9},
        }
    )
    v = h2_verdict(s)
    assert v["supported"] and v["P1_payload_visible"] and v["P2_metadata_borne"]


def test_h2_verdict_fails_on_schema_drift_and_coverage_gaps() -> None:
    # The committed-data shape: schema_drift breaks P1; unit-change/outlier break P2.
    s = _summary(
        {
            "cross_source_contradiction": {"C": 1.0, "D": 1.0},
            "duplicate_vendor_conflicting_terms": {"C": 0.02, "D": 0.0},
            "missing_mandatory_field": {"C": 0.77, "D": 1.0},
            "schema_drift": {"C": 0.0, "D": 1.0},  # P1 fail
            "plausible_outlier": {"C": 0.0, "D": 0.0},  # P2 fail
            "silent_unit_change": {"C": 0.0, "D": 0.0},  # P2 fail
            "stale_master_data": {"C": 0.0, "D": 1.0},
            "superseded_golden_record": {"C": 1.0, "D": 1.0},  # P2 fail
        }
    )
    v = h2_verdict(s)
    assert not v["supported"]
    fails = {r["class"] for r in v["rows"] if not r["pass"]}
    assert {"schema_drift", "plausible_outlier", "silent_unit_change"} <= fails
