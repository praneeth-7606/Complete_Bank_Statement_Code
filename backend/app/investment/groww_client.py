"""
Groww REST API Client
---------------------
Direct HTTP client for Groww Trading API v1.
Automatically refreshes the access token on 401 responses.
"""
import logging
from typing import Any, Dict, Optional

import httpx

from .auth import groww_auth

logger = logging.getLogger(__name__)
BASE_URL = "https://api.groww.in/v1"


class GrowwClient:
    def __init__(self):
        self._token: Optional[str] = None

    async def _get_headers(self) -> Dict[str, str]:
        if not self._token:
            self._token = await groww_auth.get_token()
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "X-API-VERSION": "1.0",
        }

    async def _get(self, path: str) -> Dict[str, Any]:
        """GET with auto-retry on 401 (token expired) and comprehensive error handling."""
        url = f"{BASE_URL}{path}"
        for attempt in range(2):
            try:
                headers = await self._get_headers()
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(url, headers=headers)

                if resp.status_code == 401 and attempt == 0:
                    logger.info("Groww 401 — refreshing token and retrying...")
                    await groww_auth.invalidate()
                    self._token = None
                    continue

                if resp.status_code == 404:
                    logger.error(f"Groww API 404 for {path} - endpoint not found")
                    return {"error": f"Endpoint not found: {path}", "status_code": 404}

                if resp.status_code == 429:
                    logger.error(f"Groww API rate limit exceeded for {path}")
                    return {"error": "Rate limit exceeded. Please try again later.", "status_code": 429}

                if resp.status_code >= 500:
                    logger.error(f"Groww API server error {resp.status_code} for {path}")
                    return {"error": "Groww server error. Please try again later.", "status_code": resp.status_code}

                if resp.status_code != 200:
                    error_text = resp.text[:300]
                    logger.error(f"Groww API error {resp.status_code} for {path}: {error_text}")
                    return {"error": f"API error: {error_text}", "status_code": resp.status_code}

                return resp.json()
                
            except httpx.TimeoutException:
                logger.error(f"Timeout calling Groww API {path}")
                return {"error": "Request timeout. Please try again.", "status_code": 408}
            
            except httpx.NetworkError as e:
                logger.error(f"Network error calling Groww API {path}: {e}")
                return {"error": "Network error. Please check your connection.", "status_code": 503}
            
            except Exception as e:
                logger.error(f"Unexpected error calling Groww API {path}: {e}")
                return {"error": f"Unexpected error: {str(e)}", "status_code": 500}
        
        return {"error": "Authentication failed after retry", "status_code": 401}

    # ── Groww API methods ─────────────────────────────────────────────────

    # Portfolio & Positions
    async def get_holdings(self) -> Dict[str, Any]:
        """Fetch equity holdings (portfolio)."""
        return await self._get("/holdings/user")

    async def get_positions(self, segment: str = "CASH") -> Dict[str, Any]:
        """Fetch intraday positions. segment: CASH, FNO, COMMODITY"""
        return await self._get(f"/positions/user?segment={segment}")

    async def get_position_by_symbol(self, trading_symbol: str, segment: str = "CASH") -> Dict[str, Any]:
        """Get position for specific instrument."""
        return await self._get(f"/positions/trading-symbol?trading_symbol={trading_symbol}&segment={segment}")

    # Margin & Funds
    async def get_funds(self) -> Dict[str, Any]:
        """Fetch margin/funds availability."""
        return await self._get("/margins/detail/user")

    # Orders
    async def get_orders(self, segment: str = None, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Fetch order book. segment: CASH, FNO, COMMODITY"""
        params = f"?page={page}&page_size={page_size}"
        if segment:
            params += f"&segment={segment}"
        return await self._get(f"/order/list{params}")

    async def get_order_status(self, groww_order_id: str, segment: str = "CASH") -> Dict[str, Any]:
        """Get order status by Groww order ID."""
        return await self._get(f"/order/status/{groww_order_id}?segment={segment}")

    async def get_order_detail(self, groww_order_id: str, segment: str = "CASH") -> Dict[str, Any]:
        """Get detailed order information."""
        return await self._get(f"/order/detail/{groww_order_id}?segment={segment}")

    async def get_order_trades(self, groww_order_id: str, segment: str = "CASH", page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Get all trades for an order."""
        return await self._get(f"/order/trades/{groww_order_id}?segment={segment}&page={page}&page_size={page_size}")

    # Live Market Data
    async def get_live_quote(self, exchange: str, trading_symbol: str, segment: str = "CASH") -> Dict[str, Any]:
        """Get complete live quote with depth, OHLC, volume. e.g. exchange=NSE, trading_symbol=RELIANCE, segment=CASH"""
        return await self._get(f"/live-data/quote?exchange={exchange}&trading_symbol={trading_symbol}&segment={segment}")

    async def get_ltp(self, segment: str, exchange_symbols: list) -> Dict[str, Any]:
        """Get last traded price for multiple symbols. exchange_symbols: ['NSE_RELIANCE', 'BSE_SENSEX']"""
        from urllib.parse import quote
        symbols_str = " ".join(exchange_symbols)
        # URL encode the space-separated symbols
        encoded_symbols = quote(symbols_str)
        return await self._get(f"/live-data/ltp?segment={segment}&exchange_symbols={encoded_symbols}")

    async def get_ohlc(self, segment: str, exchange_symbols: list) -> Dict[str, Any]:
        """Get OHLC for multiple symbols. exchange_symbols: ['NSE_RELIANCE', 'NSE_INFY']"""
        from urllib.parse import quote
        symbols_str = " ".join(exchange_symbols)
        encoded_symbols = quote(symbols_str)
        return await self._get(f"/live-data/ohlc?segment={segment}&exchange_symbols={encoded_symbols}")

    async def get_option_chain(self, exchange: str, underlying: str, expiry_date: str) -> Dict[str, Any]:
        """Get option chain with Greeks. expiry_date: YYYY-MM-DD"""
        return await self._get(f"/option-chain/exchange/{exchange}/underlying/{underlying}?expiry_date={expiry_date}")

    async def get_greeks(self, exchange: str, underlying: str, trading_symbol: str, expiry: str) -> Dict[str, Any]:
        """Get Greeks for FNO contract. expiry: YYYY-MM-DD"""
        return await self._get(f"/live-data/greeks/exchange/{exchange}/underlying/{underlying}/trading_symbol/{trading_symbol}/expiry/{expiry}")

    # Historical Data
    async def get_historical_candles(self, exchange: str, segment: str, trading_symbol: str, 
                                     start_time: str, end_time: str, interval_in_minutes: int = 1) -> Dict[str, Any]:
        """Get historical candle data. start_time/end_time: 'YYYY-MM-DD HH:mm:ss' or epoch seconds"""
        return await self._get(
            f"/historical/candle/range?exchange={exchange}&segment={segment}&trading_symbol={trading_symbol}"
            f"&start_time={start_time}&end_time={end_time}&interval_in_minutes={interval_in_minutes}"
        )

    # User Profile
    async def get_profile(self) -> Dict[str, Any]:
        """Fetch user profile."""
        return await self._get("/user/detail")


# Singleton
groww_client = GrowwClient()
