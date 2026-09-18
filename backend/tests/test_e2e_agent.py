from datetime import datetime, timezone

from e2e_agent import BrowserDriver, E2EReport, Evidence, _usage_metrics, build_tools, run_public_smoke


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


def test_public_smoke_rejects_google_auth_ui():
    class GoogleDriver(FakeDriver):
        def run(self, step, *args, **kwargs):
            evidence = super().run(step, *args, **kwargs)
            if step == "public-login-snapshot":
                evidence.output = "Sign in with Google"
            return evidence

    report = E2EReport(run_id="run-4", base_url="http://localhost:3001", started_at="now")
    assert run_public_smoke(GoogleDriver(), report) is False
    assert "Google authentication UI" in report.issues[0]


def test_browser_driver_uses_cmd_shim_on_windows(monkeypatch, tmp_path):
    monkeypatch.setattr("e2e_agent.os.name", "nt")
    driver = BrowserDriver("http://localhost:3001", tmp_path, session="test-session")
    driver.binary = "C:/tools/agent-browser.cmd"
    assert driver._command("snapshot")[:4] == ["cmd.exe", "/d", "/c", "C:/tools/agent-browser.cmd"]


def test_upload_tool_allows_exact_explicit_fixture(monkeypatch, tmp_path):
    fixture = tmp_path / "statement.pdf"
    fixture.write_bytes(b"%PDF-1.4")
    monkeypatch.setenv("E2E_ALLOWED_FILES", str(fixture))
    monkeypatch.setenv("E2E_FIXTURE_DIR", str(tmp_path / "fixtures"))
    driver = BrowserDriver("http://localhost:3001", tmp_path / "artifacts")
    driver.run = lambda step, *args, **kwargs: Evidence(step=step, action=" ".join(args), ok=True)
    tools = build_tools(driver)
    upload_tool = next(tool for tool in tools if tool.name == "upload_file")
    result = upload_tool.invoke({"ref_or_locator": "@e1", "file_path": str(fixture)})
    assert "not in E2E_FIXTURE_DIR" not in result
