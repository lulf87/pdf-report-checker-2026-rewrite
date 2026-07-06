from app.domain.pdf import ParsedPdf, PdfPage
from app.domain.ptr import PTRScopeType
from app.infrastructure.ptr.ptr_extractor import PTRExtractor


def test_extracts_chapter2_by_number_not_fixed_title_and_table_refs() -> None:
    parsed_pdf = ParsedPdf(
        file_id="ptr-fixture",
        file_name="ptr.pdf",
        page_count=2,
        pages=[
            PdfPage(page_number=1, text="1 范围\n本文件规定了产品要求。"),
            PdfPage(
                page_number=2,
                text="\n".join(
                    [
                        "2 通用要求",
                        "2.1 物理性能",
                        "2.1.1 参数要求",
                        "2.1.1.1 脉冲宽度",
                        "脉冲宽度应符合表 1 中的数值。",
                        "2.2 电磁兼容",
                        "电磁兼容应符合YY 9706.102-2021要求。",
                        "3 检验方法",
                        "3.1 按图1进行测试。",
                    ]
                ),
            ),
        ],
    )

    document = PTRExtractor().extract(parsed_pdf)

    numbers = [str(clause.number) for clause in document.clauses]
    assert numbers == ["2", "2.1", "2.1.1", "2.1.1.1", "2.2"]
    assert document.chapter2_span == (2, 2)

    leaf = document.get_clause_by_string("2.1.1.1")
    assert leaf is not None
    assert leaf.title == "脉冲宽度"
    assert leaf.body_text == "脉冲宽度\n脉冲宽度应符合表 1 中的数值。"
    assert leaf.location is not None
    assert leaf.location.page_number == 2
    assert leaf.table_refs == ["1"]
    assert leaf.table_references[0].reference_text == "表 1"

    parent = document.get_clause_by_string("2.1.1")
    assert parent is not None
    assert parent.children_ids == [leaf.clause_id]
    assert leaf.parent_id == parent.clause_id


def test_extracts_hyphenated_table_reference_numbers_without_truncation() -> None:
    for separator in ("-", "‑", "－", "–"):
        parsed_pdf = ParsedPdf(
            file_id=f"ptr-table-2{separator}1",
            file_name="ptr.pdf",
            page_count=1,
            pages=[
                PdfPage(
                    page_number=1,
                    text="\n".join(
                        [
                            "2 性能指标",
                            "2.1.1 基本频率",
                            f"基本频率应符合表 2{separator}1 规定的要求。",
                            f"表 2{separator}1 起搏参数",
                        ]
                    ),
                )
            ],
        )

        document = PTRExtractor().extract(parsed_pdf)

        clause = document.get_clause_by_string("2.1.1")
        assert clause is not None
        assert clause.table_refs == ["2-1"]
        assert clause.table_references[0].table_number == "2-1"
        assert clause.table_references[0].reference_text == "表 2-1"


def test_classifies_non_requirement_lines_without_comparing() -> None:
    parsed_pdf = ParsedPdf(
        file_id="ptr-fixture",
        file_name="ptr.pdf",
        page_count=1,
        pages=[
            PdfPage(
                page_number=1,
                text="\n".join(
                    [
                        "2 性能指标",
                        "2.1 外观",
                        "外观应平整。",
                        "2.2 说明：本章图示仅作参考。",
                        "2.3 附录A 资料性说明。",
                    ]
                ),
            )
        ],
    )

    document = PTRExtractor().extract(parsed_pdf)
    by_number = {str(clause.number): clause for clause in document.clauses}

    assert by_number["2.1"].scope_type == PTRScopeType.REQUIREMENT
    assert by_number["2.2"].scope_type == PTRScopeType.INFORMATIONAL
    assert by_number["2.3"].scope_type == PTRScopeType.APPENDIX


