from app.domain.ptr import PTRTable
from app.domain.table import CanonicalTable, ParameterRecord, TableHeader
from app.infrastructure.ptr.ptr_extractor import PTRExtractor


def _ptr_table(
    table_id: str,
    *,
    table_number: str | None,
    page: int,
    y0: float,
    headers: list[str],
    records: list[ParameterRecord],
) -> PTRTable:
    canonical = CanonicalTable(
        table_id=f"canonical:{table_id}",
        caption=f"表 {table_number} 参数" if table_number else "续表 参数",
        headers=[TableHeader(rows=[headers], column_paths=[[header] for header in headers])],
        header_rows=[headers],
        parameter_name_column=headers[0],
        value_columns=[headers[3]] if len(headers) > 3 else [],
        condition_columns=[headers[1]] if len(headers) > 1 else [],
        parameter_records=records,
    )
    return PTRTable(
        table_id=table_id,
        table_number=table_number,
        title=canonical.caption,
        canonical_table=canonical,
        page_span=(page, page),
        metadata={"y0": y0},
    )


def test_merges_cross_page_continuation_with_repeated_header() -> None:
    extractor = PTRExtractor()
    first = _ptr_table(
        "table-1a",
        table_number="1",
        page=3,
        y0=520,
        headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
        records=[
            ParameterRecord(
                parameter_name="脉冲宽度(ms)",
                dimensions={"型号": "全部型号"},
                values={"标准设置": "0.4", "允许误差": "±20μs"},
            )
        ],
    )
    continuation = _ptr_table(
        "table-1b",
        table_number=None,
        page=4,
        y0=40,
        headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
        records=[
            ParameterRecord(
                parameter_name="基础频率(bpm)",
                dimensions={"型号": "全部型号"},
                values={"标准设置": "60", "允许误差": "±20ms"},
            )
        ],
    )

    merged = extractor._merge_continuation_tables([first, continuation])

    assert len(merged) == 1
    assert merged[0].table_number == "1"
    assert merged[0].page_span == (3, 4)
    assert merged[0].metadata["continuation_reason"] in {
        "same_header_continuation",
        "top_bottom_with_header_overlap",
    }
    names = [record.parameter_name for record in merged[0].canonical_table.parameter_records]
    assert names == ["脉冲宽度(ms)", "基础频率(bpm)"]


def test_rejects_no_number_continuation_when_headers_differ() -> None:
    extractor = PTRExtractor()
    first = _ptr_table(
        "table-1a",
        table_number="1",
        page=3,
        y0=520,
        headers=["参数", "型号", "常规数值", "标准设置", "允许误差"],
        records=[
            ParameterRecord(
                parameter_name="脉冲宽度(ms)",
                dimensions={"型号": "全部型号"},
                values={"标准设置": "0.4"},
            )
        ],
    )
    unrelated = _ptr_table(
        "table-2",
        table_number=None,
        page=4,
        y0=40,
        headers=["章节", "说明", "备注"],
        records=[
            ParameterRecord(
                parameter_name="资料性说明",
                values={"备注": "不参与参数比对"},
            )
        ],
    )

    merged = extractor._merge_continuation_tables([first, unrelated])

    assert len(merged) == 2
    assert merged[1].metadata["continuation_reject_reason"] in {
        "header_mismatch",
        "missing_table_number_without_strong_evidence",
    }
