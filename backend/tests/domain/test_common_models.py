from pydantic import ValidationError

from app.domain.common import BoundingBox, Confidence, Evidence, EvidenceMethod, Location, SourceType


def test_location_and_evidence_serialize_traceable_json() -> None:
    location = Location(
        source_id="report.pdf",
        source_type=SourceType.REPORT,
        page_number=3,
        bbox=(10, 20, 30, 45),
        section="third_page",
        table_id="sample-description",
        row_index=2,
        column_name="型号规格",
        text_span=(4, 12),
    )
    evidence = Evidence(
        id="ev-model-spec",
        source_type=SourceType.REPORT,
        location=location,
        raw_text="型号规格：ABC-1",
        normalized_text="ABC-1",
        value="ABC-1",
        method=EvidenceMethod.PDF_TEXT,
        confidence="high",
    )

    payload = evidence.model_dump(mode="json")

    assert payload["source_type"] == "report"
    assert payload["method"] == "pdf_text"
    assert payload["metadata"] == {}
    assert payload["location"]["page_number"] == 3
    assert payload["location"]["bbox"] == {"x0": 10.0, "y0": 20.0, "x1": 30.0, "y1": 45.0}
    assert location.bbox is not None
    assert location.bbox.width == 20
    assert location.bbox.height == 25
    assert location.bbox.area == 500


def test_location_adapts_old_bounding_box_shape_without_preserving_old_model() -> None:
    legacy_bbox = {"x0": 1, "y0": 2, "x1": 11, "y1": 22, "page": 5}

    location = Location.from_legacy_bbox(
        legacy_bbox,
        source_id="ptr.pdf",
        source_type=SourceType.PTR,
        section="chapter_2",
    )

    payload = location.model_dump(mode="json")
    assert payload["source_id"] == "ptr.pdf"
    assert payload["source_type"] == "ptr"
    assert payload["page_number"] == 5
    assert payload["section"] == "chapter_2"
    assert payload["bbox"] == {"x0": 1.0, "y0": 2.0, "x1": 11.0, "y1": 22.0}


def test_evidence_confidence_uses_stable_enum_values() -> None:
    evidence = Evidence(
        id="ev-ocr-low",
        source_type=SourceType.REPORT,
        raw_text="型号规格：ABC-1",
        method=EvidenceMethod.OCR,
        confidence="low",
    )

    assert evidence.confidence is Confidence.LOW
    assert evidence.model_dump(mode="json")["confidence"] == "low"


def test_location_rejects_invalid_page_indices_and_text_span() -> None:
    invalid_values = [
        {"page_number": 0},
        {"row_index": -1},
        {"text_span": (12, 4)},
        {"bbox": (30, 10, 20, 20)},
    ]

    for kwargs in invalid_values:
        try:
            Location(**kwargs)
        except ValidationError:
            continue
        raise AssertionError(f"Location accepted invalid value: {kwargs}")
