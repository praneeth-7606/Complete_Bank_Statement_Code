from datetime import datetime, timezone

from e2e_agent import E2EReport, Evidence, _usage_metrics, run_public_smoke


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


class FakeDriver:
    base_url = "http://localhost:3001"

    def __init__(self, urls=("/signup", "/login")):
        self.urls = iter(urls)

    def run(self, step, *args, **kwargs):
        output = next(self.urls, "") if args[:2] == ("get", "url") else "ok"
        return Evidence(step=step, action=" ".join(args), ok=True, output=output)


def test_public_smoke_asserts_signup_and_auth_redirect_urls():
    report = E2EReport(run_id="run-2", base_url="http://localhost:3001", started_at="now")
    assert run_public_smoke(FakeDriver(), report) is True
    assert all(item.ok for item in report.evidence)


def test_public_smoke_reports_wrong_signup_url():
    report = E2EReport(run_id="run-3", base_url="http://localhost:3001", started_at="now")
    assert run_public_smoke(FakeDriver(("/login", "/login")), report) is False
    assert "signup-url" in report.issues[0]
