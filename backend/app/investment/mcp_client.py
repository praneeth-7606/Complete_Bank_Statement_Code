import asyncio
import logging
import contextlib
import os
import shutil
import subprocess
from typing import Optional, List, Dict, Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from ..config import settings

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# WHY THIS FILE WAS REWRITTEN
#
# Old command (GROWW_MCP_SERVER_COMMAND in .env):
#   uvx --from git+https://github.com/arkapravasinha/groww-mcp-server.git groww-mcp-server
#   npx @smithery/cli run arkapravasinha/groww-mcp-server
#
# Both fail because:
#   1. They download packages from internet ON EVERY REQUEST (slow + flaky)
#   2. Smithery routes through a cloud WebSocket relay (times out from India)
#   3. On Windows, npx/uvx are .cmd scripts that need `cmd /c` wrapping
#
# THE FIX: Install once locally, run directly via `node dist/index.js`
#   One-time setup:  python setup_groww_mcp.py
#   OR manually:     npm install @arkapravasinha/groww-mcp-server
#
# Connection priority:
#   1. Local node_modules (fastest, most reliable) ← PRIMARY
#   2. GROWW_MCP_SERVER_URL (SSE mode)
#   3. GROWW_MCP_SERVER_COMMAND (env fallback, slow but works)
# ─────────────────────────────────────────────────────────────────────────────

_INIT_TIMEOUT = 20.0   # seconds — local node starts in <1s, generous buffer
_MAX_RETRIES  = 1      # one retry after first failure


def _find_node() -> str:
    """Return absolute path to node.exe (cross-platform)."""
    node = shutil.which("node")
    if node:
        return node
    for candidate in [
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files (x86)\nodejs\node.exe",
    ]:
        if os.path.isfile(candidate):
            return candidate
    raise RuntimeError(
        "node.exe not found on PATH. "
        "Install Node.js 20+ from https://nodejs.org and restart your terminal."
    )


