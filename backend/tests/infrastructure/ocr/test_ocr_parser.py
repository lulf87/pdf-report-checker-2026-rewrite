from app.infrastructure.ocr.ocr_parser import (
    OCRParser,
    OCRWarning,
    correct_text_symbols,
)


def test_parse_paddleocr_output_builds_blocks_text_confidence_and_fields() -> None:
    raw = [
        [
            ([[10, 20], [120, 20], [120, 40], [10, 40]], ("型号规格：RMD01", 0.93)),
            ([[10, 48], [160, 48], [160, 68], [10, 68]], ("生产日期：2025-12-30", 0.87)),
        ]
    ]

    result = OCRParser().parse_raw_result(raw, page_number=3)

    assert result.text == "型号规格：RMD01\n生产日期：2025-12-30"
    assert len(result.blocks) == 2
    assert result.blocks[0].bbox is not None
    assert result.blocks[0].bbox.x0 == 10
    assert result.confidence == 0.9
    assert result.field_candidates["model_spec"] == "RMD01"
    assert result.field_candidates["production_date"] == "2025-12-30"


def test_symbol_corrections_return_warnings_without_business_judgement() -> None:
    corrected, warnings = correct_text_symbols("电压 +/- 5V，电阻 <= 10 Q")

    assert "±" in corrected
    assert "≤" in corrected
    assert "Ω" in corrected
    assert warnings
    assert all(isinstance(warning, OCRWarning) for warning in warnings)
    assert all("pass" not in warning.symbol.lower() for warning in warnings)


def test_low_confidence_blocks_are_marked_as_diagnostics_only() -> None:
    raw = [[([[0, 0], [20, 0], [20, 10], [0, 10]], ("批号：LOT001", 0.42))]]

    result = OCRParser(low_confidence_threshold=0.6).parse_raw_result(raw, page_number=1)

    assert result.field_candidates["batch_number"] == "LOT001"
    assert result.confidence == 0.42
    assert any("low confidence" in diagnostic for diagnostic in result.diagnostics)
