from app.rules.report.c08_non_empty import (
    CHECK_ID,
    CHECK_NAME,
    REQUIRED_FIELDS,
    check_c08_non_empty_fields,
    is_empty_required_field,
)


is_effectively_empty = is_empty_required_field


__all__ = [
    "CHECK_ID",
    "CHECK_NAME",
    "REQUIRED_FIELDS",
    "check_c08_non_empty_fields",
    "is_empty_required_field",
    "is_effectively_empty",
]
