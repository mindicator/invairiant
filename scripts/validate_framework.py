#!/usr/bin/env python3
"""invAIriant framework self-validation.

Dogfoods the protocol's own contracts:

  1. every JSON schema in schemas/ parses and is a valid JSON Schema;
  2. every example invairiant.config.yml validates against the config schema;
  3. the example findings validate against the finding schema;
  4. every canonical lens file carries the required section structure, and
     every cross-listed stub points at an existing canonical file.

Runs in CI (.github/workflows/validate.yml) and locally:

    python3 scripts/validate_framework.py

jsonschema and pyyaml enable the full check. If they are missing, the script
degrades to JSON-parse + lens-structure checks and says so, still failing on
any structural problem.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "schemas"
LENSES = ROOT / "lenses"
EXAMPLES = ROOT / "examples"

errors: list[str] = []
notes: list[str] = []

try:
    import jsonschema  # type: ignore
    from jsonschema import Draft202012Validator
    HAVE_JSONSCHEMA = True
except Exception:  # pragma: no cover - environment dependent
    HAVE_JSONSCHEMA = False
    notes.append("jsonschema not installed -> skipping instance validation")

try:
    import yaml  # type: ignore
    HAVE_YAML = True
except Exception:  # pragma: no cover - environment dependent
    HAVE_YAML = False
    notes.append("pyyaml not installed -> skipping YAML config validation")


REQUIRED_LENS_SECTIONS = [
    "## Purpose",
    "## Scope",
    "## Core Questions",
    "## Good-State Examples",
    "## Red Flags",
    "## Required Evidence",
    "## Scoring Rubric",
    "## Finding Examples",
    "## Prompt Block",
]

RUBRIC_ROW = "| 0–2 | Dangerous / uncontrolled |"


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
        return None


def check_schemas() -> dict[str, dict]:
    loaded: dict[str, dict] = {}
    schema_files = sorted(SCHEMAS.glob("*.json"))
    if not schema_files:
        errors.append("schemas/: no JSON schema files found")
        return loaded
    for path in schema_files:
        schema = load_json(path)
        if schema is None:
            continue
        loaded[path.name] = schema
        if HAVE_JSONSCHEMA:
            try:
                Draft202012Validator.check_schema(schema)
            except jsonschema.exceptions.SchemaError as exc:  # type: ignore
                errors.append(f"{path.relative_to(ROOT)}: not a valid schema: {exc.message}")
    return loaded


def validate_instance(instance, schema, label: str) -> None:
    if not HAVE_JSONSCHEMA:
        return
    validator = Draft202012Validator(schema)
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{label}: {loc}: {err.message}")


def check_configs(schemas: dict[str, dict]) -> None:
    schema = schemas.get("invairiant.config.schema.json")
    if schema is None:
        return
    configs = sorted(EXAMPLES.glob("*/invairiant.config.yml"))
    if not configs:
        errors.append("examples/: no invairiant.config.yml found")
        return
    for path in configs:
        if not HAVE_YAML:
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path.relative_to(ROOT)}: invalid YAML: {exc}")
            continue
        validate_instance(data, schema, str(path.relative_to(ROOT)))


def check_findings(schemas: dict[str, dict]) -> None:
    schema = schemas.get("finding.schema.json")
    if schema is None:
        return
    finding_files = sorted(EXAMPLES.glob("*/example-findings.json"))
    if not finding_files:
        notes.append("examples/: no example-findings.json (optional)")
        return
    for path in finding_files:
        data = load_json(path)
        if data is None:
            continue
        items = data if isinstance(data, list) else [data]
        for i, item in enumerate(items):
            validate_instance(item, schema, f"{path.relative_to(ROOT)}[{i}]")


def check_lenses() -> None:
    lens_files = [p for p in LENSES.glob("*/*.md") if p.name != "README.md"]
    if not lens_files:
        errors.append("lenses/: no lens files found")
        return
    canonical = 0
    stubs = 0
    for path in sorted(lens_files):
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)
        if "Canonical file:" in text or "(cross-listed)" in text:
            stubs += 1
            m = re.search(r"\*\*Canonical file:\*\*\s*\[[^\]]+\]\(([^)]+)\)", text)
            if not m:
                errors.append(f"{rel}: cross-listed stub without a canonical-file link")
                continue
            target = (path.parent / m.group(1)).resolve()
            if not target.exists():
                errors.append(f"{rel}: canonical file not found: {m.group(1)}")
            continue
        canonical += 1
        if not re.match(r"^#\s+.+Lens\s+—\s+.+", text.splitlines()[0] if text.splitlines() else ""):
            errors.append(f"{rel}: title must be '# <Name> Lens — <Short Description>'")
        for section in REQUIRED_LENS_SECTIONS:
            if section not in text:
                errors.append(f"{rel}: missing required section '{section}'")
        if RUBRIC_ROW not in text:
            errors.append(f"{rel}: scoring rubric must include the verbatim row '{RUBRIC_ROW}'")
    notes.append(f"lenses: {canonical} canonical + {stubs} cross-listed stub(s) checked")


def main() -> int:
    schemas = check_schemas()
    check_configs(schemas)
    check_findings(schemas)
    check_lenses()

    print("invAIriant self-validation")
    print("=" * 30)
    for note in notes:
        print(f"  note: {note}")
    print()
    if errors:
        print(f"FAILED with {len(errors)} problem(s):")
        for e in errors:
            print(f"  ✗ {e}")
        return 1
    print("OK: schemas parse, examples validate, lens structure intact.")
    if not (HAVE_JSONSCHEMA and HAVE_YAML):
        print("(ran in degraded mode; install jsonschema + pyyaml for full checks)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
