"""JSON response validation for API monitors."""

from __future__ import annotations

import json
from typing import Any, Optional

from app.models.api_monitor import ValidationRule


def resolve_path(data: Any, path: str) -> tuple[Any, bool]:
    current = data
    for part in (path or "").split("."):
        if part == "":
            continue
        if isinstance(current, dict):
            if part not in current:
                return None, False
            current = current[part]
            continue
        if isinstance(current, list):
            if not part.isdigit():
                return None, False
            index = int(part)
            if index < 0 or index >= len(current):
                return None, False
            current = current[index]
            continue
        return None, False
    return current, True


def _as_text(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def evaluate_rule(data: Any, rule: ValidationRule) -> tuple[bool, str]:
    value, exists = resolve_path(data, rule.field)
    operator = rule.operator
    expected = rule.value

    if operator == "exists":
        if exists:
            return True, ""
        return False, f"Field '{rule.field}' does not exist"

    if operator == "not_exists":
        if not exists:
            return True, ""
        return False, f"Field '{rule.field}' exists"

    if not exists:
        return False, f"Field '{rule.field}' does not exist"

    actual_text = _as_text(value)
    expected_text = "" if expected is None else str(expected)

    if operator == "equals":
        if actual_text == expected_text:
            return True, ""
        return False, f"Field '{rule.field}' expected '{expected_text}', got '{actual_text}'"

    if operator == "not_equals":
        if actual_text != expected_text:
            return True, ""
        return False, f"Field '{rule.field}' should not equal '{expected_text}'"

    if operator == "contains":
        if expected_text in actual_text:
            return True, ""
        return False, f"Field '{rule.field}' does not contain '{expected_text}'"

    if operator == "not_contains":
        if expected_text not in actual_text:
            return True, ""
        return False, f"Field '{rule.field}' contains '{expected_text}'"

    return False, f"Unknown operator '{operator}'"


def parse_json_body(text: Optional[str]) -> tuple[Any, Optional[str]]:
    if text is None or text.strip() == "":
        return None, "Empty response body"
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        return None, "Response is not valid JSON"


def validate_response(text: Optional[str], rules: list[ValidationRule]) -> tuple[bool, Optional[str]]:
    data, error = parse_json_body(text)
    if error:
        return False, error
    for rule in rules:
        ok, message = evaluate_rule(data, rule)
        if not ok:
            return False, message
    return True, None
