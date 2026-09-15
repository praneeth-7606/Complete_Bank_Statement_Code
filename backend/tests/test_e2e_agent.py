from e2e_agent import E2EReport
from e2e_agent import _usage_metrics
from datetime import datetime, timezone


def test_e2e_report_has_traceable_status_and_evidence():
    report = E2EReport(
        run_id="run-1",
        base_url="http://localhost:3001",
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    report.status = "completed"
    assert report.status in {"running", "completed", "failed", "blocked"}
    assert report.evidence == []
    assert report.metrics["fallback_count"] == 0


def test_usage_metrics_reads_langchain_message_metadata():
    class Message:
        type = "ai"
        usage_metadata = {"input_tokens": 12, "output_tokens": 8}
        response_metadata = {}

    metrics = _usage_metrics({"messages": [Message()]})
    assert metrics["llm_calls"] == 1
    assert metrics["input_tokens"] == 12
    assert metrics["output_tokens"] == 8
