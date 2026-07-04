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
import re
import shutil
import subprocess
import sys
from pathlib import Path


def _looks_like_root(p: Path) -> bool:
    return (p / "schemas").is_dir() and (p / "lenses").is_dir()


def framework_root() -> Path:
    """Resolve the framework tree. Order: $INVAIRIANT_HOME, the repo layout
    (cli/invairiant.py -> repo root), then a search upward from the script and
    the cwd. This lets the installed `invairiant` command work from inside a
    checkout regardless of how it was installed."""
    env = os.environ.get("INVAIRIANT_HOME")
    if env:
        return Path(env).expanduser().resolve()
    here = Path(__file__).resolve()
    cand = here.parent.parent
    if _looks_like_root(cand):
        return cand
    for start in (here.parent, Path.cwd().resolve()):
        for d in (start, *start.parents):
            if _looks_like_root(d):
                return d
    return cand  # best effort; schema loads will emit a clear error


def known_lens_ids() -> set:
    """The set of valid lens ids = basenames of lenses/*/*.md (minus README).
    Cross-listed stubs reuse a canonical id, so the set stays deduplicated."""
    lenses = framework_root() / "lenses"
    return {p.stem for p in lenses.glob("*/*.md") if p.stem != "README"}


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


def _check_lens_refs(data: dict, label: str) -> int:
    """Referential integrity: config lens ids must exist in the lens library.
    Catches a typo'd mandatory_lens at validate time instead of mid-audit."""
    known = known_lens_ids()
    if not known:
        return 0  # library not resolvable here — skip rather than false-fail
    n = 0
    for key in ("mandatory_lenses", "critical_lenses"):
        for lid in (data.get(key) or []):
            if lid not in known:
                print(f"  ✗ {label}: {key}: unknown lens id '{lid}' (no lenses/*/{lid}.md)")
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
        errs += _check_lens_refs(data if isinstance(data, dict) else {}, p)
        total += errs
        if errs == 0:
            print(f"  ✓ {p}")
    if total:
        _die(f"{total} config problem(s)", 1)
    print("OK: config valid.")
    return 0


_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]{3,}$")


def _repo_root() -> Path:
    """The git repo root, so audit memory resolves the same from any subdir.
    Falls back to CWD outside a git repo (e.g. a temp dir in tests)."""
    try:
        p = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=5)
        if p.returncode == 0 and p.stdout.strip():
            return Path(p.stdout.strip())
    except Exception:  # noqa: BLE001
        pass
    return Path.cwd()


def _history_dir() -> Path:
    return _repo_root() / ".invairiant" / "history"


def _claim_key(text: str) -> str:
    """A normalized key for matching a claim/hypothesis across audits."""
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())[:80]


# Applied in order before any value enters committed memory.
_SECRET_SUBS = [
    (re.compile(r"-----BEGIN[^-]*PRIVATE KEY-----[\s\S]*?-----END[^-]*PRIVATE KEY-----"), "[REDACTED KEY]"),
    (re.compile(r"-----BEGIN[^-]*PRIVATE KEY-----"), "[REDACTED KEY]"),
    (re.compile(r"(?i)\b(authorization)\b\s*[:=]\s*(?:bearer\s+)?\S+"), r"\1=[REDACTED]"),
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{12,}"), "bearer [REDACTED]"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[REDACTED AWS KEY]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"), "[REDACTED TOKEN]"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"), "[REDACTED TOKEN]"),
    (re.compile(r"(?i)\b(api[_-]?key|secret|token|password|passwd)\b\s*[=:]\s*\S+"), r"\1=[REDACTED]"),
]


def _sanitize(s):
    """Redact secret-like substrings before a value enters committed memory.
    Audit memory never stores raw evidence blobs — only distilled fields — so
    this is a second line of defense on the text it does store."""
    if not isinstance(s, str):
        return s
    for rx, repl in _SECRET_SUBS:
        s = rx.sub(repl, s)
    return s[:600]


def _report_threshold(config_path: str) -> float:
    try:
        import yaml
        p = Path(config_path)
        if p.exists():
            cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            return float((cfg.get("severity_policy") or {}).get("low_score_threshold", 6.0))
    except Exception:  # noqa: BLE001
        pass
    return 6.0


