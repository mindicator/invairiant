"""invAIriant helper CLI — package facade.

The CLI serves the invAIriant audit protocol; it does not audit (no lenses, no
findings, no scores). `main` is the only public entry point (wired in pyproject
`[project.scripts]` and reachable via `python -m invairiant`).

Everything else re-exported below is the module's internal surface that the
white-box unit tests exercise directly (see tests/). It is grouped by home
submodule so the split stays legible, and is deliberately kept out of `__all__`.
"""
from __future__ import annotations

from .cli import main, cmd_init
from .models import ScopeKind, ResolvedScope
from .schemas import (
    framework_root, known_lens_ids, _need, _validator, _errors, _check_lens_refs,
    _report_threshold, _semantic_report_errors, _md_report_errors, _citation_errors,
    cmd_validate_config, cmd_validate_report, cmd_ci_gate,
)
from .subprocesses import _repo_root, _is_probably_binary, _ls_files, _run, _git
from .history import _sanitize, _claim_key, _history_dir, cmd_record, cmd_history
from .scopes import (
    ScopeError, _resolve_scope, _scope_detail, _adr_broad_limit,
    _ADR_BROAD_FLOOR, _ADR_MAX_SCOPE_FILES, _extract_adr_refs,
)
from .evidence import (
    _sha256, _scan, _new_budget, _SIGNAL_PATTERNS,
    cmd_collect, cmd_collect_evidence,
)
from .render import cmd_render_report, cmd_render_comment

__all__ = ["main"]
