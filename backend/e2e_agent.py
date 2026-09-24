"""Application-specific browser E2E agent.

This is intentionally separate from the API runtime. It drives a persistent
agent-browser session through LangChain tools and writes an evidence-rich JSON
report. The browser CLI is an explicit dependency so the same runner works in
CI, locally, and against a deployed frontend.

Usage:
    python e2e_agent.py --base-url http://localhost:3001
    python e2e_agent.py --base-url https://your-app.example --email ... --password ...
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    step: str
    action: str
    ok: bool
    output: str = ""
    duration_ms: int = 0
    artifact: Optional[str] = None
    error: Optional[str] = None


class E2EReport(BaseModel):
    run_id: str
    base_url: str
    started_at: str
    completed_at: Optional[str] = None
    status: str = "running"
    scenarios: List[str] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=lambda: {
        "llm_calls": 0, "input_tokens": 0, "output_tokens": 0,
        "estimated_cost_usd": 0.0, "fallback_count": 0, "trace_url": None,
    })


class BrowserDriver:
    """Small, auditable adapter around the agent-browser CLI."""

    def __init__(self, base_url: str, artifacts: Path, session: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.artifacts = artifacts
        self.session = session or f"finance-e2e-{uuid.uuid4().hex[:8]}"
        configured_binary = os.getenv("AGENT_BROWSER_BIN")
        local_bin_dir = Path(__file__).resolve().parents[1] / "frontend" / "node_modules" / ".bin"
        local_native = local_bin_dir.parent / "agent-browser" / "bin" / "agent-browser-win32-x64.exe"
        local_candidates = [local_native, local_bin_dir / "agent-browser.cmd", local_bin_dir / "agent-browser"]
        local_binary = next((candidate for candidate in local_candidates if candidate.is_file()), None)
        if configured_binary and configured_binary.lower().endswith((".cmd", ".bat")) and os.name == "nt":
            configured_native = Path(configured_binary).parent.parent / "agent-browser" / "bin" / "agent-browser-win32-x64.exe"
            self.binary = str(configured_native) if configured_native.is_file() else configured_binary
        else:
            self.binary = configured_binary or (str(local_binary) if local_binary else "agent-browser")
        self.artifacts.mkdir(parents=True, exist_ok=True)

    def _command(self, *args: str) -> List[str]:
        """Build a cross-platform command, including Windows .cmd shims."""
        command = [self.binary, "--session", self.session, *args]
        if os.name == "nt" and self.binary.lower().endswith((".cmd", ".bat")):
            return ["cmd.exe", "/d", "/c", *command]
        return command

    def _run_subprocess(self, *args: str) -> subprocess.CompletedProcess[str]:
        command = self._command(*args)
        # The Windows native browser binary can keep inherited PIPE handles open
        # while its short-lived command completes. A file-backed stream avoids
        # that deadlock while preserving command output for evidence.
        with tempfile.TemporaryFile(mode="w+b") as stream:
            result = subprocess.run(
                command, stdout=stream, stderr=stream, timeout=45, check=False
            )
            stream.seek(0)
            output = stream.read().decode("utf-8", errors="replace")
        return subprocess.CompletedProcess(command, result.returncode, output, "")

    def run(self, step: str, *args: str, screenshot: bool = False) -> Evidence:
        started = time.perf_counter()
        try:
            result = self._run_subprocess(*args)
            output = (result.stdout or result.stderr or "").strip()
            artifact = None
            if screenshot:
                artifact_path = self.artifacts / f"{len(list(self.artifacts.glob('*.png'))):03d}-{step}.png"
                shot = self._run_subprocess("screenshot", str(artifact_path))
                if shot.returncode == 0 and artifact_path.exists():
                    artifact = str(artifact_path)
            ok = result.returncode == 0
            return Evidence(
                step=step, action=" ".join(args), ok=ok, output=output[-8000:],
                duration_ms=round((time.perf_counter() - started) * 1000),
                artifact=artifact, error=None if ok else output[-2000:],
            )
        except subprocess.TimeoutExpired:
            return Evidence(
                step=step, action=" ".join(args), ok=False,
                duration_ms=round((time.perf_counter() - started) * 1000),
                error="agent-browser command timed out after 45 seconds",
            )
        except Exception as exc:
            return Evidence(
                step=step, action=" ".join(args), ok=False,
                duration_ms=round((time.perf_counter() - started) * 1000), error=str(exc),
            )


def build_tools(driver: BrowserDriver):
    """Create typed LangChain tools for browser actions."""
    try:
        from langchain_core.tools import tool
    except ImportError as exc:
        raise RuntimeError("Install backend dependencies before running the E2E agent") from exc

    @tool
    def open_page(path: str) -> str:
        """Open an application path and return the browser result."""
        target = path if path.startswith("http") else f"{driver.base_url}/{path.lstrip('/')}"
        return driver.run("open-page", "open", target, screenshot=True).model_dump_json()

    @tool
    def snapshot(reason: str = "") -> str:
        """Capture interactive page elements and their current refs."""
        return driver.run("snapshot", "snapshot", "-i").model_dump_json()

    @tool
    def click(ref_or_locator: str) -> str:
        """Click an agent-browser ref such as @e1 or a semantic locator expression."""
        args = ["click", ref_or_locator] if ref_or_locator.startswith("@") else ["find", "text", ref_or_locator, "click"]
        return driver.run("click", *args).model_dump_json()

    @tool
    def fill(locator: str, value: str) -> str:
        """Fill a form field by label, placeholder, CSS selector, or browser ref."""
        args = ["fill", locator, value] if locator.startswith("@") else ["find", "label", locator, "fill", value]
        return driver.run("fill", *args).model_dump_json()

    @tool
    def wait_for(target: str) -> str:
        """Wait for a URL pattern, selector/ref, or milliseconds."""
        args = ["wait", "--url", target] if target.startswith("**/") else ["wait", target]
        return driver.run("wait", *args).model_dump_json()

    @tool
    def read_page(reason: str = "") -> str:
        """Read visible page text for assertions and report evidence."""
        return driver.run("read-page", "get", "text", "body").model_dump_json()

    @tool
    def capture_screenshot(name: str = "manual") -> str:
        """Capture a named screenshot artifact."""
        return driver.run(name, "screenshot", str(driver.artifacts / f"{name}.png")).model_dump_json()

    @tool
    def upload_file(ref_or_locator: str, file_path: str) -> str:
        """Upload an explicitly allowed PDF fixture through a file input."""
        candidate = Path(file_path).expanduser().resolve()
        if candidate.suffix.lower() != ".pdf":
            return json.dumps({"ok": False, "error": "Only PDF test fixtures are allowed"})
        fixture_root = Path(os.getenv("E2E_FIXTURE_DIR", "e2e-fixtures")).resolve()
        allowed_files = {
            Path(item).expanduser().resolve()
            for item in os.getenv("E2E_ALLOWED_FILES", "").split(os.pathsep)
            if item.strip()
        }
        is_under_fixture_root = candidate == fixture_root or fixture_root in candidate.parents
        if not candidate.is_file() or (not is_under_fixture_root and candidate not in allowed_files):
            return json.dumps({"ok": False, "error": "Fixture is not in E2E_FIXTURE_DIR or E2E_ALLOWED_FILES"})
        args = ["upload", ref_or_locator, str(candidate)]
        return driver.run("upload-file", *args, screenshot=True).model_dump_json()

    @tool
    def fill_configured_secret(locator: str, secret_name: str = "E2E_STATEMENT_PASSWORD") -> str:
        """Fill a browser field from an E2E environment secret without returning the secret."""
        secret = os.getenv(secret_name, "")
        if not secret:
            return json.dumps({"ok": False, "error": f"Missing configured secret: {secret_name}"})
        attempts = [["fill", locator, secret]] if locator.startswith("@") else [
            ["find", "label", locator, "fill", secret],
            ["find", "placeholder", locator, "fill", secret],
        ]
        last_evidence = None
        for args in attempts:
            evidence = driver.run("fill-configured-secret", *args)
            last_evidence = evidence
            if evidence.ok:
                evidence.output = "configured secret submitted"
                evidence.error = None
                return evidence.model_dump_json()
        last_evidence.output = ""
        return last_evidence.model_dump_json()

    @tool
    def verify_latest_backend_state(reason: str = "") -> str:
        """Verify latest upload persistence/enrichment through authenticated APIs without exposing financial rows."""
        script = r"""(async () => {
          const token = localStorage.getItem('access_token');
          const apiRequest = performance.getEntriesByType('resource').map(e => e.name).reverse()
            .find(url => url.includes('/process-statement') || url.includes('/statements'));
          if (!token || !apiRequest) return JSON.stringify({ok:false,error:'No authenticated API request was observed'});
          const origin = new URL(apiRequest).origin;
          const headers = {Authorization: `Bearer ${token}`};
          const listResponse = await fetch(`${origin}/statements/`, {headers});
          if (!listResponse.ok) return JSON.stringify({ok:false,error:`Statements API ${listResponse.status}`});
          const listBody = await listResponse.json();
          const statements = listBody.statements || listBody || [];
          if (!statements.length) return JSON.stringify({ok:false,error:'No persisted statement found'});
          const latest = statements[0];
          const uploadId = latest.upload_id;
          const [statusResponse, detailResponse] = await Promise.all([
            fetch(`${origin}/background-status/${encodeURIComponent(uploadId)}`, {headers}),
            fetch(`${origin}/statement/${encodeURIComponent(uploadId)}`, {headers})
          ]);
          const status = await statusResponse.json();
          const detail = await detailResponse.json();
          const count = (detail.transactions || []).length;
          return JSON.stringify({
            ok: statusResponse.ok && detailResponse.ok && status.db_save_completed === true && count > 0,
            upload_id: uploadId,
            persisted_transactions: count,
            status: status.status,
            db_save_completed: status.db_save_completed,
            insights_completed: status.insights_completed,
            vector_index_completed: status.vector_index_completed,
            all_tasks_completed: status.all_tasks_completed,
            error: status.error || null
          });
        })()"""
        return driver.run("verify-latest-backend-state", "eval", script, screenshot=True).model_dump_json()

    return [
        open_page, snapshot, click, fill, wait_for, read_page,
        capture_screenshot, upload_file, fill_configured_secret,
        verify_latest_backend_state,
    ]


def create_agent(driver: BrowserDriver):
    """Build the LangChain agent using the current project's hosted LLM router."""
    try:
        from app.llm_provider import build_chat_llm
        from app.config import settings
    except ImportError as exc:
        raise RuntimeError("Run this command from backend with the project dependencies installed") from exc

    system = """You are the Financial Statement Analyzer E2E test agent.
Use browser tools only. Re-snapshot after every navigation or DOM change because refs expire.
Test each scenario in order and collect evidence. Never invent a success: a scenario passes
only when the visible UI, URL, and expected response are confirmed. Record the first broken
boundary and continue with independent scenarios. Use only the supplied dedicated E2E account
and explicitly allowed fixture PDFs; never use any other personal or financial data. Never repeat
credentials or PDF passwords in the final summary.

Application-specific scenarios:
1. Public login page renders; signup navigation works; protected pages redirect unauthenticated users.
   Confirm that no Google sign-in control or Google OAuth prompt is present.
2. With supplied test credentials, use fill_configured_secret for E2E_TEST_EMAIL and
   E2E_TEST_PASSWORD, then login and confirm the authenticated dashboard.
3. Dashboard, statements, analytics, transactions, corrections, and chat pages render without console-visible errors.
4. Upload workflow shows validation for a non-PDF and starts processing for a supplied test PDF.
   Use fill_configured_secret for E2E_STATEMENT_PASSWORD; never type or repeat the value directly.
5. Processing status/logs update and statement results show transactions, categories, totals, and balances.
   "Transactions Saved" is only an intermediate success. Call verify_latest_backend_state after upload,
   and do not report full success unless Mongo persistence has a positive transaction count. Full
   enrichment succeeds only when insights_completed, vector_index_completed, and all_tasks_completed are true.
6. Transaction filters and category correction update the visible row and persist after refresh.
7. Chat accepts a safe transaction query and renders a response or a clear backend error state.
8. Logout clears the session and protected routes redirect to login.

Use semantic locators when stable and screenshots at scenario boundaries. Finish with a concise
JSON-like summary in your final message including passed, failed, blocked, evidence, and fixes.
"""
    model = build_chat_llm(settings.GEMINI_MODEL, temperature=0)
    tools = build_tools(driver)
    try:
        from langchain.agents import create_agent
        return create_agent(model=model, tools=tools, system_prompt=system)
    except ImportError:
        # Compatibility for older lockfiles that still expose the LangGraph API.
        from langgraph.prebuilt import create_react_agent
        return create_react_agent(model, tools, prompt=system)


