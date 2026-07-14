"""Unit tests for the pure helpers in cli/invairiant.py.

These import the module directly (see conftest) and exercise the logic that the
JSON schema cannot express: secret redaction, claim-key normalization, and the
semantic report linter.
"""

from __future__ import annotations

import json


# --------------------------------------------------------------------------- #
# _sanitize
# --------------------------------------------------------------------------- #
class TestSanitize:
    def test_redacts_api_key_assignment(self, cli):
        out = cli._sanitize("connect with api_key=SUPERSECRET123 to the host")
        assert "SUPERSECRET123" not in out
        assert "[REDACTED]" in out

    def test_redacts_secret_colon(self, cli):
        out = cli._sanitize("secret: hunter2please")
        assert "hunter2please" not in out
        assert "[REDACTED]" in out

    def test_redacts_token_assignment(self, cli):
        out = cli._sanitize("token=abc.def.ghi")
        assert "abc.def.ghi" not in out
        assert "[REDACTED]" in out

    def test_redacts_password_colon(self, cli):
        out = cli._sanitize("password: correcthorse")
        assert "correcthorse" not in out
        assert "[REDACTED]" in out

    def test_redacts_private_key_block(self, cli):
        # The redactor replaces the identifying BEGIN marker of a PEM private
        # key with a placeholder; the marker (and thus the "this is a private
        # key" signal) is removed.
        blob = "-----BEGIN RSA PRIVATE KEY-----\nMIIabc123\n-----END RSA PRIVATE KEY-----"
        out = cli._sanitize(blob)
        assert "-----BEGIN RSA PRIVATE KEY-----" not in out
        assert "[REDACTED KEY]" in out

    def test_truncates_to_600_chars(self, cli):
        out = cli._sanitize("x" * 5000)
        assert len(out) == 600

    def test_passes_normal_prose_unchanged(self, cli):
        prose = "The scheduler rebuilds its run queue from the cache on restart."
        assert cli._sanitize(prose) == prose

    def test_non_str_input_returned_as_is(self, cli):
        assert cli._sanitize(None) is None
        assert cli._sanitize(42) == 42
        payload = {"a": 1}
        assert cli._sanitize(payload) is payload


# --------------------------------------------------------------------------- #
# _claim_key
# --------------------------------------------------------------------------- #
class TestClaimKey:
    def test_lowercases_and_strips_non_alphanumeric(self, cli):
        assert cli._claim_key("Hello, World! (v2)") == "helloworldv2"

    def test_truncates_to_80(self, cli):
        assert len(cli._claim_key("a" * 200)) == 80

    def test_surface_variants_produce_same_key(self, cli):
        a = cli._claim_key("Webhook retries re-POST without an idempotency key.")
        b = cli._claim_key("  webhook  retries re-POST, without an idempotency key!!! ")
        assert a == b

    def test_different_claims_differ(self, cli):
        a = cli._claim_key("Secrets leak to the operator log")
        b = cli._claim_key("Redis is treated as the source of truth")
        assert a != b

    def test_empty_and_none(self, cli):
        assert cli._claim_key("") == ""
        assert cli._claim_key(None) == ""


# --------------------------------------------------------------------------- #
# _report_threshold
# --------------------------------------------------------------------------- #
class TestReportThreshold:
    def test_default_when_missing(self, cli, tmp_path):
        assert cli._report_threshold(str(tmp_path / "nope.yml")) == 6.0

    def test_reads_from_config(self, cli, tmp_path):
        cfg = tmp_path / "invairiant.config.yml"
        cfg.write_text("severity_policy:\n  low_score_threshold: 7.5\n", encoding="utf-8")
        assert cli._report_threshold(str(cfg)) == 7.5


# --------------------------------------------------------------------------- #
# known_lens_ids
# --------------------------------------------------------------------------- #
class TestKnownLensIds:
    def test_contains_core_lenses(self, cli):
        ids = cli.known_lens_ids()
        assert {"parnas", "mcconnell", "turing", "security-threat"} <= ids

    def test_excludes_readme(self, cli):
        assert "README" not in cli.known_lens_ids()


