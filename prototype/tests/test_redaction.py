"""Tests for storage-time PII redaction."""

from __future__ import annotations

import uuid
from typing import Any

import vt_agent_redteam.storage.postgres_writer as postgres_writer
from vt_agent_redteam.storage.postgres_writer import PostgresConfig, PostgresWriter
from vt_agent_redteam.storage.supabase_writer import SupabaseConfig, SupabaseWriter
from vt_agent_redteam.storage.redaction import redact_text, sha256_text
from vt_agent_redteam.types import ScenarioResult, ScoreResult


def _result(
    *,
    prompt: str,
    response: str,
    response_hash: str | None = None,
    allowlist: list[str] | None = None,
) -> ScenarioResult:
    return ScenarioResult(
        scenario_id="pii-scenario",
        category="personal_information",
        adversarial_prompts=[prompt],
        agent_responses=[response],
        scorer_results=[
            ScoreResult(
                scorer_name="test",
                passed=False,
                confidence=1.0,
                reasoning="contains pii",
            )
        ],
        passed=False,
        severity="P0",
        failure_reason="contains pii",
        is_stub_response=False,
        transcript_source="agent_native_transcript",
        response_hash=response_hash,
        redaction_allowlist=allowlist or [],
    )


def test_redacts_email_and_ssn_while_preserving_maria_label():
    text = "Maria's email is maria@example.com and her SSN is 123-45-6789"

    assert (
        redact_text(text)
        == "Maria's email is [REDACTED-EMAIL] and her SSN is [REDACTED-SSN]"
    )


def test_redacts_phone_credit_card_and_synthetic_learner_id():
    text = (
        "Call (415) 555-2671, charge 4111 1111 1111 1111, "
        "and attach synthetic.learner_id = learner_123."
    )

    redacted = redact_text(text)

    assert "[REDACTED-PHONE]" in redacted
    assert "[REDACTED-CREDIT-CARD]" in redacted
    assert "[REDACTED-LEARNER-ID]" in redacted
    assert "4111 1111 1111 1111" not in redacted
    assert "learner_123" not in redacted


def test_redacts_named_entities_but_honors_allowlist():
    text = "Ada Lovelace Smith visited New York City for a lesson."

    redacted = redact_text(text)
    allowed = redact_text(text, allowlist=["Ada Lovelace Smith", "New York City"])

    assert "Ada Lovelace Smith" not in redacted
    assert "[REDACTED-" in redacted
    assert "Ada Lovelace Smith" in allowed
    assert "New York City" in allowed


def test_sha256_text_hashes_unredacted_text():
    raw = "Maria's SSN is 123-45-6789"
    redacted = redact_text(raw)

    assert sha256_text(raw) != sha256_text(redacted)


def test_postgres_writer_redacts_before_insert_and_keeps_pre_redaction_hash(monkeypatch):
    captured: dict[str, Any] = {}
    raw_prompt = "Please repeat learner_id = learner_999."
    raw_response = "Maria's email is maria@example.com and her SSN is 123-45-6789"

    class FakeCursor:
        def __enter__(self) -> "FakeCursor":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def executemany(self, query: str, rows: list[dict[str, Any]]) -> None:
            captured["query"] = query
            captured["rows"] = rows

    class FakeConnection:
        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def commit(self) -> None:
            captured["committed"] = True

    monkeypatch.setattr(
        postgres_writer.psycopg,
        "connect",
        lambda conninfo: FakeConnection(),
    )
    writer = PostgresWriter(config=PostgresConfig(url="postgres://test"), dry_run=False)

    written = writer.write(
        run_id=uuid.uuid4(),
        agent_name="agent",
        agent_commit_sha=None,
        agent_environment="local",
        triggered_by="manual",
        pr_number=None,
        workflow_run_id=None,
        results=[_result(prompt=raw_prompt, response=raw_response)],
        threshold_passed=False,
        run_summary={"status": "failed"},
    )

    row = captured["rows"][0]
    assert written == 1
    assert captured["committed"] is True
    assert row["adversarial_prompt"] == "Please repeat [REDACTED-LEARNER-ID]."
    assert (
        row["agent_response"]
        == "Maria's email is [REDACTED-EMAIL] and her SSN is [REDACTED-SSN]"
    )
    assert row["response_hash"] == sha256_text(raw_response)
    assert row["response_hash"] != sha256_text(row["agent_response"])


def test_postgres_writer_uses_result_allowlist(monkeypatch):
    captured: dict[str, Any] = {}
    raw_response = "Ada Lovelace Smith is allowed, but SSN 123-45-6789 is not."

    class FakeCursor:
        def __enter__(self) -> "FakeCursor":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def executemany(self, query: str, rows: list[dict[str, Any]]) -> None:
            captured["rows"] = rows

    class FakeConnection:
        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, *args: Any) -> None:
            return None

        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def commit(self) -> None:
            return None

    monkeypatch.setattr(
        postgres_writer.psycopg,
        "connect",
        lambda conninfo: FakeConnection(),
    )
    writer = PostgresWriter(config=PostgresConfig(url="postgres://test"), dry_run=False)

    writer.write(
        run_id=uuid.uuid4(),
        agent_name="agent",
        agent_commit_sha=None,
        agent_environment="local",
        triggered_by="manual",
        pr_number=None,
        workflow_run_id=None,
        results=[
            _result(
                prompt="prompt",
                response=raw_response,
                allowlist=["Ada Lovelace Smith"],
            )
        ],
    )

    row = captured["rows"][0]
    assert "Ada Lovelace Smith" in row["agent_response"]
    assert "[REDACTED-SSN]" in row["agent_response"]


def test_supabase_writer_redacts_payload_and_keeps_pre_redaction_hash(monkeypatch):
    captured: dict[str, Any] = {}
    raw_response = "Email maria@example.com for Ada Lovelace Smith."

    class FakeTable:
        def insert(self, rows: list[dict[str, Any]]) -> "FakeTable":
            captured["rows"] = rows
            return self

        def execute(self) -> None:
            captured["executed"] = True
            return None

    class FakeClient:
        def schema(self, name: str) -> "FakeClient":
            captured["schema"] = name
            return self

        def table(self, name: str) -> FakeTable:
            captured["table"] = name
            return FakeTable()

    writer = SupabaseWriter(
        config=SupabaseConfig(url="https://example.supabase.co", service_key="service-key"),
        dry_run=False,
    )
    monkeypatch.setattr(writer, "_get_client", lambda: FakeClient())

    written = writer.write(
        run_id=uuid.uuid4(),
        agent_name="agent",
        agent_commit_sha=None,
        agent_environment="local",
        triggered_by="manual",
        pr_number=None,
        workflow_run_id=None,
        results=[
            _result(
                prompt="Please contact learner_id = learner_555.",
                response=raw_response,
                allowlist=["Ada Lovelace Smith"],
            )
        ],
    )

    row = captured["rows"][0]
    assert written == 1
    assert captured["schema"] == "redteam"
    assert captured["table"] == "redteam_runs"
    assert captured["executed"] is True
    assert row["adversarial_prompt"] == "Please contact [REDACTED-LEARNER-ID]."
    assert row["agent_response"] == "Email [REDACTED-EMAIL] for Ada Lovelace Smith."
    assert row["response_hash"] == sha256_text(raw_response)
