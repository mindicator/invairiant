"""Scope resolvers: turn a bounded scope (kind + target) into a file set,
failing closed rather than silently widening to a whole-repo search.

The CLI serves the invAIriant audit; it never runs a lens, invents a
finding, or assigns a score.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from .models import ResolvedScope, ScopeKind
from .subprocesses import _MAX_FILE_BYTES, _is_probably_binary, _ls_files, _run

# A scope resolver turns a bounded scope (kind + target) into a file set, so
# `collect` computes the whole bundle OVER that set — bounded, never a general
# repo search. Only the `repo` scope is (explicitly) unbounded.
#
# An ADR scope resolves to the code its text references. That must stay a
# *bounded decision area*, not the whole repo wearing an ADR hat — so we fail
# closed (require --narrow) when it resolves "too broadly". "Too broad" is
# relative to repo size (a share of tracked files), with a floor so small repos
# aren't over-constrained and an absolute ceiling for very large ones.
_ADR_MAX_SCOPE_FILES = 200   # absolute ceiling (large repos)


_ADR_BROAD_FRACTION = 0.4    # more than this share of tracked files = too broad


_ADR_BROAD_FLOOR = 40        # but always allow at least this many (small repos)


def _adr_broad_limit(total_tracked: int) -> int:
    """Max files an ADR may resolve to before it must be narrowed."""
    return min(_ADR_MAX_SCOPE_FILES,
               max(_ADR_BROAD_FLOOR, int(_ADR_BROAD_FRACTION * total_tracked)))


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


def _remote_name() -> str:
    """The remote a PR resolver may reach. Fail closed if there is none."""
    _, out, _ = _run(["git", "remote"])
    remotes = [r for r in out.split() if r]
    if not remotes:
        raise ScopeError("no git remote configured; a PR cannot be resolved — "
                         "pass --range <base>...<head> instead")
    return "origin" if "origin" in remotes else remotes[0]


def _default_base_ref(remote: str):
    """The remote's default branch ref (e.g. origin/main), or None."""
    rc, out, _ = _run(["git", "rev-parse", "--abbrev-ref", f"{remote}/HEAD"])
    if rc == 0 and "/" in out.strip():
        return out.strip()
    for cand in (f"{remote}/main", f"{remote}/master"):
        if _run(["git", "rev-parse", "--verify", "--quiet", cand])[0] == 0:
            return cand
    return None


