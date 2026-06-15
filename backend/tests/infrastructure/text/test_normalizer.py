from app.infrastructure.text.normalizer import (
    TextNormalizer,
    are_text_equal_normalized,
    compare_text,
    normalize_for_display,
    normalize_text,
)


def test_strict_normalize_keeps_old_fullwidth_whitespace_and_ocr_symbol_behavior() -> None:
    normalizer = TextNormalizer()

    assert normalizer.normalize("Ｈｅｌｌｏ　　Ｗｏｒｌｄ") == "Hello World"
    assert normalizer.normalize("导 管 外 观") == "导管外观"
    assert normalizer.normalize("直流电阻值≤20Ω。 单位：Ω") == "直流电阻值<=20Ω。"
    assert normalizer.normalize("绝缘电阻>5MQ") == "绝缘电阻>5MΩ"
    assert normalizer.normalize("导丝兼容性可兼容0.038″导丝。") == '导丝兼容性可兼容0.038"导丝。'
    assert normalizer.normalize("Pb²⁺ 和 KMnO₄") == "Pb2+和KMnO4"
    assert ">=1μs" in normalizer.normalize("相间间隔>=lμus")


def test_strict_normalize_merges_natural_breaks_and_repeated_heading_prefix() -> None:
    normalizer = TextNormalizer()

    assert normalizer.normalize("脚踏开关\n脚踏开关应符合YY/T1057-2016标准的要求。") == (
        "脚踏开关应符合YY/T1057-2016标准的要求。"
    )
    assert normalizer.normalize("通用要求:应符合GB16174.1-2024的要求。") == (
        "通用要求应符合GB16174.1-2024的要求。"
    )


def test_display_normalize_preserves_raw_readability_without_strict_symbol_rewrites() -> None:
    raw = "  型号规格：ＲＭＤ０１\n\n生产日期：2025?230  "

    assert normalize_for_display(raw) == "型号规格：ＲＭＤ０１\n生产日期：2025?230"
    assert normalize_text(raw) != normalize_for_display(raw)


def test_compare_helpers_use_strict_normalization_only() -> None:
    assert compare_text("ABC", "ＡＢＣ")
    assert are_text_equal_normalized("电阻值≦10Ω", "电阻值<=10Ω")
    assert not compare_text("符合", "不符合")
