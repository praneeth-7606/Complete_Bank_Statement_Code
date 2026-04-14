"""
Groww Token Manager
-------------------
Flow: GROWW_API_KEY (Bearer) + TOTP code → access_token

The GROWW_API_KEY is the API key used in the Authorization header.
The GROWW_API_SECRET is the TOTP secret used with pyotp to generate OTP.
The resulting access_token is used for all Groww REST API calls.
"""
import asyncio
import logging
import datetime
from typing import Optional

import httpx
import pyotp

from ..config import settings

logger = logging.getLogger(__name__)

AUTH_URL = "https://api.groww.in/v1/token/api/access"
_TOKEN_BUFFER_SECONDS = 300          # refresh 5 mins before expiry
_DEFAULT_LIFETIME_SECONDS = 86400    # assume 24h if API doesn't say


class GrowwAuthClient:
    """Thread-safe, auto-refreshing Groww access token manager."""

    def __init__(self):
        self.access_token: Optional[str] = None
        self._expires_at: Optional[datetime.datetime] = None
        self._lock = asyncio.Lock()

    # ── public API ─────────────────────────────────────────────────────────

    async def get_token(self) -> Optional[str]:
        """Return a valid access token, refreshing if needed."""
        async with self._lock:
            if self._is_valid():
                return self.access_token
            return await self._fetch()

    async def invalidate(self):
        """Force a refresh on the next call."""
        async with self._lock:
            self.access_token = None
            self._expires_at = None

    # ── internal ───────────────────────────────────────────────────────────

    def _is_valid(self) -> bool:
        if not self.access_token:
            return False
        if not self._expires_at:
            return True
        buffer = datetime.timedelta(seconds=_TOKEN_BUFFER_SECONDS)
        return datetime.datetime.utcnow() < (self._expires_at - buffer)

    def _generate_totp(self) -> Optional[str]:
        """Generate current TOTP from GROWW_API_SECRET."""
        secret = settings.GROWW_API_SECRET
        if not secret:
            logger.info("GROWW_API_SECRET not set — cannot generate TOTP.")
            return None
        try:
            totp = pyotp.TOTP(secret)
            code = totp.now()
            logger.info(f"Generated TOTP code successfully")
            return code
        except Exception as e:
            logger.error(f"TOTP generation failed: {e}")
            return None

    async def _fetch(self) -> Optional[str]:
        """Hit Groww auth API and cache the token."""
        api_key = settings.GROWW_API_KEY
        if not api_key:
            logger.info("GROWW_API_KEY not set — using LLM fallback.")
            return None

        totp = self._generate_totp()
        if not totp:
            logger.info("TOTP not available — using LLM fallback.")
            return None

        logger.info(f"Fetching Groww access token from {AUTH_URL} ...")
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    AUTH_URL,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "X-API-VERSION": "1.0"
                    },
                    json={"key_type": "totp", "totp": totp},
                )

            if response.status_code == 200:
                data = response.json()
                
                # Check if response has status field indicating failure
                if data.get("status") == "FAILURE":
                    logger.error(f"Groww auth failed: {data.get('error', 'Unknown error')}")
                    return None
                
                # Token can be at root level or in payload
                self.access_token = data.get("token") or data.get("payload", {}).get("token")
                
                if not self.access_token:
                    logger.error(f"No token in response")
                    return None
                
                # Calculate expiry
                expiry_str = data.get("expiry") or data.get("payload", {}).get("expiry")
                if expiry_str:
                    try:
                        self._expires_at = datetime.datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
                    except:
                        self._expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=_DEFAULT_LIFETIME_SECONDS)
                else:
                    self._expires_at = datetime.datetime.utcnow() + datetime.timedelta(seconds=_DEFAULT_LIFETIME_SECONDS)
                
                logger.info("✅ Groww auth successful!")
                return self.access_token
            else:
                logger.error(
                    f"Groww auth failed: HTTP {response.status_code} — "
                    f"{response.text[:300]}"
                )
                self.access_token = None
                self._expires_at = None
                return None

        except httpx.TimeoutException:
            logger.error("Groww auth request timed out.")
            return None
        except Exception as e:
            logger.error(f"Unexpected Groww auth error: {e}", exc_info=True)
            return None


# Module-level singleton
groww_auth = GrowwAuthClient()
