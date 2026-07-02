#!/usr/bin/env python3
"""invAIriant CLI — infrastructure around the agentic audit.

This tool deliberately does NOT audit architecture. It has no lenses, produces
no findings, and assigns no scores. All architectural judgment lives in the
`/invairiant` agent skill and the prompt pack. The CLI is the seatbelt around
that judgment: scaffold config, validate inputs/outputs against the schemas,
collect raw evidence from other tools, render a report, and enforce the gate.

Commands:
  init             scaffold ./invairiant.config.yml for a project type
  validate-config  validate a config against schemas/invairiant.config.schema.json
  validate-report  validate an audit report against schemas/audit-report.schema.json
  collect-evidence run declared evidence adapters, emit candidate evidence (JSON)
  render-report    deterministically render a report JSON to Markdown
  ci-gate          exit non-zero when a report has open S0/S1 findings

Full spec: docs/cli.md. Requires Python 3.9+; validation/collection need
`jsonschema` and `pyyaml` (pip install jsonschema pyyaml).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def framework_root() -> Path:
    env = os.environ.get("INVAIRIANT_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


ROOT = framework_root()
SCHEMAS = ROOT / "schemas"
EXAMPLES = ROOT / "examples"


def _die(msg: str, code: int = 1) -> None:
    print(f"invairiant: {msg}", file=sys.stderr)
    sys.exit(code)


def _need(module: str):
    try:
        return __import__(module)
    except Exception:
        _die(f"'{module}' is required for this command — pip install jsonschema pyyaml", 3)


def _load_schema(name: str) -> dict:
    path = SCHEMAS / f"{name}.schema.json"
    if not path.exists():
        _die(f"schema not found: {path} (set INVAIRIANT_HOME?)", 3)
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(schema_name: str):
    """Draft 2020-12 validator with a registry so local $refs resolve."""
    _need("jsonschema")
    from jsonschema import Draft202012Validator
    try:
        from referencing import Registry, Resource
        resources = []
        for p in SCHEMAS.glob("*.json"):
            data = json.loads(p.read_text(encoding="utf-8"))
            rid = data.get("$id") or p.name
            resources.append((rid, Resource.from_contents(data)))
        registry = Registry().with_resources(resources)
        return Draft202012Validator(_load_schema(schema_name), registry=registry)
    except Exception:
        # Older jsonschema without `referencing`: validate without cross-refs.
        return Draft202012Validator(_load_schema(schema_name))


def _errors(validator, instance, label: str) -> int:
    n = 0
    for err in sorted(validator.iter_errors(instance), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "<root>"
        print(f"  ✗ {label}: {loc}: {err.message}")
        n += 1
    return n


# --------------------------------------------------------------------------- #
# init
# --------------------------------------------------------------------------- #
def cmd_init(args) -> int:
    dest = Path(args.path)
    if dest.exists() and not args.force:
        _die(f"{dest} already exists (use --force to overwrite)")
    example = EXAMPLES / args.type / "invairiant.config.yml"
    if example.exists():
        text = example.read_text(encoding="utf-8")
    else:
        available = ", ".join(sorted(p.name for p in EXAMPLES.iterdir() if p.is_dir()))
        print(f"note: no example for type '{args.type}' (have: {available}); writing a minimal config")
        text = _MINIMAL_CONFIG.format(name=Path.cwd().name, type=args.type)
    dest.write_text(text, encoding="utf-8")
    (Path("docs") / "audits").mkdir(parents=True, exist_ok=True)
    print(f"wrote {dest} (type: {args.type}) and ensured docs/audits/")
    print("next: edit the config, then run `invairiant validate-config`")
    return 0


_MINIMAL_CONFIG = """project:
  name: {name}
  type: {type}

canonical_docs:
  - README.md

mandatory_lenses:
  - mcconnell
  - parnas
  - security-threat
  - turing

risk_assets:
  - user data
  - availability

evidence:
  require_file_or_diff_reference: true
  allow_observations_without_evidence: true
  allow_findings_without_evidence: false

severity_policy:
  low_score_threshold: 6.0
  critical_domain_threshold: 5.0
  id_prefix: INV