def _usage_metrics(result: Any) -> Dict[str, Any]:
    """Extract provider usage when the selected LangChain integration exposes it."""
    metrics = {"llm_calls": 0, "input_tokens": 0, "output_tokens": 0,
               "estimated_cost_usd": 0.0, "fallback_count": 0}
    messages = result.get("messages", []) if isinstance(result, dict) else []
    for message in messages:
        if getattr(message, "type", "") not in {"ai", "assistant"}:
            continue
        metrics["llm_calls"] += 1
        usage = getattr(message, "usage_metadata", None) or {}
        response_usage = getattr(message, "response_metadata", {}).get("token_usage", {})
        metrics["input_tokens"] += int(usage.get("input_tokens", response_usage.get("prompt_tokens", 0)) or 0)
        metrics["output_tokens"] += int(usage.get("output_tokens", response_usage.get("completion_tokens", 0)) or 0)
    return metrics


def run_public_smoke(driver: BrowserDriver, report: E2EReport) -> bool:
    """Run provider-independent public checks so a bad LLM key cannot hide UI regressions."""
    steps = [
        ("public-login", ("open", f"{driver.base_url}/login"), True),
        ("public-login-snapshot", ("snapshot", "-i"), False),
        ("signup-navigation", ("find", "text", "Sign up for free →", "click"), False),
        ("signup-url", ("get", "url"), False),
        ("signup-snapshot", ("snapshot", "-i"), False),
        ("protected-route-redirect", ("open", f"{driver.base_url}/dashboard"), False),
        ("protected-route-settle", ("wait", "500"), False),
        ("protected-login-url", ("get", "url"), False),
    ]
    all_ok = True
    for step, args, screenshot in steps:
        evidence = driver.run(step, *args, screenshot=screenshot)
        report.evidence.append(evidence)
        if evidence.ok and step in {"public-login-snapshot", "signup-snapshot"}:
            google_markers = ("sign in with google", "continue with google", "google oauth", "google login")
            if any(marker in evidence.output.lower() for marker in google_markers):
                evidence.ok = False
                evidence.error = "Google authentication UI is still present"
        if evidence.ok and step == "signup-url" and "/signup" not in evidence.output:
            evidence.ok = False
            evidence.error = f"Expected signup URL, got: {evidence.output}"
        if evidence.ok and step == "protected-login-url" and "/login" not in evidence.output:
            evidence.ok = False
            evidence.error = f"Expected login redirect, got: {evidence.output}"
        if not evidence.ok:
            all_ok = False
            report.issues.append(f"Public smoke check failed at {step}: {evidence.error or evidence.output}")
    return all_ok


