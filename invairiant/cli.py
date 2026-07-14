"""Argument parsing and command dispatch. `init` plus the wiring that maps
each subcommand to its handler in the sibling modules.

The CLI serves the invAIriant audit; it never runs a lens, invents a
finding, or assigns a score.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from .evidence import cmd_collect, cmd_collect_evidence, cmd_verify_provenance
from .history import cmd_history, cmd_record
from .render import cmd_render_comment, cmd_render_report
from .schemas import EXAMPLES, cmd_ci_gate, cmd_validate_config, cmd_validate_report
from .term import _die

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
    pr.add_argument("--strict", action="store_true",
                    help="promote the provenance-completeness nudges to errors: a `verified` finding "
                         "must carry a verification record, and a report with findings must carry a "
                         "provenance block (issue #2, staged rollout)")
    pr.add_argument("--check-citations", action="store_true",
                    help="opt-in: verify each file_lines citation points at a real file + line range "
                         "(working tree, or --commit)")
    pr.add_argument("--commit", default=None,
                    help="resolve --check-citations paths at this commit instead of the working tree")
    pr.set_defaults(func=cmd_validate_report)

    pcol = sub.add_parser("collect", help="gather a deterministic, scope-bounded evidence bundle for the skill")
    pcol.add_argument("--scope", choices=["working", "range", "commit", "module", "adr", "rp", "pr", "repo"],
                      default=None, help="bounded audit scope (default: range if --range given, else working)")
    pcol.add_argument("--range", default=None, help="git range A..B (for --scope range)")
    pcol.add_argument("--commit", default=None, help="commit sha (for --scope commit)")
    pcol.add_argument("--pr", default=None, help="pull-request number (for --scope pr; resolves via gh or the pull/<n>/head ref)")
    pcol.add_argument("--path", default=None,
                      help="module dir/file (--scope module), ADR file (--scope adr), or "
                           "refactoring-proposal file (--scope rp)")
    pcol.add_argument("--narrow", default=None, help="restrict an adr/rp scope's code to this subtree")
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

    pvp = sub.add_parser("verify-provenance",
                         help="prove a report binds to its commit (and, with --bundle, its evidence bundle)")
    pvp.add_argument("report")
    pvp.add_argument("--bundle", default=None,
                     help="evidence bundle (from `collect`) to compare the report's provenance against")
    pvp.add_argument("--commit", default=None,
                     help="the audited commit to bind to (default: git HEAD)")
    pvp.add_argument("--require", action="store_true",
                     help="fail if the report carries no provenance block (default: warn)")
    pvp.add_argument("--require-exact-bundle", action="store_true",
                     help="with --bundle: fail (not warn) if the report's scope_hash/bundle_hash "
                          "differ from the bundle's — proves it came from THIS exact bundle "
                          "(needs deterministic collect in both places)")
    pvp.set_defaults(func=cmd_verify_provenance)

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
    pg.add_argument("--config", default=None, help="config for the low-score threshold (optional)")
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
