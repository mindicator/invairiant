"""v0.2 scope resolvers: bounded scopes, fail-closed, resolved_scope, scoped scanning."""

from __future__ import annotations

import argparse
import json
import subprocess

import pytest


def _ns(**kw):
    d = dict(scope=None, range=None, commit=None, path=None, narrow=None)
    d.update(kw)
    return argparse.Namespace(**d)


class TestResolvers:
    def test_working_is_default(self, cli):
        s = cli._resolve_scope(_ns())
        assert s["kind"] == "working" and s["bounded"] is True

    def test_range_inferred_from_flag(self, cli):
        s = cli._resolve_scope(_ns(range="HEAD~1..HEAD"))
        assert s["kind"] == "range" and s["bounded"] and len(s["files"]) >= 1 and s["diff"]

    def test_commit(self, cli):
        s = cli._resolve_scope(_ns(scope="commit", commit="HEAD"))
        assert s["kind"] == "commit" and s["diff"] and len(s["files"]) >= 1

    def test_module_is_bounded_snapshot(self, cli):
        s = cli._resolve_scope(_ns(scope="module", path="cli"))
        assert s["kind"] == "module" and s["diff"] is None and s["files"]
        assert all(f.startswith("cli/") for f in s["files"])

    def test_repo_is_explicitly_unbounded(self, cli):
        s = cli._resolve_scope(_ns(scope="repo"))
        assert s["kind"] == "repo" and s["bounded"] is False and len(s["files"]) > 10


class TestFailClosed:
    def test_range_without_range(self, cli):
        with pytest.raises(cli.ScopeError):
            cli._resolve_scope(_ns(scope="range"))

    def test_module_missing_path(self, cli):
        with pytest.raises(cli.ScopeError):
            cli._resolve_scope(_ns(scope="module", path="does/not/exist"))

    def test_commit_bad_sha(self, cli):
        with pytest.raises(cli.ScopeError):
            cli._resolve_scope(_ns(scope="commit", commit="deadbeefbad00000"))

    def test_adr_not_a_file(self, cli):
        with pytest.raises(cli.ScopeError):
            cli._resolve_scope(_ns(scope="adr", path="nope-not-here.md"))


class TestADR:
    def test_resolves_referenced_path_and_identifier(self, cli, tmp_path):
        adr = tmp_path / "adr.md"
        adr.write_text("ADR: the resolver lives in `cli/invairiant.py` via `_resolve_scope`.")
        s = cli._resolve_scope(_ns(scope="adr", path=str(adr)))
        assert s["kind"] == "adr" and "cli/invairiant.py" in s["files"]
        assert s["docs"] and s["docs"][0]["path"] == str(adr)

    def test_narrow_restricts_scope(self, cli, tmp_path):
        adr = tmp_path / "adr.md"
        adr.write_text("references `cli/invairiant.py` and `README.md`")
        s = cli._resolve_scope(_ns(scope="adr", path=str(adr), narrow="cli"))
        assert s["files"] and all(f.startswith("cli/") for f in s["files"])

    def test_no_references_fails_closed(self, cli, tmp_path):
        adr = tmp_path / "adr.md"
        adr.write_text("This ADR is only prose and mentions no tracked code at all.")
        with pytest.raises(cli.ScopeError):
            cli._resolve_scope(_ns(scope="adr", path=str(adr)))


class TestScopedScanE2E:
    def test_module_bundle_is_bounded(self, cli_path, repo_root, tmp_path):
        out = tmp_path / "b.json"
        subprocess.run(["python3", str(cli_path), "collect", "--scope", "module",
                        "--path", "cli", "--out", str(out)],
                       cwd=repo_root, check=True, capture_output=True)
        d = json.loads(out.read_text(encoding="utf-8"))
        rs = d["resolved_scope"]
        assert rs["kind"] == "module" and rs["bounded"] is True and rs["files_in_scope"] >= 1
        sigfiles = {it["file"] for cat in d["signals"].values() for it in cat}
        assert all(f.startswith("cli/") for f in sigfiles)   # scoped, not whole-repo
        assert [e["entry"] for e in d["repo_tree"]] == ["cli"]

    def test_collect_fails_closed_with_exit_2(self, cli_path, repo_root):
        r = subprocess.run(["python3", str(cli_path), "collect", "--scope", "module",
                            "--path", "does/not/exist"], cwd=repo_root, capture_output=True)
        assert r.returncode == 2 and b"could not be bounded" in r.stderr