def _find_groww_server_script() -> Optional[str]:
    """
    Search for the locally installed groww-mcp-server entry point.
    Returns None if not found (caller falls back to next strategy).
    """
    base = os.path.dirname(os.path.abspath(__file__))
    for _ in range(8):  # walk up project tree
        for subdir in ["dist", "build"]:
            candidate = os.path.join(
                base, "node_modules", "@arkapravasinha",
                "groww-mcp-server", subdir, "index.js"
            )
            if os.path.isfile(candidate):
                return candidate
        base = os.path.dirname(base)

    # Try global npm root
    try:
        result = subprocess.run(
            ["npm", "root", "-g"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            global_root = result.stdout.strip()
            for subdir in ["dist", "build"]:
                candidate = os.path.join(
                    global_root, "@arkapravasinha",
                    "groww-mcp-server", subdir, "index.js"
                )
                if os.path.isfile(candidate):
                    return candidate
    except Exception:
        pass

    return None


def _build_env() -> dict:
    """Build subprocess environment with Groww credentials injected."""
    env = os.environ.copy()
    if getattr(settings, "GROWW_API_KEY", None):
        env["GROWW_API_KEY"] = settings.GROWW_API_KEY
    if getattr(settings, "GROWW_SECRET_KEY", None):
        env["GROWW_API_SECRET"] = settings.GROWW_SECRET_KEY
        env["GROWW_SECRET_KEY"] = settings.GROWW_SECRET_KEY
    return env


class GrowwMCPClient:
    """
    Manages a stdio/SSE MCP session with the Groww MCP server.
    Drop-in replacement — same interface as the original.

    Usage (unchanged):
        async with GrowwMCPClient() as client:
            if client.is_connected:
                tools = await load_mcp_tools(client.session)
    """

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self._exit_stack: Optional[contextlib.AsyncExitStack] = None
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    @property
    def is_connected(self) -> bool:
        return self.session is not None

    # ── public API (unchanged from original) ─────────────────────────────────

    async def connect(self):
        async with self._lock:
            if self.session:
                return
            for attempt in range(1, _MAX_RETRIES + 2):
                try:
                    await self._attempt_connect(attempt)
                    if self.session:
                        return
                except Exception as e:
                    logger.error(f"MCP connect attempt {attempt} failed: {e}")
                if attempt <= _MAX_RETRIES:
                    await asyncio.sleep(0.5)
            logger.warning("All MCP connect attempts failed. Using LLM fallback.")

    async def disconnect(self):
        async with self._lock:
            if self._exit_stack:
                try:
                    await self._exit_stack.aclose()
                except Exception as e:
                    logger.debug(f"MCP disconnect error (safe to ignore): {e}")
                finally:
                    self._exit_stack = None
                    self.session = None
                    logger.info("Groww MCP session closed.")

    async def list_tools(self) -> List[Any]:
        if not self.session:
            return []
        try:
            result = await self.session.list_tools()
            return result.tools
        except Exception as e:
            logger.error(f"list_tools failed: {e}")
            return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        if not self.session:
            raise RuntimeError("MCP session not connected")
        try:
            return await self.session.call_tool(name, arguments)
        except Exception as e:
            logger.error(f"call_tool({name}) failed: {e}")
            raise

    # ── internal ──────────────────────────────────────────────────────────────

    async def _attempt_connect(self, attempt: int):
        logger.info(f"MCP connect attempt {attempt}...")
        stack = contextlib.AsyncExitStack()
        session = None

        try:
            # Priority 1: local node_modules install (fast, no internet needed)
            session = await self._try_local_node(stack)

            # Priority 2: SSE URL
            if session is None:
                session = await self._try_sse(stack)

            # Priority 3: env command (slow but last resort)
            if session is None:
                session = await self._try_env_command(stack)

        except Exception:
            try:
                await stack.aclose()
            except Exception:
                pass
            raise

        if session is None:
            await stack.aclose()
            logger.warning("No MCP connection method available.")
            return

        self._exit_stack = stack
        self.session = session

    async def _init_session(self, stack, read, write) -> ClientSession:
        """Enter ClientSession and run initialize() with timeout."""
        session = await stack.enter_async_context(ClientSession(read, write))
        try:
            await asyncio.wait_for(session.initialize(), timeout=_INIT_TIMEOUT)
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"session.initialize() timed out after {_INIT_TIMEOUT}s"
            )
        return session

    async def _try_local_node(self, stack) -> Optional[ClientSession]:
        """Run the locally npm-installed server via node directly."""
        script = _find_groww_server_script()
        if not script:
            logger.info(
                "Local groww-mcp-server not installed. "
                "Run: npm install @arkapravasinha/groww-mcp-server  "
                "(in your project root, next to package.json / run.py)"
            )
            return None

        try:
            node_bin = _find_node()
        except RuntimeError as e:
            logger.warning(str(e))
            return None

        logger.info(f"Launching local Groww MCP: {node_bin} {script}")
        params = StdioServerParameters(
            command=node_bin,
            args=[script],
            env=_build_env(),
        )
        read, write = await stack.enter_async_context(stdio_client(params))
        session = await self._init_session(stack, read, write)
        logger.info("✓ Groww MCP connected via local node.")
        return session

    async def _try_sse(self, stack) -> Optional[ClientSession]:
        """Connect to official Groww MCP SSE endpoint with Bearer auth."""
        url = getattr(settings, "GROWW_MCP_SERVER_URL", "") or ""
        if not url:
            return None
        
        # The official Groww MCP (mcp.groww.in) uses Bearer token auth
        api_key = getattr(settings, "GROWW_API_KEY", "") or ""
        headers = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            logger.info("Connecting to official Groww MCP SSE with Bearer token...")
        else:
            logger.info(f"Connecting to Groww MCP SSE (no auth): {url}")

        read, write = await stack.enter_async_context(
            sse_client(url, headers=headers)
        )
        session = await self._init_session(stack, read, write)
        logger.info("Groww MCP connected via SSE (official mcp.groww.in).")
        return session

    async def _try_env_command(self, stack) -> Optional[ClientSession]:
        """
        Run GROWW_MCP_SERVER_COMMAND from .env.
        Fixed for Windows: wraps non-.exe commands with `cmd /c`.
        """
        command = getattr(settings, "GROWW_MCP_SERVER_COMMAND", "") or ""
        if not command:
            return None

        parts = command.split()
        cmd = parts[0]
        args = parts[1:]

        # On Windows, scripts like npx/uvx are .cmd files that require cmd /c
        if os.name == "nt" and not cmd.lower().endswith(".exe"):
            logger.info(f"Windows: wrapping command with cmd /c: {command}")
            params = StdioServerParameters(
                command="cmd",
                args=["/c"] + parts,
                env=_build_env(),
            )
        else:
            params = StdioServerParameters(
                command=cmd,
                args=args,
                env=_build_env(),
            )

        logger.info(f"Launching Groww MCP via env command: {command}")
        read, write = await stack.enter_async_context(stdio_client(params))
        session = await self._init_session(stack, read, write)
        logger.info("✓ Groww MCP connected via env command.")
        return session