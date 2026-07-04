"""v0.2 scope resolvers: bounded scopes, fail-closed, resolved_scope, scoped scanning."""

from __future__ import annotations

import argparse
import json
import subprocess

import pytest


def _ns(**kw):
    d = dict(scope=None, range=None, commit=None, path=None, narrow=None, pr=None)
    d.update(kw)
    return argparse.Namespace(**d)


def _init_pr_repo(tmp_path):
    """A bare 'remote' carrying main + refs/pull/1/head, plus a consumer clone
    that does NOT have the PR head locally — so _resolve_pr must fetch the pull
    ref. Exercises the PR resolver's git path with no gh/network. Returns the
    consumer repo path (feature.txt is added only on the PR head)."""
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    consumer = tmp_path / "consumer"

    def g(cwd, *a):
        subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True)

    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True, capture_output=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True, capture_output=True)
    g(work, "config", "user.email", "t@example.com")
    g(work, "config", "user.name", "t")
    g(work, "config", "commit.gpgsign", "false")
    (work / "base.txt").write_text("base\n", encoding="utf-8")
    g(work, "add", "-A")
    g(work, "commit", "-q", "-m", "base")
    g(work, "remote", "add", "origin", str(remote))
    g(work, "push", "-q", "origin", "main")
    g(work, "checkout", "-q", "-b", "feature")
    (work / "feature.txt").write_text("feat\n", encoding="utf-8")
    g(work, "add", "-A")
    g(work, "commit", "-q", "-m", "feat")
    g(work, "push", "-q", "origin", "feature:refs/pull/1/head")   # the PR head

    subprocess.run(["git", "clone", "-q", str(remote), str(consumer)], check=True, capture_output=True)
    g(consumer, "remote", "set-head", "origin", "main")   # so origin/HEAD → origin/main
    return consumer


def _init_git_repo(path):
    """A hermetic 2-commit git repo so range/commit resolution tests don't
    depend on the ambient checkout's history depth (CI clones shallow)."""
    def g(*a):
        subprocess.run(["git", *a], cwd=path, check=True, capture_output=True, text=True)
    g("init", "-q")
    g("config", "user.email", "t@example.com")
    g("config", "user.name", "t")
    g("config", "commit.gpgsign", "false")
    (path / "a.txt").write_text("one\n", encoding="utf-8")
    g("add", "-A")
    g("commit", "-q", "-m", "first")
    (path / "b.txt").write_text("two\n", encoding="utf-8")
    g("add", "-A")
    g("commit", "-q", "-m", "second")


class TestResolvers:
    def test_working_is_default(self, cli):
        s = cli._resolve_scope(_ns())
        assert s["kind"] == "working" and s["bounded"] is True

    def test_range_inferred_from_flag(self, cli, tmp_path, monkeypatch):
        _init_git_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        s = cli._resolve_scope(_ns(range="HEAD~1..HEAD"))
        assert s["kind"] == "range" and s["bounded"] and s["diff"]
        assert s["files"] == ["b.txt"]

    def test_commit(self, cli, tmp_path, monkeypatch):
        _init_git_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        s = cli._resolve_scope(_ns(scope="commit", commit="HEAD"))
        assert s["kind"] == "commit" and s["diff"] and s["files"] == ["b.txt"]

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

    def test_too_broad_fails_without_narrow(self, cli):
        # README is a project index referencing most of the repo — not a bounded
        # decision area. It must fail closed and demand --narrow, not resolve to
        # ~the whole repo just because each ref is a strict subset.
        with pytest.raises(cli.ScopeError, match="too broadly"):
            cli._resolve_scope(_ns(scope="adr", path="README.md"))

    def test_too_broad_recovers_with_narrow(self, cli):
        s = cli._resolve_scope(_ns(scope="adr", path="README.md", narrow="cli"))
        assert s["files"] and all(f.startswith("cli/") for f in s["files"])

    def test_broad_limit_is_relative_to_repo_size(self, cli):
        assert cli._adr_broad_limit(10) == cli._ADR_BROAD_FLOOR      # floor on tiny repos
        assert cli._adr_broad_limit(1000) == cli._ADR_MAX_SCOPE_FILES  # ceiling on huge repos
        assert cli._adr_broad_limit(200) == 80                        # 0.4 share in between