def test_chapter2_detection_does_not_stop_at_standalone_page_number() -> None:
    parsed_pdf = ParsedPdf(
        file_id="ptr-page-number-fixture",
        file_name="ptr.pdf",
        page_count=4,
        pages=[
            PdfPage(
                page_number=1,
                text="\n".join(
                    [
                        "2 性能指标",
                        "2.2 心脏脉冲电场消融仪",
                        "2.2.1 心脏脉冲电场消融仪输出",
                        "心脏脉冲电场消融仪应至少能够提供电压和电流。",
                    ]
                ),
            ),
            PdfPage(
                page_number=2,
                text="\n".join(
                    [
                        "3",
                        "2.2.2 心脏脉冲电场消融仪输出波形图和波形参数",
                        "输出波形图见图 1，波形参数应满足表 6 的要求。",
                    ]
                ),
            ),
            PdfPage(
                page_number=3,
                text="\n".join(
                    [
                        "4",
                        "2.2.7 保护功能",
                        "心脏脉冲电场消融仪应具有保护功能。",
                    ]
                ),
            ),
            PdfPage(page_number=4, text="3 检验方法\n按规定方法检验。"),
        ],
    )

    document = PTRExtractor().extract(parsed_pdf)

    assert document.chapter2_span == (1, 4)
    assert [str(clause.number) for clause in document.clauses] == ["2", "2.2", "2.2.1", "2.2.2", "2.2.7"]


def test_extracts_1539_like_chapter2_until_method_chapter() -> None:
    parsed_pdf = ParsedPdf(
        file_id="ptr-1539-like",
        file_name="ptr.pdf",
        page_count=6,
        pages=[
            PdfPage(page_number=1, text="1 产品型号/规格及其分类说明"),
            PdfPage(
                page_number=2,
                text="\n".join(
                    [
                        "2 性能指标",
                        "2.2 心脏脉冲电场消融仪",
                        "2.2.1 心脏脉冲电场消融仪输出",
                        "心脏脉冲电场消融仪应至少能够提供电压和电流。",
                    ]
                ),
            ),
            PdfPage(
                page_number=3,
                text="\n".join(
                    [
                        "3",
                        "2.2.2 心脏脉冲电场消融仪输出波形图和波形参数",
                        "波形参数应满足表 6 的要求。",
                        "2.2.3 脉冲上升时间",
                        "脉冲上升时间应不超过 700ns。",
                        "2.2.4 脉冲宽度",
                        "脉冲宽度应符合要求。",
                    ]
                ),
            ),
            PdfPage(
                page_number=4,
                text="\n".join(
                    [
                        "4",
                        "2.2.5 脉冲衰减",
                        "脉冲衰减应在 10%内。",
                        "2.2.6 最大输出能量",
                        "单个脉冲最大输出能量应小于 258mJ。",
                        "2.2.7 保护功能",
                        "2.2.7.1 温度超限保护",
                        "2.2.7.2 过流保护",
                    ]
                ),
            ),
            PdfPage(
                page_number=5,
                text="\n".join(
                    [
                        "5",
                        "2.5.2.1 电气安全",
                        "应符合 GB 9706.1-2020 和 GB9706.202-2021 标准的要求。",
                        "2.5.2.2 电磁兼容性",
                        "电磁兼容性应符合 YY 9706.102-2021 标准的要求。",
                        "2.6 软件功能",
                        "软件功能应符合产品技术要求。",
                    ]
                ),
            ),
            PdfPage(page_number=6, text="3 检验方法\n按产品技术要求检验。"),
        ],
    )

    document = PTRExtractor().extract(parsed_pdf)

    numbers = [str(clause.number) for clause in document.clauses]
    assert "2.2.1" in numbers
    assert "2.2.2" in numbers
    assert "2.2.3" in numbers
    assert "2.2.4" in numbers
    assert "2.2.5" in numbers
    assert "2.2.6" in numbers
    assert "2.2.7" in numbers
    assert "2.5.2.1" in numbers
    assert "2.5.2.2" in numbers
    assert "2.6" in numbers