def _semantic_report_errors(data: dict, low_threshold: float):
    """Protocol rules the JSON schema can't express. Returns (errors, warnings)."""
    errs, warns = [], []
    findings = data.get("findings", [])
    ids = [f.get("id") for f in findings]
    idset = set(ids)
    for d in {i for i in ids if ids.count(i) > 1}:
        errs.append(f"duplicate finding id '{d}'")
    # S0/S1 confidence (belt-and-suspenders over the schema)
    for f in findings:
        if f.get("severity") in ("S0", "S1") and f.get("confidence") not in ("high", "medium"):
            errs.append(f"{f.get('id')}: {f.get('severity')} requires confidence high/medium (got {f.get('confidence')})")
    # verdict must derive from open findings, never from score averages
    verdict = (data.get("summary") or {}).get("verdict")
    openf = [f for f in findings if f.get("status") != "rejected"]
    if any(f.get("severity") == "S0" for f in openf) and verdict != "fail":
        errs.append(f"open S0 finding present but verdict is '{verdict}' (must be 'fail')")
    if any(f.get("severity") == "S1" for f in openf) and verdict == "pass":
        errs.append("open S1 finding present but verdict is 'pass' (must be at best 'pass_with_conditions')")
    # lens-score referential integrity
    lens_with_finding = {f.get("lens") for f in findings}
    for s in data.get("lens_scores", []):
        lens = s.get("lens")
        try:
            score = float(s.get("score"))
        except (TypeError, ValueError):
            score = None
        if score is not None and score < low_threshold:
            if lens not in lens_with_finding and not (s.get("evidence_refs") or []):
                warns.append(f"lens '{lens}' scored {score} (< {low_threshold}) but has no finding and no evidence_refs")
        for r in (s.get("evidence_refs") or []):
            if _ID_RE.match(str(r)) and r not in idset:
                errs.append(f"lens '{lens}' evidence_ref '{r}' is not a finding id in this report")
    # required_actions must reference real findings
    for a in (data.get("summary") or {}).get("required_actions", []):
        for fid in (a.get("finding_ids") or []):
            if fid not in idset:
                errs.append(f"required_action references unknown finding id '{fid}'")
    # rejected hypotheses must be kept, not dropped
    if "hypotheses" not in data:
        warns.append("no 'hypotheses' section — rejected hypotheses must be kept, not deleted")
    # memory-aware: warn if a finding reuses a previously-rejected claim
    rejp = _history_dir() / "rejected-hypotheses.jsonl"
    if rejp.exists():
        rejected = set()
        for line in rejp.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    rejected.add(json.loads(line).get("claim_key"))
                except Exception:  # noqa: BLE001
                    pass
        for f in findings:
            if _claim_key(f.get("claim", "")) in rejected:
                warns.append(f"{f.get('id')}: claim matches a previously-rejected hypothesis in audit memory — re-verify before shipping")
    return errs, warns


_MD_REQUIRED = ["Verdict", "Hypotheses"]


def _md_report_errors(text: str, label: str):
    errs = []
    if not re.search(r"^#\s+\S", text, re.M):
        errs.append(f"{label}: no H1 title")
    if not re.search(r"^##\s+\S", text, re.M):
        errs.append(f"{label}: no section headings")
    for needle in _MD_REQUIRED:
        if needle.lower() not in text.lower():
            errs.append(f"{label}: missing '{needle}'")
    for e in errs:
        print(f"  ✗ {e}")
    return len(errs)


def cmd_validate_report(args) -> int:
    threshold = _report_threshold(args.config)
    validator = None if args.md else _validator("audit-report")
    total = 0
    for p in args.paths:
        path = Path(p)
        if not path.exists():
            print(f"  ✗ {p}: not found")
            total += 1
            continue
        text = path.read_text(encoding="utf-8")
        if args.md or p.endswith(".md"):
            n = _md_report_errors(text, p)
            total += n
            if n == 0:
                print(f"  ✓ {p} (markdown structure)")
            continue
        try:
            data = json.loads(text)
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ {p}: invalid JSON: {exc}")
            total += 1
            continue
        errs = _errors(validator, data, p)
        if not args.schema_only:
            serrs, warns = _semantic_report_errors(data, threshold)
            for w in warns:
                print(f"  ⚠ {p}: {w}")
            for e in serrs:
                print(f"  ✗ {p}: {e}")
            errs += len(serrs)
        total += errs
        if errs == 0:
            print(f"  ✓ {p}")
    if total:
        _die(f"{total} report problem(s)", 1)
    print("OK: report valid." + ("" if args.md or args.schema_only else " (schema + semantic)"))
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


def _run_adapters(adapters: list, timeout: int, max_chars: int) -> list:
    """Run declared evidence adapters, capturing raw output as candidate
    evidence. Judges nothing — every item must still pass stage-2 verification."""
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
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            output = (proc.stdout + proc.stderr).strip()
            out.append({
                "type": "command_output",
                "adapter": name,
                "command": " ".join(cmd),
                "exit_code": proc.returncode,
                "output": output[-max_chars:],
                "status": "candidate",
                "note": "raw adapter output; must pass stage-2 verification to become a finding",
            })
        except subprocess.TimeoutExpired:
            out.append({"type": "command_output", "adapter": name, "command": " ".join(cmd),
                        "exit_code": None, "output": f"(timed out after {timeout}s)", "status": "candidate"})
    return out


