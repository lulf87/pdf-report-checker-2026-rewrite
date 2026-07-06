from app.domain.pdf import ParsedPdf, PdfPage
from app.domain.ptr import PTRScopeType
from app.infrastructure.ptr.ptr_extractor import PTRExtractor
from tests.fixtures.table_fixture_builder import build_pdf_table


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


def test_referenced_cross_page_table_text_is_attached_to_clause_body() -> None:
    parsed_pdf = ParsedPdf(
        file_id="ptr-pm3562-table-continuation",
        file_name="ptr.pdf",
        page_count=3,
        pages=[
            PdfPage(
                page_number=1,
                text="\n".join(
                    [
                        "2 性能指标",
                        "2.3 特殊功能",
                        "特殊功能应符合表 2-2 的要求。",
                    ]
                ),
                tables=[
                    build_pdf_table(
                        [
                            ["功能", "要求"],
                            ["VIP", "应支持"],
                            ["SyncAV", "应支持"],
                            ["QuickOpt", "应支持"],
                            ["Measure RV-LV conduction time", "应支持"],
                            ["VectSelect Quartet", "应支持"],
                            ["Lead Impedance Monitoring", "应支持"],
                            ["AutoVect Select", "应支持"],
                            ["Diagnostic Histograms", "应支持"],
                        ],
                        page=1,
                        table_id="ptr-table-2-2-a",
                        table_number="2-2",
                        caption="表2-2 特殊功能",
                    )
                ],
            ),
            PdfPage(
                page_number=2,
                text="2.3 特殊功能（续）",
                tables=[
                    build_pdf_table(
                        [
                            ["功能", "要求"],
                            ["PVC 反应 / PVC Response", "应支持"],
                            ["MR Conditional", "应支持"],
                        ],
                        page=2,
                        table_id="ptr-table-2-2-b",
                        table_number="2-2",
                        caption="表2-2 特殊功能（续）",
                    )
                ],
            ),
            PdfPage(page_number=3, text="3 检验方法\n按产品技术要求检验。"),
        ],
    )

    document = PTRExtractor().extract(parsed_pdf)

    clause = document.get_clause_by_string("2.3")
    assert clause is not None
    assert "VIP" in clause.body_text
    assert "SyncAV" in clause.body_text
    assert "QuickOpt" in clause.body_text
    assert "Measure RV-LV conduction time" in clause.body_text
    assert "VectSelect Quartet" in clause.body_text
    assert "Lead Impedance Monitoring" in clause.body_text
    assert "AutoVect Select" in clause.body_text
    assert "Diagnostic Histograms" in clause.body_text
    assert "PVC Response" in clause.body_text
    assert "MR Conditional" in clause.body_text


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


def test_extracts_split_number_title_clauses_and_cross_page_leading_continuation() -> None:
    parsed_pdf = ParsedPdf(
        file_id="ptr-pm3562-split-headings",
        file_name="ptr.pdf",
        page_count=4,
        pages=[
            PdfPage(page_number=1, text="1.3.2\n电池信息\n选择性更换电压（空载）\n2.62 V"),
            PdfPage(
                page_number=2,
                text="\n".join(
                    [
                        "2",
                        "性能指标",
                        "2.2",
                        "基本功能",
                        "2.2.2",
                        "紧急起搏模式",
                        "起搏器应有在紧急情况下的安全起搏模式。",
                        "参数",
                        "应急 VVI 设置",
                        "模式",
                        "VVI",
                        "基本频率",
                        "70min-1",
                        "右室/左室脉冲振幅",
                        "7.5 V/7.5V",
                        "右室/左室脉宽",
                        "0.6ms/0.6ms",
                        "心室不应期",
                        "325ms*",
                        "2.3 特殊功能",
                        "起搏器应具备表 2-2 所列的特殊功能。",
                        "表 2-2 特殊功能",
                        "休息频率",
                        "Rest Rate",
                    ]
                ),
            ),
            PdfPage(
                page_number=3,
                text="\n".join(
                    [
                        "3/14",
                        "心室自身优先功能",
                        "VIP",
                        "PVC 反应",
                        "PVC Response",
                        "MR 特定条件安全",
                        "MR Conditional",
                        "2.6",
                        "通用要求",
                        "应符合 GB 16174.1-2024 的要求。",
                        "2.7",
                        "专用要求",
                        "应符合 GB 16174.2-2024 的要求。",
                        "2.8",
                        "附件要求",
                        "2.8.2",
                        "扭矩扳手尺寸",
                        "0.88 毫米≤ A ≤ 0.89 毫米",
                        "0.96 毫米≤ B ≤ 1 毫米",
                    ]
                ),
            ),
            PdfPage(page_number=4, text="3\n检验方法\n3.1 试验的基本要求"),
        ],
    )

    document = PTRExtractor().extract(parsed_pdf)

    numbers = [str(clause.number) for clause in document.clauses]
    assert "2.62" not in numbers
    assert "2.2.2" in numbers
    assert "2.6" in numbers
    assert "2.7" in numbers
    assert "2.8.2" in numbers
    clause_222 = document.get_clause_by_string("2.2.2")
    assert clause_222 is not None
    assert "紧急起搏模式" in clause_222.body_text
    assert "VVI" in clause_222.body_text
    clause_23 = document.get_clause_by_string("2.3")
    assert clause_23 is not None
    assert "Rest Rate" in clause_23.body_text
    assert "PVC Response" in clause_23.body_text
    assert "MR Conditional" in clause_23.body_text
    clause_282 = document.get_clause_by_string("2.8.2")
    assert clause_282 is not None
    assert "扭矩扳手尺寸" in clause_282.body_text
    assert "0.884" not in clause_282.body_text


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