def run(base_url: str, email: str = "", password: str = "", statement: str = "", smoke_only: bool = False) -> E2EReport:
    run_id = uuid.uuid4().hex
    artifacts = Path(os.getenv("E2E_ARTIFACT_DIR", "e2e-artifacts")) / run_id
    driver = BrowserDriver(base_url, artifacts)
    report = E2EReport(
        run_id=run_id, base_url=base_url, started_at=datetime.now(timezone.utc).isoformat(),
        scenarios=["public-auth", "protected-navigation", "dashboard", "upload-processing",
                   "transactions-corrections", "chat-rag", "logout"],
    )
    credentials = "Test credentials are available." if email and password else "No credentials supplied; stop at public/protected checks."
    statement_note = f"Use this test fixture if present: {statement}" if statement else "No statement fixture supplied; validate upload UI only."
    prompt = f"Run the complete application E2E suite against {base_url}. {credentials} {statement_note}"
    try:
        if email:
            os.environ["E2E_TEST_EMAIL"] = email
        if password:
            os.environ["E2E_TEST_PASSWORD"] = password
        if statement:
            resolved_statement = str(Path(statement).expanduser().resolve())
            os.environ["E2E_STATEMENT_PATH"] = resolved_statement
            allowed = [item for item in os.getenv("E2E_ALLOWED_FILES", "").split(os.pathsep) if item]
            if resolved_statement not in allowed:
                os.environ["E2E_ALLOWED_FILES"] = os.pathsep.join([*allowed, resolved_statement])
        if not shutil.which(driver.binary) and not Path(driver.binary).is_file():
            report.status = "blocked"
            report.issues.append(f"Browser CLI not found: {driver.binary}")
            report.recommendations.append("Install agent-browser or set AGENT_BROWSER_BIN to its executable path.")
            return report
        smoke_ok = run_public_smoke(driver, report)
        if smoke_only:
            report.status = "completed" if smoke_ok else "failed"
            if not email or not password:
                report.recommendations.append("Provide dedicated E2E_TEST_EMAIL and E2E_TEST_PASSWORD for authenticated scenarios.")
            return report
        agent = create_agent(driver)
        result = agent.invoke({"messages": [{"role": "user", "content": prompt}]}, config={"recursion_limit": 80})
        report.evidence.append(Evidence(step="agent-summary", action="langchain-agent", ok=True, output=str(result)[-12000:]))
        report.metrics.update(_usage_metrics(result))
        report.metrics["trace_url"] = os.getenv("LANGCHAIN_TRACE_URL")
        report.status = "completed"
    except Exception as exc:
        report.status = "blocked" if "agent-browser" in str(exc).lower() else "failed"
        report.evidence.append(Evidence(
            step="agent-bootstrap", action="langchain-agent", ok=False, error=str(exc)
        ))
        report.issues.append(str(exc))
        if "api key" in str(exc).lower() or "provider" in str(exc).lower():
            report.status = "blocked"
            report.recommendations.append(
                "Configure a valid GEMINI_API_KEY, or configure GROQ_API_KEY for the Gemini-to-Groq fallback, then rerun."
            )
    finally:
        report.completed_at = datetime.now(timezone.utc).isoformat()
        (artifacts / "report.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Financial Statement Analyzer LangChain E2E agent")
    parser.add_argument("--base-url", default=os.getenv("E2E_BASE_URL", "http://localhost:3001"))
    parser.add_argument("--email", default=os.getenv("E2E_TEST_EMAIL", ""))
    parser.add_argument("--password", default=os.getenv("E2E_TEST_PASSWORD", ""))
    parser.add_argument("--statement", default=os.getenv("E2E_STATEMENT_PATH", ""))
    parser.add_argument("--smoke-only", action="store_true", help="Run deterministic public browser checks without an LLM provider")
    args = parser.parse_args()
    report = run(args.base_url, args.email, args.password, args.statement, args.smoke_only)
    print(json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