def _resolve_pr(args) -> ResolvedScope:
    """Optional PR resolver ADAPTER. Core scopes are pure-local; ONLY --scope pr
    may reach the remote (gh, or the pull/<n>/head ref). A PR resolves to an
    ordinary bounded base...head range — the same shape as --scope range. If it
    cannot be resolved, fail closed and suggest --range; never scan the whole
    repo."""
    raw = getattr(args, "pr", None)
    if not raw:
        raise ScopeError("--scope pr requires --pr <number>")
    num = str(raw).lstrip("#").strip()
    if not num.isdigit():
        raise ScopeError(f"--pr expects a PR number, got '{raw}'")

    remote = _remote_name()
    base_name = head_name = head_oid = None
    resolver = "git"

    # 1) gh, if present: the reliable source of the PR's base/head.
    if shutil.which("gh"):
        rc, out, _ = _run(["gh", "pr", "view", num, "--json",
                           "baseRefName,headRefName,headRefOid"])
        if rc == 0:
            try:
                meta = json.loads(out)
                base_name = meta.get("baseRefName") or None
                head_name = meta.get("headRefName") or None
                head_oid = meta.get("headRefOid") or None
                resolver = "gh"
            except (json.JSONDecodeError, AttributeError, TypeError):
                pass

    # 2) Head object: reuse it if already local (checked-out PR → no network);
    #    otherwise fetch the pull ref.
    if head_oid and _run(["git", "cat-file", "-e", f"{head_oid}^{{commit}}"])[0] == 0:
        head_sha = head_oid
    else:
        rc, _, err = _run(["git", "fetch", "--quiet", remote, f"pull/{num}/head"])
        if rc != 0:
            raise ScopeError(
                f"could not fetch PR #{num} from '{remote}' "
                f"({(err or '').strip()[:100]}); the remote may not be GitHub or "
                "is unreachable — pass --range <base>...<head> instead")
        head_sha = _run(["git", "rev-parse", "FETCH_HEAD"])[1].strip()
    if not head_sha:
        raise ScopeError(f"PR #{num} head did not resolve — pass --range instead")

    # 3) Base ref (must be local to diff against): gh's base branch, else the
    #    remote default branch; fetch it if missing.
    base_ref = f"{remote}/{base_name}" if base_name else _default_base_ref(remote)
    if not base_ref or _run(["git", "rev-parse", "--verify", "--quiet", base_ref])[0] != 0:
        if base_name:
            _run(["git", "fetch", "--quiet", remote, base_name])
        if not base_ref or _run(["git", "rev-parse", "--verify", "--quiet", base_ref])[0] != 0:
            raise ScopeError(
                f"could not resolve the base branch for PR #{num} — pass "
                "--range <base>...<head> instead")

    # 4) PR is now an ordinary bounded range.
    rng = f"{base_ref}...{head_sha}"
    rc, names, err = _run(["git", "diff", "--name-only", rng])
    if rc != 0:
        raise ScopeError(f"PR #{num} range '{rng}' did not resolve "
                         f"({(err or '').strip()[:100]}) — pass --range instead")
    files = [f for f in names.splitlines() if f.strip()]
    _, diff, _ = _run(["git", "diff", rng])

    head_disp = head_name or head_sha[:12]
    # Content-level signals are read from the working tree; if the PR head isn't
    # what's checked out, they'll be sparse (the diff/files/mass stay correct
    # from git). Flag it so collect can warn.
    cur = _run(["git", "rev-parse", "HEAD"])[1].strip()
    head_checked_out = bool(cur) and cur == head_sha
    return ResolvedScope(
        kind=ScopeKind.pr, target=num, files=tuple(files), bounded=True,
        diff=diff or None, range=rng, base=base_ref, head=head_disp,
        resolver=resolver, head_checked_out=head_checked_out,
        note=f"PR #{num} ({base_ref}...{head_disp}) via {resolver} "
             f"({len(files)} file(s))")


