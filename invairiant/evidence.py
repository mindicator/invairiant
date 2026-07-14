"""The deterministic evidence bundle: `collect` and its signal scans plus
the provenance hash. Everything here is a candidate pointer, not a finding.

The CLI serves the invAIriant audit; it never runs a lens, invents a
finding, or assigns a score.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .history import _history_dir
from .models import ResolvedScope
from .schemas import _COMMIT_RE, _SHA256_RE, _need
from .scopes import ScopeError, _resolve_scope, _scope_detail
from .subprocesses import (_MAX_FILE_BYTES, _MAX_SCAN_FILES, _git,
                           _is_probably_binary, _ls_files, _run)
from .term import _bad, _c, _die, _dim, _ok, _warn

def _sha256(obj) -> str:
    """Stable sha256 over a JSON-serializable value (sorted keys, no whitespace)."""
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _recompute_bundle_hash(bundle: dict) -> str:
    """The bundle_hash `collect` would have written: sha256 over the bundle with
    provenance.bundle_hash removed. Recompute it to prove the bundle wasn't edited."""
    b = copy.deepcopy(bundle)
    if isinstance(b.get("provenance"), dict):
        b["provenance"].pop("bundle_hash", None)
    return _sha256(b)


def _sha_matches(a: str, b: str) -> bool:
    """True if two commit shas name the same commit (prefix match, min 7 chars),
    so a short sha in the report matches a full sha from git."""
    a, b = str(a).lower(), str(b).lower()
    n = min(len(a), len(b))
    return n >= 7 and a[:n] == b[:n]


def _provenance_check(report: dict, commit=None, bundle=None, require=False,
                      require_exact_bundle=False):
    """Mechanical provenance verification (issue #2): does the report bind to the
    commit — and, if a bundle is given, to that bundle — it claims to be built
    from? Judgment-free: hashing and equality only, never whether a finding is
    real. Returns (errors, warnings).

    Hard checks (portable, deterministic) are errors; content-level cross-machine
    signals (scope_hash / bundle_hash mismatch vs a freshly-collected bundle) are
    warnings by default, so the gate does not flake across environments.
    `require_exact_bundle` promotes those two to errors — for when `collect` runs
    identically in both places and you want to *prove* the report came from this
    exact bundle, not merely from some bundle at the same commit."""
    errs, warns = [], []
    prov = report.get("provenance")
    if not prov:
        msg = "report has no 'provenance' block — cannot bind it to a commit or bundle"
        (errs if require else warns).append(msg)
        return errs, warns
    for key, rx in (("bundle_hash", _SHA256_RE), ("scope_hash", _SHA256_RE),
                    ("commit_sha", _COMMIT_RE)):
        v = prov.get(key)
        if v is not None and not rx.match(str(v)):
            errs.append(f"provenance.{key} is not a valid hash")
    # 1) commit binding (portable, hard): the report must name the audited commit.
    if commit:
        rc = prov.get("commit_sha")
        if not rc:
            (errs if require else warns).append(
                "provenance has no commit_sha to bind to the audited commit")
        elif not _sha_matches(rc, commit):
            errs.append(f"report was built for commit {str(rc)[:12]} but the audited "
                        f"commit is {str(commit)[:12]}")
    # 2) bundle binding: compare against a (freshly-collected) evidence bundle.
    if bundle is not None:
        bp = bundle.get("provenance") or {}
        if bp.get("bundle_hash") and _recompute_bundle_hash(bundle) != bp["bundle_hash"]:
            errs.append("evidence bundle is corrupt or was edited "
                        "(its bundle_hash does not recompute)")
        if prov.get("commit_sha") and bp.get("commit_sha") and \
                not _sha_matches(prov["commit_sha"], bp["commit_sha"]):
            errs.append("report.commit_sha does not match the bundle's commit_sha")
        sink = errs if require_exact_bundle else warns
        if prov.get("scope_hash") and bp.get("scope_hash") and \
                prov["scope_hash"] != bp["scope_hash"]:
            sink.append("report.scope_hash differs from the bundle's — the report may "
                        "cover a different scope than this bundle")
        if prov.get("bundle_hash") and bp.get("bundle_hash") and \
                prov["bundle_hash"] != bp["bundle_hash"]:
            sink.append("report.bundle_hash differs from this bundle's — the report was "
                        "built from a different bundle (expected only if collect ran in a "
                        "different layout)")
    return errs, warns


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
        except OSError:
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
        except OSError:
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