def cmd_collect_evidence(args) -> int:
    yaml = _need("yaml")
    cfg_path = Path(args.config)
    adapters = []
    if cfg_path.exists():
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        adapters = cfg.get("evidence_adapters", []) or []
    else:
        print(f"note: {cfg_path} not found; nothing declared to collect", file=sys.stderr)

    out = _run_adapters(adapters, args.timeout, args.max_chars)
    payload = json.dumps(out, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        print(f"wrote {len(out)} candidate-evidence item(s) to {args.out}")
    else:
        print(payload)
    return 0


# --------------------------------------------------------------------------- #
# collect  (the full deterministic evidence bundle; the CLI's core helper)
# --------------------------------------------------------------------------- #
_SIGNAL_PATTERNS = {
    "model_calls": r"openai|anthropic|claude|\bllm\b|chat\.completions|messages\.create|invoke_model|generate_content|\bcompletion\(",
    "shell": r"subprocess\.|os\.system|\bPopen\b|child_process|\bexec\(|sh -c",
    "sql": r"SELECT .*FROM|INSERT INTO|UPDATE .*SET|DELETE FROM|\.execute\(|\.query\(|\braw\(",
    "secrets": r"api[_-]?key|secret|access[_-]?token|BEGIN [A-Z ]*PRIVATE KEY|password\s*=",
    "todo": r"TODO|FIXME|XXX|HACK",
}
_IMPORT_PATTERN = r"^\s*(import\s+\S|from\s+\S+\s+import|import\s+.*\bfrom\b|#include|require\()"


def _run(cmd: list, timeout: int = 60):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except Exception as exc:  # noqa: BLE001
        return None, "", str(exc)


def _git(args: list) -> str:
    rc, out, _ = _run(["git"] + args)
    return out.strip() if rc == 0 else ""


# Bounds so `collect` stays fast and memory-safe on very large repos.
_MAX_SCAN_FILES = 4000        # tracked files read in the no-ripgrep fallback
_MAX_FILE_BYTES = 512 * 1024  # skip files larger than this (likely data/binary)


def _is_probably_binary(path: Path, sniff: int = 1024) -> bool:
    try:
        with path.open("rb") as fh:
            return b"\x00" in fh.read(sniff)
    except Exception:  # noqa: BLE001
        return True


def _rg(pattern: str, cap: int) -> list:
    items = []
    _, out, _ = _run(["rg", "-n", "-i", "--no-heading", "--color", "never",
                      "-e", pattern, "--", "."], timeout=60)
    for line in out.splitlines():
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        f, ln, content = parts
        items.append({"file": f, "line": int(ln) if ln.isdigit() else None,
                      "match": content.strip()[:200]})
        if len(items) >= cap:
            break
    return items


def _ls_files(path: str = None) -> list:
    """Tracked files, optionally bounded to a path (dir or file)."""
    cmd = ["git", "ls-files"]
    if path:
        cmd += ["--", path]
    _, out, _ = _run(cmd)
    return [f for f in out.splitlines() if f.strip()]


def _scan_fileset(patterns: dict, cap: int, budget: dict, files: list) -> dict:
    """One bounded pass over a given file set (skipping large/binary files,
    capping the count) — O(files), never O(files x patterns). Pointers, not findings."""
    compiled = {k: re.compile(p, re.I) for k, p in patterns.items()}
    out = {k: [] for k in patterns}
    for f in files:
        p = Path(f)
        if not p.is_file():
            continue
        if budget["files_scanned"] >= budget["max_files"]:
            budget["truncated"] = True
            break
        try:
            if p.stat().st_size > budget["max_bytes"] or _is_probably_binary(p):
                budget["skipped_large_or_binary"] += 1
                continue
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        budget["files_scanned"] += 1
        for i, line in enumerate(text.splitlines(), 1):
            for k, rx in compiled.items():
                if len(out[k]) < cap and rx.search(line):
                    out[k].append({"file": f, "line": i, "match": line.strip()[:200]})
    return out


def _scan(patterns: dict, cap: int, budget: dict, files: list = None) -> dict:
    """Grep candidate pointers per named pattern. When `files` is given (a bounded
    scope), scan ONLY those. When None (repo scope), use ripgrep if present, else
    a bounded pass over all tracked files. Candidate pointers, not findings."""
    if files is None:
        if shutil.which("rg"):
            return {k: _rg(p, cap) for k, p in patterns.items()}
        files = _ls_files()
    return _scan_fileset(patterns, cap, budget, files)


def _new_budget() -> dict:
    return {"max_files": _MAX_SCAN_FILES, "max_bytes": _MAX_FILE_BYTES,
            "files_scanned": 0, "skipped_large_or_binary": 0, "truncated": False,
            "ripgrep": bool(shutil.which("rg"))}


def _lang_stats(files: list = None) -> dict:
    if files is None:
        files = _ls_files()
    stats: dict = {}
    for i, f in enumerate(files):
        if i >= _MAX_SCAN_FILES:
            break
        p = Path(f)
        if not p.is_file():
            continue
        try:
            if p.stat().st_size > _MAX_FILE_BYTES:
                continue
            n = sum(1 for _ in p.open("rb"))
        except Exception:  # noqa: BLE001
            continue
        ext = p.suffix or "(none)"
        stats[ext] = stats.get(ext, 0) + n
    return dict(sorted(stats.items(), key=lambda kv: -kv[1])[:15])


def _repo_tree(files: list = None) -> list:
    if files is None:
        files = _ls_files()
    top: dict = {}
    for f in files:
        head = f.split("/", 1)[0]
        top[head] = top.get(head, 0) + 1
    return [{"entry": k, "tracked_files": v} for k, v in sorted(top.items())]


# A scope resolver turns a bounded scope (kind + target) into a file set, so
# `collect` computes the whole bundle OVER that set — bounded, never a general
# repo search. Only the `repo` scope is (explicitly) unbounded.
_ADR_MAX_SCOPE_FILES = 200


class ScopeError(Exception):
    """A scope that cannot be bounded — collect fails closed rather than
    silently scanning the whole repo."""


def _extract_adr_refs(text: str):
    """Pull the file paths and code identifiers an ADR names (backtick spans +
    bare path-like tokens). Returns (paths, identifiers)."""
    toks = re.findall(r"`([^`\n]{2,80})`", text)
    toks += re.findall(r"(?<![\w`/])([A-Za-z0-9_][\w./\-]*/[\w./\-]+\.\w{1,6})", text)
    paths, idents = set(), set()
    for tok in toks:
        tok = tok.strip().strip("()").split(":")[0]
        if not tok:
            continue
        if "/" in tok or re.search(r"\.\w{1,6}$", tok):
            paths.add(tok)
        elif re.match(r"^[A-Za-z_][A-Za-z0-9_]{2,}$", tok):
            idents.add(tok)
    return paths, idents


def _resolve_scope(args) -> dict:
    """Deterministically bound the audit scope. Raises ScopeError (fail closed)
    when a scope cannot be bounded."""
    kind = getattr(args, "scope", None) or ("range" if args.range else "working")

    if kind == "working":
        _, names, _ = _run(["git", "status", "--porcelain"])
        files = [l[3:] for l in names.splitlines() if l.strip()]
        _, diff, _ = _run(["git", "diff"])
        return {"kind": kind, "target": "working tree", "files": files,
                "diff": diff or None, "docs": [], "bounded": True,
                "note": "uncommitted working-tree changes"}

    if kind == "range":
        rng = args.range
        if not rng:
            raise ScopeError("--scope range requires --range A..B")
        rc, names, err = _run(["git", "diff", "--name-only", rng])
        if rc != 0:
            raise ScopeError(f"range '{rng}' did not resolve ({err.strip()[:120]})")
        files = [f for f in names.splitlines() if f.strip()]
        _, diff, _ = _run(["git", "diff", rng])
        return {"kind": kind, "target": rng, "files": files, "diff": diff or None,
                "docs": [], "bounded": True, "note": f"files changed in {rng}"}

    if kind == "commit":
        sha = args.commit
        if not sha:
            raise ScopeError("--scope commit requires --commit <sha>")
        rc, names, err = _run(["git", "show", "--name-only", "--format=", sha])
        if rc != 0:
            raise ScopeError(f"commit '{sha}' did not resolve ({err.strip()[:120]})")
        files = [f for f in names.splitlines() if f.strip()]
        _, diff, _ = _run(["git", "show", sha])
        return {"kind": kind, "target": sha, "files": files, "diff": diff or None,
                "docs": [], "bounded": True, "note": f"files in commit {sha[:12]}"}

    if kind == "module":
        path = args.path
        if not path:
            raise ScopeError("--scope module requires --path <dir-or-file>")
        if not Path(path).exists():
            raise ScopeError(f"module path '{path}' does not exist")
        files = _ls_files(path)
        if not files:
            raise ScopeError(f"module path '{path}' has no tracked files")
        return {"kind": kind, "target": path, "files": files, "diff": None,
                "docs": [], "bounded": True, "snapshot": True,
                "note": f"tracked files under {path} (snapshot)"}

    if kind == "adr":
        adr = args.path
        if not adr or not Path(adr).is_file():
            raise ScopeError("--scope adr requires --path <adr-file>")
        text = Path(adr).read_text(encoding="utf-8", errors="ignore")
        docs = [{"path": adr, "excerpt": text[:8000]}]
        paths, idents = _extract_adr_refs(text)
        tracked = set(_ls_files())
        refs = set()
        for pth in paths:
            pfx = pth.rstrip("/") + "/"
            if pth in tracked:
                refs.add(pth)
            elif any(t.startswith(pfx) for t in tracked):
                refs.update(t for t in tracked if t.startswith(pfx))
        if idents:
            idre = re.compile(r"\b(" + "|".join(re.escape(i) for i in list(idents)[:40]) + r")\b")
            for f in tracked:
                if len(refs) > _ADR_MAX_SCOPE_FILES:
                    break
                p = Path(f)
                if not p.is_file() or str(p) == adr:
                    continue
                try:
                    if p.stat().st_size > _MAX_FILE_BYTES or _is_probably_binary(p):
                        continue
                    if idre.search(p.read_text(encoding="utf-8", errors="ignore")):
                        refs.add(f)
                except Exception:  # noqa: BLE001
                    continue
        narrow = getattr(args, "narrow", None)
        if narrow:
            pfx = narrow.rstrip("/") + "/"
            refs = {f for f in refs if f == narrow or f.startswith(pfx)}
        files = sorted(refs)
        if not files:
            raise ScopeError(
                "ADR references did not resolve to tracked code"
                + (f" under --narrow '{narrow}'" if narrow else "; re-run with --narrow <path>"))
        if len(files) > _ADR_MAX_SCOPE_FILES and not narrow:
            raise ScopeError(f"ADR references resolved too broadly ({len(files)} files); "
                             "re-run with --narrow <path>")
        return {"kind": kind, "target": adr, "files": files, "diff": None, "docs": docs,
                "bounded": True, "snapshot": True,
                "note": f"ADR + the code it references ({len(files)} files)"
                        + (f", narrowed to {narrow}" if narrow else "")}

    if kind == "repo":
        return {"kind": kind, "target": "whole repo", "files": _ls_files(), "diff": None,
                "docs": [], "bounded": False,
                "note": "explicitly unbounded (full-audit scope)"}

    raise ScopeError(f"unknown scope '{kind}'")


def _scope_detail(scope: dict) -> dict:
    """The change detail (name-status + diffstat) for change scopes; a snapshot
    summary otherwise."""
    kind, target = scope["kind"], scope["target"]
    if kind == "commit":
        _, ns, _ = _run(["git", "show", "--name-status", "--format=", target])
        _, st, _ = _run(["git", "show", "--stat", "--format=", target])
        changed = [{"status": l.split("\t")[0], "file": l.split("\t")[-1]}
                   for l in ns.splitlines() if "\t" in l]
    elif kind == "range":
        _, ns, _ = _run(["git", "diff", "--name-status", target])
        _, st, _ = _run(["git", "diff", "--stat", target])
        changed = [{"status": l.split("\t")[0], "file": l.split("\t")[-1]}
                   for l in ns.splitlines() if l.strip()]
    elif kind == "working":
        _, ns, _ = _run(["git", "status", "--porcelain"])
        _, st, _ = _run(["git", "diff", "--stat"])
        changed = [{"status": l[:2].strip(), "file": l[3:]}
                   for l in ns.splitlines() if l.strip()]
    else:  # module / adr / repo — a snapshot, not a change
        return {"kind": kind, "target": target, "snapshot": True,
                "changed_files": [], "diffstat": ""}
    return {"kind": kind, "target": target, "changed_files": changed,
            "diffstat": st.strip()[:4000]}


def _generated_mass(scope: dict) -> dict:
    kind, target = scope["kind"], scope["target"]
    if kind == "commit":
        num = _run(["git", "show", "--numstat", "--format=", target])[1]
        short = _run(["git", "show", "--shortstat", "--format=", target])[1]
    elif kind == "range":
        num = _run(["git", "diff", "--numstat", target])[1]
        short = _run(["git", "diff", "--shortstat", target])[1]
    elif kind == "working":
        num = _run(["git", "diff", "--numstat"])[1]
        short = _run(["git", "diff", "--shortstat"])[1]
    else:  # module / adr / repo — a snapshot: report the size of the file set
        sized, total = [], 0
        for f in scope["files"]:
            p = Path(f)
            try:
                n = sum(1 for _ in p.open("rb")) if (p.is_file() and p.stat().st_size <= _MAX_FILE_BYTES) else 0
            except Exception:  # noqa: BLE001
                n = 0
            total += n
            sized.append({"file": f, "lines": n})
        sized.sort(key=lambda x: -x["lines"])
        return {"snapshot": True, "files": len(scope["files"]),
                "total_lines": total, "largest_files": sized[:10]}
    files = []
    for l in num.splitlines():
        parts = l.split("\t")
        if len(parts) >= 3 and parts[0].isdigit():
            files.append({"file": parts[2], "added": int(parts[0]),
                          "deleted": int(parts[1]) if parts[1].isdigit() else 0})
    files.sort(key=lambda x: -(x["added"] + x["deleted"]))
    return {"shortstat": short.strip(), "largest_changed": files[:10]}


def _config_and_docs():
    cfg, docs = None, []
    try:
        import yaml
    except Exception:  # noqa: BLE001
        return cfg, docs
    p = Path("invairiant.config.yml")
    if p.exists():
        cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    for d in ((cfg or {}).get("canonical_docs") or []):
        dp = Path(d)
        if dp.is_file():
            lines = dp.read_text(encoding="utf-8", errors="ignore").splitlines()[:40]
            docs.append({"path": d, "excerpt": "\n".join(lines)[:2000]})
        elif dp.is_dir():
            docs.append({"path": d, "note": "directory"})
    return cfg, docs


def _known_rejected() -> list:
    p = _history_dir() / "rejected-hypotheses.jsonl"
    out = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:  # noqa: BLE001
                pass
    return out


def cmd_collect(args) -> int:
    # Bound the scope first — FAIL CLOSED rather than silently scan the whole repo.
    try:
        scope = _resolve_scope(args)
    except ScopeError as exc:
        print(f"collect: scope could not be bounded — {exc}", file=sys.stderr)
        return 2
    scan_files = None if scope["kind"] == "repo" else scope["files"]

    cfg, docs = _config_and_docs()
    docs = list(docs) + list(scope.get("docs", []))   # ADR text joins canonical docs
    git_info = {
        "head": _git(["rev-parse", "HEAD"]),
        "branch": _git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "dirty": bool(_git(["status", "--porcelain"])),
    }
    adapters = (cfg or {}).get("evidence_adapters", []) or []
    budget = _new_budget()
    patterns = dict(_SIGNAL_PATTERNS)
    patterns["import_boundaries"] = _IMPORT_PATTERN
    scanned = _scan(patterns, args.cap, budget, files=scan_files)
    imports = scanned.pop("import_boundaries")

    resolved_scope = {
        "kind": scope["kind"],
        "target": scope["target"],
        "bounded": scope["bounded"],
        "files_in_scope": len(scope["files"]),
        "sample_files": scope["files"][:25],
        "has_diff": scope.get("diff") is not None,
        "docs": [d.get("path") for d in scope.get("docs", [])],
        "note": scope.get("note", ""),
    }
    bundle = {
        "schema": "invairiant.evidence-bundle/v1",
        "notice": ("All signals below are candidate pointers gathered by a deterministic "
                   "helper over the RESOLVED SCOPE ONLY — NOT findings, and not a general "
                   "repo search. The /invairiant skill applies lenses; only verified, "
                   "evidence-bound claims become findings. The CLI never judges."),
        "resolved_scope": resolved_scope,
        "generated_for": {
            "repo": Path.cwd().name,
            "commit": git_info["head"],
            "branch": git_info["branch"],
            "scope": scope["kind"],
            "target": scope["target"],
        },
        "scope": _scope_detail(scope),
        "repo_tree": _repo_tree(files=scan_files),
        "language_stats": _lang_stats(files=scan_files),
        "tests_ci": {
            "git": git_info,
            "adapters_ran": bool(args.run_adapters),
            "adapters": _run_adapters(adapters, args.timeout, args.max_chars) if args.run_adapters else [],
        },
        "config": cfg,
        "canonical_docs": docs,
        "signals": scanned,
        "import_boundaries": imports,
        "generated_mass": _generated_mass(scope),
        "known_rejected": _known_rejected(),
        "limits": budget,
    }
    payload = json.dumps(bundle, indent=2, ensure_ascii=False)
    unb = "" if scope["bounded"] else ", UNBOUNDED"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        n = sum(len(v) for v in bundle["signals"].values())
        print(f"wrote evidence bundle to {args.out} — scope={scope['kind']} "
              f"({resolved_scope['files_in_scope']} file(s){unb}); {n} candidate "
              f"signal(s); raw — keep it gitignored")
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
# render-comment  (deterministic PR-comment render; no judgment)
# --------------------------------------------------------------------------- #
_SEV_ORDER = {"S0": 0, "S1": 1, "S2": 2, "S3": 3, "NOTE": 4}


def _ev_short(e: dict) -> str:
    t = e.get("type", "")
    if e.get("file"):
        return f"`{e['file']}:{e.get('lines', '')}`"
    if t == "doc_code_contradiction":
        return f"{e.get('doc', '')} vs {e.get('code', '')}"
    if t == "diff_hunk":
        return "diff hunk"
    if t == "test_failure":
        return e.get("test", "test")
    if t == "command_output":
        return f"`{e.get('command', '')}`"
    if t in ("ci_output", "incident"):
        return e.get("reference", "")
    return e.get("description", t)


def cmd_render_comment(args) -> int:
    data = json.loads(Path(args.report).read_text(encoding="utf-8"))
    summary = data.get("summary", {})
    lenses = ", ".join(dict.fromkeys(s.get("lens", "") for s in data.get("lens_scores", [])))
    proj = data.get("project", {})
    audited = proj.get("commit_range") or proj.get("branch") or (data.get("scope", "")[:60])
    title = data.get("title", "")
    header = title if "pr audit" in title.lower() else f"invAIriant PR Audit — {title}"
    L = [f"# {header}", ""]
    L.append(f"**Verdict:** {summary.get('verdict', '')}")
    L.append(f"**Audited:** {audited} · **Lenses:** {lenses}")
    L.append("")
    findings = [f for f in data.get("findings", []) if f.get("status") != "rejected"]
    findings.sort(key=lambda f: _SEV_ORDER.get(f.get("severity"), 9))
    if findings:
        L += ["## Findings", ""]
        for f in findings:
            ev = f.get("evidence", [])
            L.append(f"**{f.get('id', '?')} ({f.get('severity')}, {f.get('lens', '?')}, "
                     f"confidence {f.get('confidence', '?')})** — {f.get('claim', '')}")
            if ev:
                L.append(f"- Evidence: {_ev_short(ev[0])}"
                         + (f" — {ev[0].get('description')}" if ev[0].get("description") else ""))
            L.append(f"- Risk: {f.get('risk', '')}")
            L.append(f"- Fix: {f.get('recommendation', '')}")
            L.append("")
    conditions = [a for a in summary.get("required_actions", []) if a.get("blocking")]
    if conditions:
        L += ["## Conditions", ""]
        for i, a in enumerate(conditions, 1):
            who = f" ({a['owner']})" if a.get("owner") else ""
            L.append(f"{i}. {a.get('action', '')}{who}")
        L.append("")
    obs = data.get("observations", [])
    hyp = data.get("hypotheses", [])
    if obs or hyp:
        L += ["## Observations / Hypotheses (non-blocking)", ""]
        for o in obs:
            L.append(f"- {o.get('text', '')}")
        for h in hyp:
            reason = h.get("rejected_reason") or h.get("follow_up") or ""
            L.append(f"- Rejected hypothesis: {h.get('text', '')}" + (f" — {reason}" if reason else ""))
        L.append("")
    payload = "\n".join(L)
    if args.out:
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        print(f"rendered PR comment: {args.report} -> {args.out}")
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
# record / history  (committed, sanitized audit memory)
# --------------------------------------------------------------------------- #
def cmd_record(args) -> int:
    data = json.loads(Path(args.report).read_text(encoding="utf-8"))
    date = data.get("date", "")
    audit = args.audit_id or data.get("title", "")[:80] or date
    audit_csv = audit.replace(",", ";").replace("\n", " ")
    hist = Path(args.dir) if args.dir else _history_dir()
    hist.mkdir(parents=True, exist_ok=True)

    # Idempotent by audit label: re-recording the same audit would duplicate
    # rows and skew `history` trends. Skip unless --force.
    freg = hist / "finding-registry.jsonl"
    if freg.exists() and not args.force:
        seen = set()
        for line in freg.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    seen.add(json.loads(line).get("audit"))
                except Exception:  # noqa: BLE001
                    pass
        if audit in seen:
            print(f"audit '{audit}' is already in memory — skipping (use --force to re-record).")
            return 0

    rejected = [h for h in data.get("hypotheses", []) if h.get("rejected_reason")]
    with (hist / "rejected-hypotheses.jsonl").open("a", encoding="utf-8") as f:
        for h in rejected:
            f.write(json.dumps({
                "date": date, "audit": audit, "lens": h.get("lens"),
                "text": _sanitize(h.get("text", "")),
                "rejected_reason": _sanitize(h.get("rejected_reason", "")),
                "claim_key": _claim_key(h.get("text", "")),
            }, ensure_ascii=False) + "\n")

    findings = data.get("findings", [])
    with freg.open("a", encoding="utf-8") as f:
        for fd in findings:
            f.write(json.dumps({
                "date": date, "audit": audit, "id": fd.get("id"),
                "severity": fd.get("severity"), "lens": fd.get("lens"),
                "category": fd.get("category"), "claim": _sanitize(fd.get("claim", "")),
                "status": fd.get("status", "verified"),
                "claim_key": _claim_key(fd.get("claim", "")),
            }, ensure_ascii=False) + "\n")

    scores = data.get("lens_scores", [])
    csvp = hist / "lens-score-history.csv"
    new = not csvp.exists()
    with csvp.open("a", encoding="utf-8") as f:
        if new:
            f.write("date,audit,lens,score\n")
        for s in scores:
            f.write(f"{date},{audit_csv},{s.get('lens')},{s.get('score')}\n")

    print(f"recorded into {hist}/ — {len(findings)} finding(s), "
          f"{len(rejected)} rejected hypothes(e)s, {len(scores)} lens score(s). "
          f"Sanitized; commit history/, keep cache/ local.")
    return 0


def cmd_history(args) -> int:
    import csv as _csv
    from collections import Counter, defaultdict
    hist = Path(args.dir) if args.dir else _history_dir()
    csvp = hist / "lens-score-history.csv"
    if not csvp.exists():
        _die(f"no audit memory at {csvp} — run `invairiant record` first", 1)
    by_lens = defaultdict(list)
    for r in _csv.DictReader(csvp.open(encoding="utf-8")):
        if args.lens and r["lens"] != args.lens:
            continue
        try:
            by_lens[r["lens"]].append((r["date"], float(r["score"])))
        except (KeyError, ValueError):
            pass
    print("lens score history (oldest → newest):")
    for lens, seq in sorted(by_lens.items()):
        seq.sort()
        scores = [s for _, s in seq]
        trend = " → ".join(f"{s:g}" for s in scores)
        flag = "   ⚠ two consecutive drops" if len(scores) >= 3 and scores[-1] < scores[-2] < scores[-3] else ""
        print(f"  {lens:26} {trend}{flag}")
    freg = hist / "finding-registry.jsonl"
    if freg.exists():
        keys = Counter()
        labels = {}
        for line in freg.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            k = rec.get("claim_key")
            if k:
                keys[k] += 1
                labels[k] = rec.get("claim", "")[:60]
        recurring = [(k, c) for k, c in keys.items() if c > 1]
        if recurring:
            print("recurring findings (seen in >1 audit):")
            for k, c in sorted(recurring, key=lambda x: -x[1]):
                print(f"  {c}×  {labels.get(k, k)}")
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

    pr = sub.add_parser("validate-report", help="validate an audit report: schema + protocol semantics")
    pr.add_argument("paths", nargs="+")
    pr.add_argument("--schema-only", action="store_true", help="skip the semantic checks")
    pr.add_argument("--md", action="store_true", help="structural lint of a markdown report (no schema)")
    pr.add_argument("--config", default="invairiant.config.yml", help="config for the low-score threshold")
    pr.set_defaults(func=cmd_validate_report)

    pcol = sub.add_parser("collect", help="gather a deterministic, scope-bounded evidence bundle for the skill")
    pcol.add_argument("--scope", choices=["working", "range", "commit", "module", "adr", "repo"],
                      default=None, help="bounded audit scope (default: range if --range given, else working)")
    pcol.add_argument("--range", default=None, help="git range A..B (for --scope range)")
    pcol.add_argument("--commit", default=None, help="commit sha (for --scope commit)")
    pcol.add_argument("--path", default=None, help="module dir/file (--scope module) or ADR file (--scope adr)")
    pcol.add_argument("--narrow", default=None, help="restrict an ADR scope's code to this subtree")
    pcol.add_argument("--out", default=None, help="write bundle here (convention: .invairiant/cache/, gitignored)")
    pcol.add_argument("--run-adapters", action="store_true", help="also run declared evidence_adapters (slower)")
    pcol.add_argument("--timeout", type=int, default=180)
    pcol.add_argument("--max-chars", type=int, default=4000)
    pcol.add_argument("--cap", type=int, default=50, help="max signal hits per category")
    pcol.set_defaults(func=cmd_collect)

    pe = sub.add_parser("collect-evidence", help="[alias] run declared adapters only (see `collect` for the full bundle)")
    pe.add_argument("--config", default="invairiant.config.yml")
    pe.add_argument("--out", default=None)
    pe.add_argument("--timeout", type=int, default=180)
    pe.add_argument("--max-chars", type=int, default=4000)
    pe.set_defaults(func=cmd_collect_evidence)

    prr = sub.add_parser("render-report", help="deterministically render a report JSON to Markdown")
    prr.add_argument("report")
    prr.add_argument("--out", default=None)
    prr.set_defaults(func=cmd_render_report)

    prc = sub.add_parser("render-comment", help="render a report JSON into a paste-ready PR comment")
    prc.add_argument("report")
    prc.add_argument("--out", default=None)
    prc.set_defaults(func=cmd_render_comment)

    pg = sub.add_parser("ci-gate", help="exit non-zero on open S0/S1 findings")
    pg.add_argument("report")
    pg.add_argument("--max-severity", choices=["S0", "S1"], default="S1",
                    help="S1 (default) blocks S0+S1; S0 blocks only S0")
    pg.set_defaults(func=cmd_ci_gate)

    prec = sub.add_parser("record", help="append a report's distilled, sanitized memory to .invairiant/history/")
    prec.add_argument("report")
    prec.add_argument("--audit-id", default=None)
    prec.add_argument("--dir", default=None, help="default: <repo-root>/.invairiant/history")
    prec.add_argument("--force", action="store_true", help="re-record even if this audit is already in memory")
    prec.set_defaults(func=cmd_record)

    phi = sub.add_parser("history", help="show lens-score trends and recurring findings from audit memory")
    phi.add_argument("--lens", default=None)
    phi.add_argument("--dir", default=None, help="default: <repo-root>/.invairiant/history")
    phi.set_defaults(func=cmd_history)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
