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
        assert not any("provenance" in w for w in warns)

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