def _generated_mass(scope: ResolvedScope) -> dict:
    kind, target = scope.kind, scope.target
    if kind == "commit":
        num = _run(["git", "show", "--numstat", "--format=", target])[1]
        short = _run(["git", "show", "--shortstat", "--format=", target])[1]
    elif kind in ("range", "pr"):
        rng = scope.range or target   # pr's target is a number; use its range
        num = _run(["git", "diff", "--numstat", rng])[1]
        short = _run(["git", "diff", "--shortstat", rng])[1]
    elif kind == "working":
        num = _run(["git", "diff", "--numstat"])[1]
        short = _run(["git", "diff", "--shortstat"])[1]
    else:  # module / adr / rp / repo — a snapshot: report the size of the file set
        sized, total = [], 0
        for f in scope.files:
            p = Path(f)
            try:
                n = sum(1 for _ in p.open("rb")) if (p.is_file() and p.stat().st_size <= _MAX_FILE_BYTES) else 0
            except OSError:
                n = 0
            total += n
            sized.append({"file": f, "lines": n})
        sized.sort(key=lambda x: -x["lines"])
        return {"snapshot": True, "files": len(scope.files),
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
    except ImportError:
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
            except json.JSONDecodeError:
                pass
    return out


def cmd_collect(args) -> int:
    # Bound the scope first — FAIL CLOSED rather than silently scan the whole repo.
    try:
        scope = _resolve_scope(args)
    except ScopeError as exc:
        print(f"collect: scope could not be bounded — {exc}", file=sys.stderr)
        return 2
    scan_files = None if scope.kind == "repo" else list(scope.files)

    if scope.kind == "pr" and not scope.head_checked_out:
        print(f"note: PR #{scope.target} head ({scope.head}) is not checked "
              f"out — content signals read the working tree and will be sparse. Run "
              f"`gh pr checkout {scope.target}` (or audit in CI, where the PR head "
              "is the checkout) for full grep fidelity; the diff, file set, and mass "
              "are correct from git regardless.", file=sys.stderr)

    cfg, docs = _config_and_docs()
    docs = list(docs) + list(scope.docs)   # ADR / proposal text joins canonical docs
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

    resolved_scope = scope.resolved_block()
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
            "scope": scope.kind.value,
            "target": scope.target,
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
    # provenance — bind this bundle to its commit + resolved scope. Structure
    # only (the CLI still never judges truth); it lets a later report/Action
    # prove it was built from THIS bundle at THIS commit. bundle_hash covers the
    # whole bundle incl. commit_sha + scope_hash; recompute it over the bundle
    # minus provenance.bundle_hash to verify.
    bundle["provenance"] = {
        "commit_sha": git_info["head"],
        "scope_hash": _sha256({"kind": scope.kind.value, "target": scope.target,
                               "files": sorted(scope.files)}),
        "generated_by": "invairiant collect",
    }
    bundle["provenance"]["bundle_hash"] = _sha256(bundle)
    payload = json.dumps(bundle, indent=2, ensure_ascii=False)
    unb = "" if scope.bounded else ", UNBOUNDED"
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(payload + "\n", encoding="utf-8")
        n = sum(len(v) for v in bundle["signals"].values())
        print(f"wrote evidence bundle to {args.out} — scope={_c('1;36', scope.kind.value)} "
              f"({resolved_scope['files_in_scope']} file(s){unb}); {n} candidate "
              f"signal(s); {_dim('raw — keep it gitignored')}")
    else:
        print(payload)
    return 0


def _load_json(path: str, label: str):
    p = Path(path)
    if not p.exists():
        _die(f"{label} not found: {path}", 3)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        _die(f"{path}: could not read/parse {label}: {exc}", 3)


def cmd_verify_provenance(args) -> int:
    """Prove a report is bound to its commit — and, with --bundle, to the evidence
    bundle it was built from. Mechanical integrity only; the CLI never judges a
    finding. The report half of report↔bundle↔commit (issue #2)."""
    exact = getattr(args, "require_exact_bundle", False)
    if exact and not args.bundle:
        _die("--require-exact-bundle needs --bundle to compare against", 3)
    report = _load_json(args.report, "report")
    bundle = _load_json(args.bundle, "bundle") if args.bundle else None
    commit = args.commit
    if commit is None:                       # default: bind to git HEAD when in a repo
        commit = _git(["rev-parse", "HEAD"]) or None
    errs, warns = _provenance_check(report, commit=commit, bundle=bundle,
                                    require=args.require, require_exact_bundle=exact)
    for w in warns:
        print(f"  {_warn('⚠')} {w}")
    for e in errs:
        print(f"  {_bad('✗')} {e}")
    if errs:
        _die(f"{len(errs)} provenance problem(s)", 1)
    bound = "commit" + ("+bundle" if bundle else "")
    print(_ok("OK: provenance verified.") + _dim(f" ({bound})"))
    return 0
