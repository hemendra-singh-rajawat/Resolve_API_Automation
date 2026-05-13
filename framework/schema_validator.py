from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import allure
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from framework.logger import get_logger

log = get_logger(__name__)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"


def load_schema(name: str) -> dict[str, Any]:
    """Load a schema by short name, e.g. 'patient' → schemas/patient_schema.json."""
    candidates = [
        SCHEMA_DIR / f"{name}_schema.json",
        SCHEMA_DIR / f"{name}.json",
    ]
    for p in candidates:
        if p.exists():
            with p.open("r", encoding="utf-8") as fh:
                return json.load(fh)
    raise FileNotFoundError(f"No schema found for '{name}' under {SCHEMA_DIR}")


def validate(payload: Any, schema_name: str) -> None:
    schema = load_schema(schema_name)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    if not errors:
        log.debug("schema '{}' OK", schema_name)
        return

    summary = "\n".join(_fmt_error(e) for e in errors[:20])
    allure.attach(
        json.dumps(payload, indent=2, default=str),
        name=f"payload (schema={schema_name})",
        attachment_type=allure.attachment_type.JSON,
    )
    allure.attach(
        summary,
        name=f"schema errors ({len(errors)})",
        attachment_type=allure.attachment_type.TEXT,
    )
    raise AssertionError(f"Schema '{schema_name}' validation failed:\n{summary}")


def _fmt_error(err: ValidationError) -> str:
    loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
    return f"  • {loc}: {err.message}"