# --------------------------------------------------------------------------- #
# _semantic_report_errors
# --------------------------------------------------------------------------- #
class TestSemanticReportErrors:
    def _finding(self, **kw):
        base = {
            "id": "T-001",
            "severity": "S2",
            "lens": "parnas",
            "claim": "some claim",
            "confidence": "high",
            "status": "verified",
        }
        base.update(kw)
        return base

    def test_open_s0_without_fail_verdict_is_error(self, cli, base_report):
        d = base_report()
        d["findings"] = [self._finding(id="T-001", severity="S0", confidence="high")]
        d["summary"]["verdict"] = "pass_with_conditions"
        errs, _ = cli._semantic_report_errors(d, 6.0)
        assert any("S0" in e and "fail" in e for e in errs)

    def test_open_s1_with_pass_verdict_is_error(self, cli, base_report):
        d = base_report()
        d["findings"] = [self._finding(id="T-001", severity="S1", confidence="high")]
        d["summary"]["verdict"] = "pass"
        errs, _ = cli._semantic_report_errors(d, 6.0)
        assert any("S1" in e and "pass" in e for e in errs)

    def test_s1_low_confidence_is_error(self, cli, base_report):
        d = base_report()
        d["findings"] = [self._finding(id="T-001", severity="S1", confidence="low")]
        # keep the verdict consistent so we isolate the confidence error
        d["summary"]["verdict"] = "pass_with_conditions"
        errs, _ = cli._semantic_report_errors(d, 6.0)
        assert any("confidence" in e for e in errs)

    def test_verified_without_verification_warns(self, cli, base_report):
        d = base_report()
        d["findings"] = [self._finding(id="T-1", status="verified")]  # no verification record
        d["summary"]["verdict"] = "pass_with_conditions"
        errs, warns = cli._semantic_report_errors(d, 6.0)
        assert not any("provenance" in e for e in errs)   # warn, not error
        assert any("verified" in w and "provenance" in w for w in warns)

    def test_verified_with_verification_is_clean(self, cli, base_report):
        d = base_report()
        d["findings"] = [self._finding(id="T-1", status="verified",
                                       verification={"verified_by": "agent-2", "method": "re-read cited lines"})]
        d["summary"]["verdict"] = "pass_with_conditions"
        _, warns = cli._semantic_report_errors(d, 6.0)
        # the verification-record nudge must not fire when verification is present
        # (distinct from the report-level provenance-block nudge below)
        assert not any("verification record" in w for w in warns)

    def test_findings_without_provenance_block_warns(self, cli, base_report, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        d = base_report()
        d["findings"] = [self._finding(id="T-1")]  # no top-level provenance block
        d["summary"]["verdict"] = "pass_with_conditions"
        errs, warns = cli._semantic_report_errors(d, 6.0)
        assert any("provenance" in w and "bundle_hash" in w for w in warns)  # the binding nudge
        assert not any("provenance" in e for e in errs)                      # warn, not error

    def test_valid_provenance_block_is_clean(self, cli, base_report, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        d = base_report()
        d["findings"] = [self._finding(id="T-1", verification={"verified_by": "a", "method": "b"})]
        d["summary"]["verdict"] = "pass_with_conditions"
        d["provenance"] = {"commit_sha": "a" * 40, "scope_hash": "b" * 64, "bundle_hash": "c" * 64}
        errs, warns = cli._semantic_report_errors(d, 6.0)
        assert not any("provenance" in w for w in warns)
        assert not any("provenance" in e for e in errs)

    def test_malformed_provenance_hash_is_error(self, cli, base_report, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        d = base_report()
        d["findings"] = [self._finding(id="T-1")]
        d["provenance"] = {"bundle_hash": "not-a-real-sha256"}
        errs, _ = cli._semantic_report_errors(d, 6.0)
        assert any("bundle_hash" in e and "not a valid hash" in e for e in errs)

    def test_strict_promotes_verified_without_verification_to_error(self, cli, base_report, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        d = base_report()
        d["findings"] = [self._finding(id="T-1", status="verified")]     # no verification
        d["provenance"] = {"commit_sha": "a" * 40}                       # so only the verification nudge fires
        d["summary"]["verdict"] = "pass_with_conditions"
        errs, warns = cli._semantic_report_errors(d, 6.0, strict=True)
        assert any("verification record" in e for e in errs)
        assert not any("verification record" in w for w in warns)

    def test_strict_promotes_missing_provenance_to_error(self, cli, base_report, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        d = base_report()
        d["findings"] = [self._finding(id="T-1", verification={"verified_by": "a", "method": "b"})]
        d["summary"]["verdict"] = "pass_with_conditions"
        errs, _ = cli._semantic_report_errors(d, 6.0, strict=True)
        assert any("provenance" in e and "bundle_hash" in e for e in errs)

    def test_default_keeps_completeness_nudges_as_warnings(self, cli, base_report, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        d = base_report()
        d["findings"] = [self._finding(id="T-1", status="verified")]     # no verification, no provenance
        d["summary"]["verdict"] = "pass_with_conditions"
        errs, warns = cli._semantic_report_errors(d, 6.0)                # non-strict default
        assert not any("verification record" in e or "provenance" in e for e in errs)
        assert any("verification record" in w for w in warns)
        assert any("provenance" in w for w in warns)

    def test_lens_score_evidence_ref_to_unknown_finding_is_error(self, cli, base_report):
        d = base_report()
        d["findings"] = [self._finding(id="T-001")]
        d["lens_scores"] = [
            {"pack": "core", "lens": "parnas", "score": 8, "evidence_refs": ["T-999"]}
        ]
        errs, _ = cli._semantic_report_errors(d, 6.0)
        assert any("T-999" in e and "not a finding id" in e for e in errs)

    def test_required_action_unknown_finding_id_is_error(self, cli, base_report):
        d = base_report()
        d["findings"] = [self._finding(id="T-001")]
        d["summary"]["required_actions"] = [
            {"action": "fix it", "finding_ids": ["T-404"], "blocking": True}
        ]
        errs, _ = cli._semantic_report_errors(d, 6.0)
        assert any("T-404" in e and "unknown finding id" in e for e in errs)

    def test_duplicate_finding_ids_is_error(self, cli, base_report):
        d = base_report()
        d["findings"] = [self._finding(id="DUP-1"), self._finding(id="DUP-1")]
        errs, _ = cli._semantic_report_errors(d, 6.0)
        assert any("duplicate finding id" in e and "DUP-1" in e for e in errs)

    def test_consistent_report_has_zero_errors(self, cli, base_report, monkeypatch, tmp_path):
        # chdir to a clean dir so no committed rejected-hypotheses.jsonl bleeds in
        monkeypatch.chdir(tmp_path)
        d = base_report()
        d["findings"] = [self._finding(id="T-001", severity="S2")]
        d["lens_scores"] = [
            {"pack": "core", "lens": "parnas", "score": 8, "evidence_refs": ["T-001"]}
        ]
        d["summary"]["required_actions"] = [
            {"action": "fix", "finding_ids": ["T-001"], "blocking": False}
        ]
        errs, warns = cli._semantic_report_errors(d, 6.0)
        assert errs == []

    def test_low_score_no_finding_no_evidence_is_warning_not_error(self, cli, base_report, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        d = base_report()
        # A lens scored below threshold, with no finding on that lens and no refs.
        d["lens_scores"] = [{"pack": "core", "lens": "turing", "score": 3.0}]
        errs, warns = cli._semantic_report_errors(d, 6.0)
        assert errs == []
        assert any("turing" in w and "no finding" in w for w in warns)

    def test_missing_hypotheses_is_warning(self, cli, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        d = {
            "findings": [],
            "lens_scores": [],
            "summary": {"verdict": "pass", "required_actions": []},
        }  # deliberately no "hypotheses" key
        errs, warns = cli._semantic_report_errors(d, 6.0)
        assert errs == []
        assert any("hypotheses" in w for w in warns)

    def test_rejected_hypothesis_revival_is_warning(self, cli, base_report, monkeypatch, tmp_path):
        # Build audit memory in an isolated cwd.
        monkeypatch.chdir(tmp_path)
        histdir = tmp_path / ".invairiant" / "history"
        histdir.mkdir(parents=True)
        claim = "Dispatch loop starves low-priority tenants under saturation"
        rec = {"claim_key": cli._claim_key(claim)}
        (histdir / "rejected-hypotheses.jsonl").write_text(
            json.dumps(rec) + "\n", encoding="utf-8"
        )
        d = base_report()
        # A finding whose claim maps to the same key as the rejected hypothesis.
        d["findings"] = [self._finding(id="T-001", claim=claim.upper())]
        errs, warns = cli._semantic_report_errors(d, 6.0)
        assert any("previously-rejected" in w for w in warns)

    def test_real_case_study_report_is_clean(self, cli, valid_report, monkeypatch, tmp_path):
        # The shipped case-study report must pass the semantic linter with no errors.
        monkeypatch.chdir(tmp_path)
        errs, _ = cli._semantic_report_errors(valid_report, 6.0)
        assert errs == []


# --------------------------------------------------------------------------- #
# _citation_errors  (opt-in: cited file/lines are real — issue #2)
# --------------------------------------------------------------------------- #
class TestCitationCheck:
    def _report(self, evidence):
        return {"findings": [{"id": "C-1", "evidence": evidence}]}

    def test_real_file_and_line_range_pass(self, cli, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "svc.py").write_text("\n".join(f"line{i}" for i in range(1, 21)))  # 20 lines
        errs = cli._citation_errors(self._report([
            {"type": "file_lines", "file": "svc.py", "lines": "5-10"}]))
        assert errs == []

    def test_missing_file_is_error(self, cli, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        errs = cli._citation_errors(self._report([
            {"type": "file_lines", "file": "nope.py", "lines": "1"}]))
        assert any("does not exist" in e and "nope.py" in e for e in errs)

    def test_lines_out_of_range_is_error(self, cli, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "small.py").write_text("a\nb\nc\n")  # 3 lines
        errs = cli._citation_errors(self._report([
            {"type": "file_lines", "file": "small.py", "lines": "5-9"}]))
        assert any("out of range" in e and "small.py" in e and "3 line" in e for e in errs)

    def test_non_file_lines_evidence_is_skipped(self, cli, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        errs = cli._citation_errors(self._report([
            {"type": "diff_hunk", "hunk": "-a\n+b"}]))
        assert errs == []

    def test_file_lines_without_file_is_error(self, cli, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        errs = cli._citation_errors(self._report([{"type": "file_lines", "lines": "1"}]))
        assert any("no 'file'" in e for e in errs)

    def test_file_without_lines_only_checks_existence(self, cli, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "exists.py").write_text("x = 1\n")
        errs = cli._citation_errors(self._report([
            {"type": "file_lines", "file": "exists.py"}]))  # no lines -> existence only
        assert errs == []

    def test_resolves_at_commit(self, cli, monkeypatch, tmp_path):
        import subprocess
        monkeypatch.chdir(tmp_path)
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "f.py").write_text("a\nb\nc\n")
        subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-qm", "one"], cwd=tmp_path, check=True)
        # cited at HEAD: 3 lines exist; line 9 does not
        assert cli._citation_errors(self._report([
            {"type": "file_lines", "file": "f.py", "lines": "1-3", "commit": "HEAD"}])) == []
        assert any("out of range" in e for e in cli._citation_errors(self._report([
            {"type": "file_lines", "file": "f.py", "lines": "9", "commit": "HEAD"}])))


# --------------------------------------------------------------------------- #
# _provenance_check  (bind report ↔ commit ↔ bundle — issue #2)
# --------------------------------------------------------------------------- #
class TestProvenanceCheck:
    def _rep(self, **prov):
        return {"provenance": prov} if prov else {}

    def _bundle(self, **prov):
        b = {"schema": "invairiant.evidence-bundle/v1", "signals": {}, "provenance": dict(prov)}
        return b

    def test_no_provenance_warns_by_default(self, cli):
        errs, warns = cli._provenance_check({}, commit="abcdef1234")
        assert errs == [] and any("no 'provenance'" in w for w in warns)

    def test_no_provenance_errors_with_require(self, cli):
        errs, _ = cli._provenance_check({}, commit="abcdef1234", require=True)
        assert any("no 'provenance'" in e for e in errs)

    def test_commit_match_is_clean(self, cli):
        errs, _ = cli._provenance_check(self._rep(commit_sha="abcdef1234567890"),
                                        commit="abcdef1234567890")
        assert errs == []

    def test_commit_short_vs_full_matches(self, cli):
        errs, _ = cli._provenance_check(self._rep(commit_sha="abcdef1"),
                                        commit="abcdef1234567890")
        assert errs == []

    def test_commit_mismatch_is_error(self, cli):
        errs, _ = cli._provenance_check(self._rep(commit_sha="deadbeef1"), commit="abcdef1234")
        assert any("was built for commit" in e for e in errs)

    def test_malformed_hash_is_error(self, cli):
        errs, _ = cli._provenance_check(self._rep(bundle_hash="not-a-valid-hash"))
        assert any("bundle_hash is not a valid hash" in e for e in errs)

    def test_bundle_match_is_clean(self, cli):
        b = self._bundle(commit_sha="a" * 40, scope_hash="b" * 64)
        b["provenance"]["bundle_hash"] = cli._recompute_bundle_hash(b)
        report = self._rep(commit_sha="a" * 40, scope_hash="b" * 64,
                           bundle_hash=b["provenance"]["bundle_hash"])
        errs, warns = cli._provenance_check(report, bundle=b)
        assert errs == [] and not any("differs" in w for w in warns)

    def test_edited_bundle_fails_integrity(self, cli):
        b = self._bundle(commit_sha="a" * 40)
        b["provenance"]["bundle_hash"] = cli._recompute_bundle_hash(b)
        b["signals"]["injected"] = ["tamper"]           # edited after it was hashed
        errs, _ = cli._provenance_check(self._rep(commit_sha="a" * 40), bundle=b)
        assert any("corrupt or was edited" in e for e in errs)

    def test_bundle_hash_mismatch_is_warning_not_error(self, cli):
        b = self._bundle(commit_sha="a" * 40, scope_hash="b" * 64)
        b["provenance"]["bundle_hash"] = cli._recompute_bundle_hash(b)
        report = self._rep(commit_sha="a" * 40, scope_hash="b" * 64, bundle_hash="c" * 64)
        errs, warns = cli._provenance_check(report, bundle=b)
        assert errs == [] and any("bundle_hash differs" in w for w in warns)

    def test_commit_mismatch_vs_bundle_is_error(self, cli):
        b = self._bundle(commit_sha="a" * 40)
        b["provenance"]["bundle_hash"] = cli._recompute_bundle_hash(b)
        report = self._rep(commit_sha="f" * 40, bundle_hash=b["provenance"]["bundle_hash"])
        errs, _ = cli._provenance_check(report, bundle=b)
        assert any("does not match the bundle's commit_sha" in e for e in errs)

    def test_require_exact_bundle_promotes_bundle_hash_mismatch_to_error(self, cli):
        b = self._bundle(commit_sha="a" * 40, scope_hash="b" * 64)
        b["provenance"]["bundle_hash"] = cli._recompute_bundle_hash(b)
        report = self._rep(commit_sha="a" * 40, scope_hash="b" * 64, bundle_hash="c" * 64)
        errs, warns = cli._provenance_check(report, bundle=b, require_exact_bundle=True)
        assert any("bundle_hash differs" in e for e in errs)
        assert not any("bundle_hash differs" in w for w in warns)

    def test_require_exact_bundle_promotes_scope_hash_mismatch_to_error(self, cli):
        b = self._bundle(commit_sha="a" * 40, scope_hash="b" * 64)
        b["provenance"]["bundle_hash"] = cli._recompute_bundle_hash(b)
        report = self._rep(commit_sha="a" * 40, scope_hash="d" * 64,
                           bundle_hash=b["provenance"]["bundle_hash"])
        errs, _ = cli._provenance_check(report, bundle=b, require_exact_bundle=True)
        assert any("scope_hash differs" in e for e in errs)

    def test_require_exact_bundle_clean_when_it_matches(self, cli):
        b = self._bundle(commit_sha="a" * 40, scope_hash="b" * 64)
        b["provenance"]["bundle_hash"] = cli._recompute_bundle_hash(b)
        report = self._rep(commit_sha="a" * 40, scope_hash="b" * 64,
                           bundle_hash=b["provenance"]["bundle_hash"])
        errs, _ = cli._provenance_check(report, bundle=b, require_exact_bundle=True)
        assert errs == []
