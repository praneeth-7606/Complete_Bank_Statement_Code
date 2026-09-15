from e2e_agent import E2EReport
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