"""


# --------------------------------------------------------------------------- #
# validate-config / validate-report
# --------------------------------------------------------------------------- #
def cmd_validate_config(args) -> int:
    yaml = _need("yaml")
    paths = args.paths or ["invairiant.config.yml"]
    validator = _validator("invairiant.config")
    total = 0
    for p in paths:
        path = Path(p)
        if not path.exists():
            print(f"  ✗ {p}: not found")
            total += 1
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"  ✗ {p}: invalid YAML: {exc}")
            total += 1
            continue
        errs = _errors(validator, data, p)
        total += errs
        if errs == 0:
            print(f"  ✓ {p}")
    if total:
        _die(f"{total} config problem(s)", 1)
    print("OK: config valid.")
    return 0


def cmd_validate_report(args) -> int:
    validator = _validator("audit-report")
    total = 0
    for p in args.paths:
        path = Path(p)
        if not path.exists():
            print(f"  ✗ {p}: not found")
            total += 1
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"  ✗ {p}: invalid JSON: {exc}")
            total += 1
            continue
        errs = _errors(validator, data, p)
        total += errs
        if errs == 0:
            print(f"  ✓ {p}")
    if total:
        _die(f"{total} report problem(s)", 1)
    print("OK: report valid.")
    return 0


# --------------------------------------------------------------------------- #
# collect-evidence  (gathers raw tool output as candidate evidence; never judges)
# --------------------------------------------------------------------------- #
_ADAPTERS = {
    "pytest": ["pytest", "-q"],
    "go-test": ["go", "test", "./..."],
    "golangci-lint": ["golangci-lint", "run"],
    "eslint": ["npx", "eslint", "."],
    "ruff": ["ruff", "check", "."],
    "semgrep": ["semgrep", "--error", "--quiet"],
    "vitest": ["npx", "vitest", "run"],
}


def cmd_collect_evidence(args) -> int:
    yaml = _need("yaml")
    cfg_path = Path(args.config)
    adapters = []
    if cfg_path.exists():
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        adapters = cfg.get("evidence_adapters", []) or []
    else:
        print(f"note: {cfg_path} not found; nothing declared to collect", file=sys.stderr)

    out = []
    for name in adapters:
        cmd = _ADAPTERS.get(name)
        if not cmd:
            print(f"note: no adapter mapping for '{name}' (skipping)", file=sys.stderr)
            continue
        if not shutil.which(cmd[0]):
            print(f"note: '{cmd[0]}' not installed (skipping '{name}')", file=sys.stderr)
            continue
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=args.timeout)
            output = (proc.stdout + proc.stderr).strip()
            out.append({
                "type": "command_output",
                "adapter": name,
                "command": " ".join(cmd),
                "exit_code": proc.returncode,
                "output": output[-args.max_chars:],
                "status": "candidate",
                "note": "raw adapter output; must pass stage-2 verification to become a finding",
            })
        except subprocess.TimeoutExpired:
            out.append({"type": "command_output", "adapter": name, "command": " ".join(cmd),
                        "exit_code": None, "output": f"(timed out after {args.timeout}s)", "status": "candidate"})

    payload = json.dumps(out, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        print(f"wrote {len(out)} candidate-evidence item(s) to {args.out}")
    else:
        print(payload)
    return 0


# --------------------------------------------------------------------------- #
# render-report  (deterministic JSON -> Markdown; no judgment)
# --------------------------------------------------------------------------- #
def _sev_block(title: str, findings: list, sev: str) -> list:
    rows = [f for f in findings if f.get("severity") == sev]
    if not rows:
        return []
    out = [f"## {title}", ""]
    for f in rows:
        out.append(f"### {f.get('id','?')} — {f.get('claim','')[:80]} "
                   f"({f.get('severity')}, {f.get('lens','?')}, confidence: {f.get('confidence','?')})")
        out.append("")
        out.append(f"- **Claim:** {f.get('claim','')}")
        ev = f.get("evidence", [])
        out.append("- **Evidence:**")
        for e in ev:
            bits = [e.get("type", "?")]
            if e.get("file"):
                bits.append(f"{e['file']}:{e.get('lines','')}")
            if e.get("description"):
                bits.append(e["description"])
            out.append(f"  - {' — '.join(str(b) for b in bits if b)}")
        out.append(f"- **Risk:** {f.get('risk','')}")
        out.append(f"- **Recommendation:** {f.get('recommendation','')}")
        if f.get("category"):
            out.append(f"- **Category:** {f['category']}")
        out.append("")
    return out


def cmd_render_report(args) -> int:
    data = json.loads(Path(args.report).read_text(encoding="utf-8"))
    L = ["# invAIriant Audit Report", ""]
    L.append(f"- **Date:** {data.get('date','')}")
    L.append(f"- **Audit type:** {data.get('audit_type','')}")
    L.append(f"- **Scope:** {data.get('scope','')}")
    L.append("")
    summary = data.get("summary", {})
    L += ["## Executive Summary", "", summary.get("executive_summary", ""), "",
          f"**Verdict:** {summary.get('verdict','')}", ""]
    scores = data.get("lens_scores", [])
    if scores:
        L += ["## Lens Scores", "", "| Pack | Lens | Score | Verdict |", "|---|---|---:|---|"]
        for s in scores:
            L.append(f"| {s.get('pack','')} | {s.get('lens','')} | {s.get('score','')} | {s.get('verdict','')} |")
        L.append("")
    findings = data.get("findings", [])
    L += _sev_block("Critical Findings (S0)", findings, "S0")
    L += _sev_block("High Findings (S1)", findings, "S1")
    L += _sev_block("Medium Findings (S2)", findings, "S2")
    hyp = data.get("hypotheses", [])
    L += ["## Unsupported Hypotheses", ""]
    if hyp:
        for h in hyp:
            L.append(f"- {h.get('text','')} — {h.get('rejected_reason', h.get('follow_up',''))}")
    else:
        L.append("- none")
    L.append("")
    payload = "\n".join(L)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        print(f"rendered {args.report} -> {args.out}")
    else:
        print(payload)
    return 0


# --------------------------------------------------------------------------- #
# ci-gate  (the seatbelt: fail on open S0/S1)
# --------------------------------------------------------------------------- #
def cmd_ci_gate(args) -> int:
    data = json.loads(Path(args.report).read_text(encoding="utf-8"))
    blocked = {"S0"} if args.max_severity == "S0" else {"S0", "S1"}
    open_blocking = [
        f for f in data.get("findings", [])
        if f.get("severity") in blocked and f.get("status") != "rejected"
    ]
    verdict = data.get("summary", {}).get("verdict")
    print(f"ci-gate: blocking severities {sorted(blocked)}; report verdict: {verdict}")
    if open_blocking:
        print(f"FAILED: {len(open_blocking)} open blocking finding(s):")
        for f in open_blocking:
            print(f"  ✗ {f.get('id','?')} [{f.get('severity')}] {f.get('claim','')[:90]}")
        return 1
    print("OK: no open S0/S1 findings.")
    return 0


# --------------------------------------------------------------------------- #
def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="invairiant",
                                description="Infrastructure around the agentic audit. It does not audit.")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init", help="scaffold ./invairiant.config.yml")
    pi.add_argument("--type", default="infra-service")
    pi.add_argument("--path", default="invairiant.config.yml")
    pi.add_argument("--force", action="store_true")
    pi.set_defaults(func=cmd_init)

    pc = sub.add_parser("validate-config", help="validate a config against its schema")
    pc.add_argument("paths", nargs="*")
    pc.set_defaults(func=cmd_validate_config)

    pr = sub.add_parser("validate-report", help="validate an audit report against its schema")
    pr.add_argument("paths", nargs="+")
    pr.set_defaults(func=cmd_validate_report)

    pe = sub.add_parser("collect-evidence", help="run declared adapters, emit candidate evidence JSON")
    pe.add_argument("--config", default="invairiant.config.yml")
    pe.add_argument("--out", default=None)
    pe.add_argument("--timeout", type=int, default=180)
    pe.add_argument("--max-chars", type=int, default=4000)
    pe.set_defaults(func=cmd_collect_evidence)

    prr = sub.add_parser("render-report", help="deterministically render a report JSON to Markdown")
    prr.add_argument("report")
    prr.add_argument("--out", default=None)
    prr.set_defaults(func=cmd_render_report)

    pg = sub.add_parser("ci-gate", help="exit non-zero on open S0/S1 findings")
    pg.add_argument("report")
    pg.add_argument("--max-severity", choices=["S0", "S1"], default="S1",
                    help="S1 (default) blocks S0+S1; S0 blocks only S0")
    pg.set_defaults(func=cmd_ci_gate)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
