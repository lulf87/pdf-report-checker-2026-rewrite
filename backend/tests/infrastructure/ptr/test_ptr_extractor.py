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