def _resolve_scope(args) -> ResolvedScope:
    """Deterministically bound the audit scope. Raises ScopeError (fail closed)
    when a scope cannot be bounded."""
    kind = getattr(args, "scope", None) or ("range" if args.range else "working")

    if kind == "pr":
        return _resolve_pr(args)

    if kind == "working":
        _, names, _ = _run(["git", "status", "--porcelain"])
        files = [l[3:] for l in names.splitlines() if l.strip()]
        _, diff, _ = _run(["git", "diff"])
        return ResolvedScope(kind=ScopeKind.working, target="working tree",
                             files=tuple(files), diff=diff or None, bounded=True,
                             note="uncommitted working-tree changes")

    if kind == "range":
        rng = args.range
        if not rng:
            raise ScopeError("--scope range requires --range A..B")
        rc, names, err = _run(["git", "diff", "--name-only", rng])
        if rc != 0:
            raise ScopeError(f"range '{rng}' did not resolve ({err.strip()[:120]})")
        files = [f for f in names.splitlines() if f.strip()]
        _, diff, _ = _run(["git", "diff", rng])
        return ResolvedScope(kind=ScopeKind.range, target=rng, files=tuple(files),
                             diff=diff or None, bounded=True,
                             note=f"files changed in {rng}")

    if kind == "commit":
        sha = args.commit
        if not sha:
            raise ScopeError("--scope commit requires --commit <sha>")
        rc, names, err = _run(["git", "show", "--name-only", "--format=", sha])
        if rc != 0:
            raise ScopeError(f"commit '{sha}' did not resolve ({err.strip()[:120]})")
        files = [f for f in names.splitlines() if f.strip()]
        _, diff, _ = _run(["git", "show", sha])
        return ResolvedScope(kind=ScopeKind.commit, target=sha, files=tuple(files),
                             diff=diff or None, bounded=True,
                             note=f"files in commit {sha[:12]}")

    if kind == "module":
        path = args.path
        if not path:
            raise ScopeError("--scope module requires --path <dir-or-file>")
        if not Path(path).exists():
            raise ScopeError(f"module path '{path}' does not exist")
        files = _ls_files(path)
        if not files:
            raise ScopeError(f"module path '{path}' has no tracked files")
        return ResolvedScope(kind=ScopeKind.module, target=path, files=tuple(files),
                             bounded=True, snapshot=True,
                             note=f"tracked files under {path} (snapshot)")

    if kind in ("adr", "rp"):
        # A doc-vs-code scope: a decision/proposal document plus the tracked code
        # it references. Same bounding + fail-closed machinery for both; only the
        # framing differs — an ADR is a *made* decision (audit for drift: does the
        # code match?), an RP is a *proposed* change (audit for risk: would
        # applying it break invariants?). The referenced code is a snapshot.
        label = "ADR" if kind == "adr" else "refactoring proposal"
        pin = "the decision area" if kind == "adr" else "the refactor's blast radius"
        src = args.path
        if not src or not Path(src).is_file():
            noun = "adr" if kind == "adr" else "proposal"
            raise ScopeError(f"--scope {kind} requires --path <{noun}-file>")
        text = Path(src).read_text(encoding="utf-8", errors="ignore")
        docs = [{"path": src, "excerpt": text[:8000]}]
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
                if not p.is_file() or str(p) == src:
                    continue
                try:
                    if p.stat().st_size > _MAX_FILE_BYTES or _is_probably_binary(p):
                        continue
                    if idre.search(p.read_text(encoding="utf-8", errors="ignore")):
                        refs.add(f)
                except OSError:
                    continue
        narrow = getattr(args, "narrow", None)
        if narrow:
            pfx = narrow.rstrip("/") + "/"
            refs = {f for f in refs if f == narrow or f.startswith(pfx)}
        files = sorted(refs)
        if not files:
            raise ScopeError(
                f"{label} references did not resolve to tracked code"
                + (f" under --narrow '{narrow}'" if narrow else "; re-run with --narrow <path>"))
        broad_limit = _adr_broad_limit(len(tracked))
        if not narrow and len(files) > broad_limit:
            raise ScopeError(
                f"{label} references resolved too broadly ({len(files)} of {len(tracked)} "
                f"tracked files, over the {broad_limit}-file bound); re-run with "
                f"--narrow <path> to pin {pin}")
        return ResolvedScope(
            kind=ScopeKind(kind), target=src, files=tuple(files), docs=tuple(docs),
            bounded=True, snapshot=True,
            note=f"{label} + the code it references ({len(files)} files)"
                 + (f", narrowed to {narrow}" if narrow else ""))

    if kind == "repo":
        return ResolvedScope(kind=ScopeKind.repo, target="whole repo",
                             files=tuple(_ls_files()), bounded=False,
                             note="explicitly unbounded (full-audit scope)")

    raise ScopeError(f"unknown scope '{kind}'")


def _scope_detail(scope: ResolvedScope) -> dict:
    """The change detail (name-status + diffstat) for change scopes; a snapshot
    summary otherwise."""
    kind, target = scope.kind, scope.target
    if kind == "commit":
        _, ns, _ = _run(["git", "show", "--name-status", "--format=", target])
        _, st, _ = _run(["git", "show", "--stat", "--format=", target])
        changed = [{"status": l.split("\t")[0], "file": l.split("\t")[-1]}
                   for l in ns.splitlines() if "\t" in l]
    elif kind in ("range", "pr"):
        rng = scope.range or target   # pr's target is a number; use its range
        _, ns, _ = _run(["git", "diff", "--name-status", rng])
        _, st, _ = _run(["git", "diff", "--stat", rng])
        changed = [{"status": l.split("\t")[0], "file": l.split("\t")[-1]}
                   for l in ns.splitlines() if l.strip()]
    elif kind == "working":
        _, ns, _ = _run(["git", "status", "--porcelain"])
        _, st, _ = _run(["git", "diff", "--stat"])
        changed = [{"status": l[:2].strip(), "file": l[3:]}
                   for l in ns.splitlines() if l.strip()]
    else:  # module / adr / rp / repo — a snapshot, not a change
        return {"kind": kind.value, "target": target, "snapshot": True,
                "changed_files": [], "diffstat": ""}
    return {"kind": kind.value, "target": target, "changed_files": changed,
            "diffstat": st.strip()[:4000]}
