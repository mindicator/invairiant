"""Typed scope models: the vocabulary the resolvers speak and the collector
consumes. A frozen dataclass instead of a bare dict so a resolved scope can't be
mutated downstream and a field-name typo (`scope.head_cheked_out`) fails loudly
at attribute access instead of silently reading `None` from a dict.

The CLI serves the invAIriant audit; it never runs a lens, invents a finding,
or assigns a score.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ScopeKind(str, Enum):
    """The eight audit scopes `collect` can resolve to. `str`-valued so it still
    compares to and JSON-serializes as the plain kind string ("adr", "repo", …),
    keeping the bundle output identical while making the set of kinds explicit."""
    working = "working"
    range = "range"
    commit = "commit"
    module = "module"
    adr = "adr"
    rp = "rp"
    pr = "pr"
    repo = "repo"


@dataclass(frozen=True)
class ResolvedScope:
    """A bounded audit scope — the resolvers' single, typed return value.

    Change scopes (working/range/commit/pr) carry a `diff`; snapshot scopes
    (module/adr/rp/repo) do not. The `pr` scope additionally records how it was
    pinned (`base`/`head`/`resolver`/`head_checked_out`). Only `repo` is
    unbounded; every other kind is bounded or the resolver raises ScopeError.
    """
    kind: ScopeKind
    target: str
    files: tuple[str, ...]
    bounded: bool
    note: str = ""
    diff: str | None = None
    docs: tuple[dict, ...] = ()
    snapshot: bool = False
    # pr scope only — how the PR was pinned:
    range: str | None = None
    base: str | None = None
    head: str | None = None
    resolver: str | None = None
    head_checked_out: bool | None = None

    @property
    def has_diff(self) -> bool:
        return self.diff is not None

    def resolved_block(self) -> dict:
        """The `resolved_scope` block for the evidence bundle — exactly the
        fields (and order) `collect` records, with `kind` as its plain string
        value so the serialized bundle is byte-for-byte what it always was."""
        block = {
            "kind": self.kind.value,
            "target": self.target,
            "bounded": self.bounded,
            "files_in_scope": len(self.files),
            "sample_files": list(self.files[:25]),
            "has_diff": self.has_diff,
            "docs": [d.get("path") for d in self.docs],
            "note": self.note,
        }
        # PR scope records how it was pinned; other scopes omit these keys.
        for k in ("base", "head", "resolver", "head_checked_out"):
            v = getattr(self, k)
            if v is not None:
                block[k] = v
        return block
