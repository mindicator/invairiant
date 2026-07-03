"""v0.2 hardening: hardened secret redaction, repo-root memory resolution,
and the bounded `collect` scan on large repos."""

from __future__ import annotations

import json
import subprocess

import pytest


class TestRedactionHardening:
    def test_full_pem_block_body_redacted(self, cli):
        pem = ("note -----BEGIN RSA PRIVATE KEY-----\n"
               "MIIBOAIBAAJAabcdEFGH1234base64body\n"
               "-----END RSA PRIVATE KEY----- end")
        out = cli._sanitize(pem)
        assert "MIIBOAIBAAJAabcdEFGH1234base64body" not in out
        assert "[REDACTED KEY]" in out

    def test_aws_access_key(self, cli):
        assert "AKIAIOSFODNN7EXAMPLE" not in cli._sanitize("id AKIAIOSFODNN7EXAMPLE x")

    def test_github_token(self, cli):
        tok = "ghp_" + "a" * 36
        assert tok not in cli._sanitize(f"token {tok}")

    def test_authorization_bearer_fully_redacted(self, cli):
        assert "abcdef1234567890" not in cli._sanitize("Authorization: Bearer abcdef1234567890")

    def test_standalone_bearer(self, cli):
        assert "abcdef1234567890xyz" not in cli._sanitize("send Bearer abcdef1234567890xyz now")

    @pytest.mark.parametrize("s", [
        "the token boundary is clean",
        "secret sauce is documentation",
        "password rotation policy",
    ])
    def test_prose_with_secret_words_untouched(self, cli, s):
        assert cli._sanitize(s) == s


class TestRepoRootMemory:
    def test_history_dir_under_repo_root(self, cli, repo_root):
        assert cli._history_dir() == repo_root / ".invairiant" / "history"

    def test_history_dir_stable_from_subdir(self, cli, repo_root, monkeypatch):
        monkeypatch.chdir(repo_root / "docs")
        assert cli._history_dir() == repo_root / ".invairiant" / "history"

    def test_repo_root_resolves_git_toplevel(self, cli, tmp_path, monkeypatch):
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
        monkeypatch.chdir(tmp_path)
        assert cli._repo_root().resolve() == tmp_path.resolve()
        assert cli._history_dir().resolve() == (tmp_path / ".invairiant" / "history").resolve()


class TestCollectBounds:
    def test_is_probably_binary(self, cli, tmp_path):
        b = tmp_path / "b.bin"; b.write_bytes(b"abc\x00def")
        t = tmp_path / "t.txt"; t.write_text("hello world")
        assert cli._is_probably_binary(b) is True
        assert cli._is_probably_binary(t) is False

    def test_new_budget_shape(self, cli):
        bud = cli._new_budget()
        for k in ("max_files", "max_bytes", "files_scanned",
                  "skipped_large_or_binary", "truncated", "ripgrep"):
            assert k in bud
        assert bud["files_scanned"] == 0 and bud["truncated"] is False

    def test_scan_fallback_skips_large_files(self, cli, tmp_path, monkeypatch):
        monkeypatch.setattr(cli.shutil, "which", lambda _name: None)  # force the fallback
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
        (tmp_path / "small.py").write_text("import os\nos.system('ls')\n")
        (tmp_path / "big.py").write_text("x = 1\n" * 200_000)  # > 512 KB
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        monkeypatch.chdir(tmp_path)
        bud = cli._new_budget()
        res = cli._scan({"shell": cli._SIGNAL_PATTERNS["shell"]}, 50, bud)
        assert bud["skipped_large_or_binary"] >= 1                 # big.py skipped
        assert any("small.py" in it["file"] for it in res["shell"])  # small.py matched

    def test_collect_bundle_reports_limits(self, cli_path, repo_root, tmp_path):
        out = tmp_path / "bundle.json"
        subprocess.run(["python3", str(cli_path), "collect", "--out", str(out)],
                       cwd=repo_root, check=True, capture_output=True)
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "limits" in data
        assert {"max_files", "max_bytes", "truncated"} <= set(data["limits"])
