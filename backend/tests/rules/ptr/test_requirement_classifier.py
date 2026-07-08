from __future__ import annotations

from app.domain.ptr import PTRClause, PTRClauseNumber, PTRDocument, TableReference
from app.rules.ptr.atomic_compare import build_atomic_requirements
from app.rules.ptr.requirement_classifier import RequirementType, classify_requirement


def _clause(number: str, title: str, body: str, *, table_refs: list[str] | None = None) -> PTRClause:
    references = [
        TableReference(table_number=table_number, context=body, clause_id=f"ptr-{number}")
        for table_number in (table_refs or [])
    ]
    return PTRClause(
        clause_id=f"ptr-{number}",
        number=PTRClauseNumber.from_string(number),
        title=title,
        body_text=body,
        full_text=f"{number} {title}\n{body}",
        table_refs=table_refs or [],
        table_references=references,
    )


def test_classifier_uses_clause_content_for_same_clause_number() -> None:
    voltage_current = _clause(
        "2.2.1",
        "心脏脉冲电场消融仪输出",
        "输出电压应不小于3333V（峰值），输出电流应不小于57A（峰值）。",
    )
    r_wave_sync = _clause(
        "2.2.1",
        "R 波同步",
        "设备应具有 R 波同步触发功能，检验结果应符合要求。",
    )

    numeric = classify_requirement(voltage_current, PTRDocument(clauses=[voltage_current]))
    functional = classify_requirement(r_wave_sync, PTRDocument(clauses=[r_wave_sync]))

    assert numeric.requirement_type == RequirementType.NUMERIC_LIMIT
    assert {requirement.atomic_id for requirement in numeric.atomic_requirements} == {
        "2.2.1:voltage",
        "2.2.1:current",
    }
    assert functional.requirement_type == RequirementType.FUNCTIONAL
    assert {requirement.atomic_id for requirement in functional.atomic_requirements} == {"2.2.1:r_wave_sync"}


def test_classifier_identifies_table_and_external_standard_requirements() -> None:
    table_clause = _clause("2.1.1", "基本频率", "应符合表2-1规定的要求。", table_refs=["2-1"])
    software_table = _clause("2.6", "软件功能", "软件功能应符合表6的要求。", table_refs=["6"])
    external = _clause("2.5", "电气安全", "应符合 GB 9706.1-2020 的要求。")
    unknown = _clause("2.9", "其他", "应满足产品技术要求。")

    assert classify_requirement(table_clause, PTRDocument(clauses=[table_clause])).requirement_type == RequirementType.TABLE_DRIVEN
    assert (
        classify_requirement(software_table, PTRDocument(clauses=[software_table])).requirement_type
        == RequirementType.SOFTWARE_FUNCTION_TABLE
    )
    assert (
        classify_requirement(external, PTRDocument(clauses=[external])).requirement_type
        == RequirementType.EXTERNAL_STANDARD_COVERAGE
    )
    assert classify_requirement(unknown, PTRDocument(clauses=[unknown])).requirement_type == RequirementType.UNKNOWN_NEEDS_REVIEW


def test_atomic_requirements_do_not_treat_all_2_2_1_clauses_as_voltage_current() -> None:
    r_wave_sync = _clause(
        "2.2.1",
        "R 波同步",
        "设备应具有 R 波同步触发功能，检验结果应符合要求。",
    )

    requirements = build_atomic_requirements(r_wave_sync, PTRDocument(clauses=[r_wave_sync]))

    assert {requirement.atomic_id for requirement in requirements} == {"2.2.1:r_wave_sync"}
    assert all(requirement.label != "电压" for requirement in requirements)
    assert all(requirement.label != "电流" for requirement in requirements)
