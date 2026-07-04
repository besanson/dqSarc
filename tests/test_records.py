"""Evidence records: payload/metadata split and versioned evidence ids."""

from __future__ import annotations

from sarc_dq.records import EvidenceRecord, RecordMetadata


def _rec(
    unit_cost: float = 10.0, as_of: int = 100, now: int = 100, version: int = 1
) -> EvidenceRecord:
    return EvidenceRecord(
        record_id="SKU-1:price",
        payload={"sku": "SKU-1", "unit_cost": unit_cost, "currency": "USD"},
        metadata=RecordMetadata(source="erp", as_of_day=as_of, retrieved_day=now, version=version),
        ground_truth={"secret": True},
    )


def test_payload_view_excludes_metadata() -> None:
    r = _rec()
    view = r.payload_view()
    assert "unit_cost" in view
    assert "as_of_day" not in view and "source" not in view


def test_full_view_includes_metadata_and_age() -> None:
    r = _rec(as_of=10, now=100)
    full = r.full_view()
    assert full["metadata"]["age_days"] == 90
    assert full["payload"]["unit_cost"] == 10.0


def test_evidence_id_is_content_addressed_and_ignores_ground_truth() -> None:
    a = _rec()
    # Same payload+metadata but different (hidden) ground truth -> same evidence id.
    b = EvidenceRecord(
        record_id=a.record_id,
        payload=dict(a.payload),
        metadata=a.metadata,
        ground_truth={"secret": False},
    )
    assert a.evidence_id() == b.evidence_id()
    # A different version changes what was relied on -> different id.
    assert _rec(version=2).evidence_id() != a.evidence_id()
    # A different price changes the id.
    assert _rec(unit_cost=11.0).evidence_id() != a.evidence_id()
