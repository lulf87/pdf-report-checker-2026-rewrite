from pathlib import Path

from app.domain.common import Confidence
from app.domain.report import LabelOCRResult
from app.infrastructure.ocr.ocr_service import OCRService


class FakeEngine:
    def ocr(self, image_path: str, cls: bool = True):
        return [
            [
                ([[0, 0], [100, 0], [100, 20], [0, 20]], ("规格型号：RMD01", 0.94)),
                ([[0, 24], [160, 24], [160, 44], [0, 44]], ("生产日期：20251230", 0.88)),
            ]
        ]


class EmptyEngine:
    def ocr(self, image_path: str, cls: bool = True):
        return [[]]


def test_ocr_service_uses_injected_engine_and_returns_domain_label_result(tmp_path: Path) -> None:
    image_path = tmp_path / "label.png"
    image_path.write_bytes(b"fake")
    service = OCRService(engine=FakeEngine(), language="ch")

    result = service.process_image(image_path, page_number=7, caption_text="图1 中文标签", label_id="label-7")

    assert isinstance(result, LabelOCRResult)
    assert result.label_id == "label-7"
    assert result.page_number == 7
    assert result.caption_text == "图1 中文标签"
    assert result.confidence == Confidence.HIGH
    assert {field.name: field.value for field in result.fields}["model_spec"] == "RMD01"
    assert result.metadata["ocr_engine"] == "FakeEngine"


def test_ocr_service_falls_back_to_text_without_treating_empty_ocr_as_label_absent(tmp_path: Path) -> None:
    image_path = tmp_path / "label.png"
    image_path.write_bytes(b"fake")
    service = OCRService(engine=EmptyEngine())

    result = service.process_image(
        image_path,
        fallback_text="型号规格：RMD01\n生产日期：20251230",
        page_number=2,
    )

    assert result.raw_blocks == ["型号规格：RMD01", "生产日期：20251230"]
    assert {field.name: field.value for field in result.fields}["production_date"] == "20251230"
    assert any("fallback text" in diagnostic for diagnostic in result.metadata["diagnostics"])


def test_low_confidence_ocr_is_marked_as_low_confidence_not_failure(tmp_path: Path) -> None:
    class LowConfidenceEngine:
        def ocr(self, image_path: str, cls: bool = True):
            return [[([[0, 0], [100, 0], [100, 20], [0, 20]], ("批号：LOT001", 0.41))]]

    image_path = tmp_path / "label.png"
    image_path.write_bytes(b"fake")
    result = OCRService(engine=LowConfidenceEngine(), low_confidence_threshold=0.6).process_image(image_path)

    assert result.confidence == Confidence.LOW
    assert result.fields[0].name == "batch_number"
    assert any("low confidence" in diagnostic for diagnostic in result.metadata["diagnostics"])