class TestRP:
    """Refactoring-proposal scope: same doc↔code bounding as ADR, its own kind."""

    def test_resolves_referenced_code(self, cli, tmp_path):
        rp = tmp_path / "rp.md"
        rp.write_text("Proposal: split the resolver in `cli/invairiant.py` "
                      "(`_resolve_scope`) into per-kind handlers.")
        s = cli._resolve_scope(_ns(scope="rp", path=str(rp)))
        assert s["kind"] == "rp" and "cli/invairiant.py" in s["files"]
        assert s["snapshot"] is True and s["diff"] is None
        assert s["docs"] and s["docs"][0]["path"] == str(rp)

    def test_missing_path_fails(self, cli):
        with pytest.raises(cli.ScopeError):
            cli._resolve_scope(_ns(scope="rp", path="no-such-proposal.md"))

    def test_no_references_fails_closed(self, cli, tmp_path):
        rp = tmp_path / "rp.md"
        rp.write_text("A prose-only proposal that names no tracked code whatsoever.")
        with pytest.raises(cli.ScopeError):
            cli._resolve_scope(_ns(scope="rp", path=str(rp)))

    def test_too_broad_message_names_the_proposal(self, cli):
        with pytest.raises(cli.ScopeError, match="refactoring proposal references resolved too broadly"):
            cli._resolve_scope(_ns(scope="rp", path="README.md"))

    def test_e2e_bundle_kind_is_rp(self, cli_path, repo_root, tmp_path):
        rp = tmp_path / "rp.md"
        rp.write_text("Refactor `cli/invairiant.py`.")
        out = tmp_path / "b.json"
        subprocess.run(["python3", str(cli_path), "collect", "--scope", "rp",
                        "--path", str(rp), "--out", str(out)],
                       cwd=repo_root, check=True, capture_output=True)
        d = json.loads(out.read_text(encoding="utf-8"))
        assert d["resolved_scope"]["kind"] == "rp" and d["resolved_scope"]["bounded"] is True
        assert d["resolved_scope"]["has_diff"] is False


class TestPR:
    """PR resolver adapter: optional (gh / pull-ref), resolves to a bounded
    base...head range, fails closed."""

    def test_requires_pr_number(self, cli):
        with pytest.raises(cli.ScopeError):
            cli._resolve_scope(_ns(scope="pr"))

    def test_pr_must_be_numeric(self, cli):
        with pytest.raises(cli.ScopeError):
            cli._resolve_scope(_ns(scope="pr", pr="abc"))

    def test_no_remote_fails_closed(self, cli, tmp_path, monkeypatch):
        _init_git_repo(tmp_path)   # commits but NO remote
        monkeypatch.chdir(tmp_path)
        with pytest.raises(cli.ScopeError, match="remote"):
            cli._resolve_scope(_ns(scope="pr", pr="1"))

    def test_resolves_pull_ref_to_bounded_range(self, cli, tmp_path, monkeypatch):
        consumer = _init_pr_repo(tmp_path)
        monkeypatch.chdir(consumer)                    # on main, NOT the PR head
        s = cli._resolve_scope(_ns(scope="pr", pr="1"))
        assert s["kind"] == "pr" and s["bounded"] is True
        assert s["files"] == ["feature.txt"]          # the PR's changed file only
        assert s["diff"] and s["range"] and "..." in s["range"]
        assert s["base"].endswith("/main") and s["resolver"] == "git"
        assert s["head_checked_out"] is False          # #3: drives the sparse-signals notice

    def test_head_checked_out_true_on_the_pr_branch(self, cli, tmp_path, monkeypatch):
        _init_pr_repo(tmp_path)
        monkeypatch.chdir(tmp_path / "work")           # this repo IS on the PR head (feature)
        s = cli._resolve_scope(_ns(scope="pr", pr="1"))
        assert s["kind"] == "pr" and s["head_checked_out"] is True

    def test_e2e_bundle_records_pr_resolution(self, cli_path, tmp_path):
        consumer = _init_pr_repo(tmp_path)
        out = tmp_path / "b.json"
        r = subprocess.run(["python3", str(cli_path), "collect", "--scope", "pr",
                            "--pr", "1", "--out", str(out)],
                           cwd=consumer, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        rs = json.loads(out.read_text(encoding="utf-8"))["resolved_scope"]
        assert rs["kind"] == "pr" and rs["has_diff"] is True and rs["bounded"] is True
        assert rs["base"].endswith("/main") and rs["resolver"] == "git" and rs["head"]
        assert rs["head_checked_out"] is False
        assert "not checked out" in r.stderr           # #3: the NOTICE fired


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
