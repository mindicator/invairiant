"""Schema loading, validators, the `validate-config` / `validate-report`
commands, the semantic (protocol) linter, and the `ci-gate` seatbelt.

The CLI serves the invAIriant audit; it never runs a lens, invents a
finding, or assigns a score.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .history import _claim_key, _history_dir
from .subprocesses import _run
from .term import _bad, _c, _die, _dim, _ok, _sev, _warn

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
    # Installed via pip (outside a checkout): the wheel bundles the framework
    # data next to the module under invairiant_framework/. This is what makes
    # `pip install invairiant` work without INVAIRIANT_HOME.
    bundled = here.parent / "invairiant_framework"
    if _looks_like_root(bundled):
        return bundled
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


def _need(module: str):
    try:
        return __import__(module)
    except ImportError:
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
    except ImportError:
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
        except (OSError, yaml.YAMLError) as exc:
            print(f"  ✗ {p}: invalid YAML: {exc}")
            total += 1
            continue
        errs = _errors(validator, data, p)
        errs += _check_lens_refs(data if isinstance(data, dict) else {}, p)
        total += errs
        if errs == 0:
            print(f"  {_ok('✓')} {p}")
    if total:
        _die(f"{total} config problem(s)", 1)
    print(_ok("OK: config valid."))
    return 0


_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*-[0-9]{3,}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")   # scope_hash / bundle_hash
_COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")  # commit_sha (short or full)


def _report_threshold(config_path) -> float:
    if not config_path:
        return 6.0
    try:
        import yaml
    except ImportError:
        return 6.0
    try:
        p = Path(config_path)
        if p.exists():
            cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            return float((cfg.get("severity_policy") or {}).get("low_score_threshold", 6.0))
    except (OSError, ValueError, TypeError, yaml.YAMLError):
        pass  # unreadable / malformed config → default threshold
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
        # provenance: a 'verified' finding should carry a verification record
        # (who re-checked it, how). Warn now; slated to become an error (issue #2).
        if f.get("status") == "verified":
            v = f.get("verification") or {}
            if not (v.get("verified_by") and v.get("method")):
                warns.append(f"{f.get('id')}: status 'verified' but no verification record "
                             "(verified_by + method) — provenance incomplete")
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
    # provenance: bind report ↔ bundle ↔ commit (issue #2). Optional today —
    # warn when a report with findings omits it (ahead of a later release that
    # requires it), and flag a malformed hash if the block is present. Integrity
    # only; the CLI still never decides whether a finding is real.
    prov = data.get("provenance")
    if not prov:
        if findings:
            warns.append("no 'provenance' block — a report with findings should carry "
                         "commit_sha + bundle_hash from the bundle it was built from "
                         "(`invairiant collect` emits them) so it binds to its commit")
    else:
        for key, rx in (("bundle_hash", _SHA256_RE), ("scope_hash", _SHA256_RE),
                        ("commit_sha", _COMMIT_RE)):
            val = prov.get(key)
            if val is not None and not rx.match(str(val)):
                errs.append(f"provenance.{key} is not a valid hash ('{str(val)[:24]}…')")
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
                except (json.JSONDecodeError, AttributeError):
                    pass
        for f in findings:
            if _claim_key(f.get("claim", "")) in rejected:
                warns.append(f"{f.get('id')}: claim matches a previously-rejected hypothesis in audit memory — re-verify before shipping")
    return errs, warns


def _file_at(path: str, commit: str | None):
    """The text of `path` at `commit` (git), or the working tree if commit is
    None. Returns None when the file does not exist there."""
    if commit:
        rc, out, _ = _run(["git", "show", f"{commit}:{path}"])
        return out if rc == 0 else None
    p = Path(path)
    if not p.is_file():
        return None
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None


def _citation_errors(data: dict, commit: str | None = None):
    """Opt-in mechanical check (issue #2): every `file_lines` citation points at a
    real file whose cited line range actually exists. Judgment-free — it confirms
    "the cited location is real", NOT that the evidence supports the claim (that
    is the skill's job). Resolves each citation at its own `commit`, else the
    given `commit`, else the working tree. Returns a list of error strings."""
    errs = []
    for f in data.get("findings", []):
        fid = f.get("id", "?")
        for e in f.get("evidence", []):
            if e.get("type") != "file_lines":
                continue   # only file+line citations are location-checkable
            path = e.get("file")
            if not path:
                errs.append(f"{fid}: file_lines evidence has no 'file' to check")
                continue
            at = e.get("commit") or commit
            whereat = f" at {at[:12]}" if at else ""
            content = _file_at(path, at)
            if content is None:
                errs.append(f"{fid}: cited file '{path}'{whereat} does not exist")
                continue
            rng = e.get("lines")
            if rng:
                nums = [int(x) for x in rng.split("-")]
                lo, hi = min(nums), max(nums)
                total = len(content.splitlines())
                if lo < 1 or hi > total:
                    errs.append(f"{fid}: cited lines {rng} out of range in "
                                f"'{path}'{whereat} ({total} line(s))")
    return errs


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
        except json.JSONDecodeError as exc:
            print(f"  ✗ {p}: invalid JSON: {exc}")
            total += 1
            continue
        errs = _errors(validator, data, p)
        if not args.schema_only:
            serrs, warns = _semantic_report_errors(data, threshold)
            for w in warns:
                print(f"  {_warn('⚠')} {p}: {w}")
            for e in serrs:
                print(f"  {_bad('✗')} {p}: {e}")
            errs += len(serrs)
        if getattr(args, "check_citations", False):
            cerrs = _citation_errors(data, getattr(args, "commit", None))
            for e in cerrs:
                print(f"  {_bad('✗')} {p}: {e}")
            errs += len(cerrs)
        total += errs
        if errs == 0:
            print(f"  {_ok('✓')} {p}")
    if total:
        _die(f"{total} report problem(s)", 1)
    suffix = "" if args.md or args.schema_only else " (schema + semantic)"
    if getattr(args, "check_citations", False):
        suffix += " + citations"
    print(_ok("OK: report valid.") + suffix)
    return 0


# --------------------------------------------------------------------------- #
# ci-gate  (the seatbelt: fail on open S0/S1)
# --------------------------------------------------------------------------- #
def cmd_ci_gate(args) -> int:
    p = args.report
    path = Path(p)
    if not path.exists():
        _die(f"report not found: {p}", 3)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _die(f"{p}: could not read/parse report: {exc}", 3)
    # Self-contained contract: parse → schema validate → semantic validate → gate.
    # Do not assume `validate-report` ran first; refuse to gate an invalid report.
    errs = _errors(_validator("audit-report"), data, p)
    serrs, warns = _semantic_report_errors(data, _report_threshold(getattr(args, "config", None)))
    for w in warns:
        print(f"  {_warn('⚠')} {p}: {w}")
    for e in serrs:
        print(f"  {_bad('✗')} {p}: {e}")
    errs += len(serrs)
    if errs:
        _die(f"{p}: {errs} report problem(s) — refusing to gate an invalid report", 3)
    blocked = {"S0"} if args.max_severity == "S0" else {"S0", "S1"}
    open_blocking = [
        f for f in data.get("findings", [])
        if f.get("severity") in blocked and f.get("status") != "rejected"
    ]
    verdict = data.get("summary", {}).get("verdict")
    vc = _bad(verdict) if verdict == "fail" else _ok(verdict) if verdict == "pass" else _warn(str(verdict))
    print(_dim(f"ci-gate: blocking {sorted(blocked)}; verdict: ") + vc)
    if open_blocking:
        print(_c("1;31", f"FAILED: {len(open_blocking)} open blocking finding(s):"))
        for f in open_blocking:
            print(f"  {_bad('✗')} {f.get('id','?')} [{_sev(f.get('severity'))}] {f.get('claim','')[:90]}")
        return 1
    print(_ok("OK: no open S0/S1 findings."))
    return 0
