"""
Investment Response Formatter
------------------------------
Formats Groww API responses into professional, analyst-style presentations.
"""
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class InvestmentResponseFormatter:
    """Format investment data like a financial analyst."""

    @staticmethod
    async def format_holdings_with_pnl(holdings_data: Dict[str, Any]) -> str:
        """Format portfolio holdings with live P&L calculation."""
        if "error" in holdings_data:
            return f"❌ Unable to fetch holdings: {holdings_data.get('error', 'Unknown error')}"

        payload = holdings_data.get("payload", {})
        holdings = payload.get("holdings", [])

        if not holdings:
            return "📊 Portfolio is empty. No holdings found."

        # Fetch live prices for all holdings
        from .groww_client import groww_client
        
        # Build symbol list - try NSE first (most common for equity holdings)
        symbols_to_fetch = []
        symbol_map = {}  # Map NSE_SYMBOL -> holding data
        
        for h in holdings:
            symbol = h.get("trading_symbol", "")
            if symbol:
                nse_symbol = f"NSE_{symbol}"
                symbols_to_fetch.append(nse_symbol)
                symbol_map[nse_symbol] = h
        
        # Fetch LTP for all symbols in one call (max 50 per call)
        ltp_data = {}
        if symbols_to_fetch:
            try:
                logger.info(f"Fetching LTP for {len(symbols_to_fetch)} symbols")
                # Split into batches of 50
                for i in range(0, len(symbols_to_fetch), 50):
                    batch = symbols_to_fetch[i:i+50]
                    logger.info(f"Batch {i//50 + 1}: Fetching LTP for symbols: {batch[:5]}...")  # Log first 5
                    
                    ltp_response = await groww_client.get_ltp("CASH", batch)
                    logger.info(f"LTP Response status: {ltp_response.get('status')}")
                    
                    if ltp_response.get("status") == "SUCCESS":
                        ltp_payload = ltp_response.get("payload", {})
                        logger.info(f"LTP Payload keys: {list(ltp_payload.keys())[:5] if isinstance(ltp_payload, dict) else 'Not a dict'}")
                        
                        if isinstance(ltp_payload, dict):
                            # The payload structure might be: { "NSE_SYMBOL": { "ltp": value } }
                            for symbol_key, price_data in ltp_payload.items():
                                if isinstance(price_data, dict) and "ltp" in price_data:
                                    ltp_data[symbol_key] = price_data
                                    logger.info(f"Got LTP for {symbol_key}: {price_data.get('ltp')}")
                                elif isinstance(price_data, (int, float)):
                                    # Sometimes API returns direct value
                                    ltp_data[symbol_key] = {"ltp": price_data}
                                    logger.info(f"Got direct LTP for {symbol_key}: {price_data}")
                    else:
                        error_msg = ltp_response.get('error', 'Unknown error')
                        logger.warning(f"LTP fetch failed: {error_msg}")
                        logger.warning(f"Full response: {ltp_response}")
            except Exception as e:
                logger.error(f"Failed to fetch LTP: {e}", exc_info=True)
        
        # Calculate totals
        total_investment = 0
        total_current = 0
        holdings_with_price = 0
        
        output = ["📊 PORTFOLIO HOLDINGS WITH LIVE P&L\n" + "=" * 80 + "\n"]
        
        for h in holdings:
            symbol = h.get("trading_symbol", "N/A")
            qty = h.get("quantity", 0)
            avg_price = h.get("average_price", 0)
            
            # Calculate investment
            investment = qty * avg_price
            total_investment += investment
            
            # Get live price
            nse_symbol = f"NSE_{symbol}"
            ltp = 0
            
            # Try to get from batch LTP data
            if nse_symbol in ltp_data:
                price_data = ltp_data[nse_symbol]
                if isinstance(price_data, dict):
                    ltp = price_data.get("ltp", 0)
                elif isinstance(price_data, (int, float)):
                    ltp = price_data
                
                if ltp > 0:
                    logger.info(f"Found LTP for {symbol}: ₹{ltp}")
            
            if ltp == 0:
                logger.warning(f"No LTP found for {symbol} (tried {nse_symbol})")
            
            # Calculate current value and P&L
            if ltp > 0:
                current_value = qty * ltp
                pnl = current_value - investment
                pnl_pct = (pnl / investment * 100) if investment > 0 else 0
                total_current += current_value
                holdings_with_price += 1
            else:
                current_value = investment
                pnl = 0
                pnl_pct = 0
                total_current += investment
            
            # Determine emoji
            pnl_emoji = "🟢" if pnl >= 0 else "🔴"
            
            # Format holding
            output.append(f"{pnl_emoji} {symbol}")
            output.append(f"   Quantity: {qty:,} shares")
            output.append(f"   Avg Price: ₹{avg_price:,.2f}")
            output.append(f"   Investment: ₹{investment:,.2f}")
            
            if ltp > 0:
                output.append(f"   Current Price: ₹{ltp:,.2f}")
                output.append(f"   Current Value: ₹{current_value:,.2f}")
                output.append(f"   P&L: ₹{pnl:,.2f} ({pnl_pct:+.2f}%)")
            else:
                output.append(f"   ⚠️  Live price unavailable")
            
            # Show locked quantities if any
            pledge = h.get("pledge_quantity", 0)
            if pledge > 0:
                output.append(f"   🔒 Pledged: {pledge} shares")
            
            output.append("")
        
        # Summary
        total_pnl = total_current - total_investment
        total_pnl_pct = (total_pnl / total_investment * 100) if total_investment > 0 else 0
        pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
        
        output.append("=" * 80)
        output.append(f"💰 Total Investment: ₹{total_investment:,.2f}")
        output.append(f"💵 Current Value: ₹{total_current:,.2f}")
        output.append(f"{pnl_emoji} Total P&L: ₹{total_pnl:,.2f} ({total_pnl_pct:+.2f}%)")
        output.append(f"📈 Total Holdings: {len(holdings)} stocks")
        
        if holdings_with_price < len(holdings):
            output.append(f"⚠️  Live prices available for {holdings_with_price}/{len(holdings)} stocks")
        
        return "\n".join(output)

    @staticmethod
    def format_holdings(data: Dict[str, Any]) -> str:
        """Format portfolio holdings (basic version without live prices)."""
        if "error" in data:
            return f"❌ Unable to fetch holdings: {data.get('error', 'Unknown error')}"

        payload = data.get("payload", {})
        holdings = payload.get("holdings", [])

        if not holdings:
            return "📊 Portfolio is empty. No holdings found."

        # Calculate totals
        total_investment = 0
        
        output = ["📊 PORTFOLIO HOLDINGS\n" + "=" * 80 + "\n"]
        
        for h in holdings:
            symbol = h.get("trading_symbol", "N/A")
            qty = h.get("quantity", 0)
            avg_price = h.get("average_price", 0)
            
            # Calculate investment
            investment = qty * avg_price
            total_investment += investment
            
            # Format holding
            output.append(f"🔹 {symbol}")
            output.append(f"   Quantity: {qty:,} shares")
            output.append(f"   Avg Price: ₹{avg_price:,.2f}")
            output.append(f"   Investment: ₹{investment:,.2f}")
            
            # Show locked quantities if any
            pledge = h.get("pledge_quantity", 0)
            if pledge > 0:
                output.append(f"   ⚠️  Pledged: {pledge} shares")
            
            output.append("")
        
        # Summary
        output.append("=" * 80)
        output.append(f"💰 Total Investment: ₹{total_investment:,.2f}")
        output.append(f"📈 Total Holdings: {len(holdings)} stocks")
        
        return "\n".join(output)

    @staticmethod
    def format_positions(data: Dict[str, Any]) -> str:
        """Format intraday positions with P&L."""
        if "error" in data:
            return f"❌ Unable to fetch positions: {data.get('error', 'Unknown error')}"

        payload = data.get("payload", {})
        positions = payload.get("positions", [])

        if not positions:
            return "📊 No open positions today."

        output = ["📊 TODAY'S POSITIONS\n" + "=" * 80 + "\n"]
        
        total_pnl = 0
        
        for p in positions:
            symbol = p.get("trading_symbol", "N/A")
            qty = p.get("quantity", 0)
            net_price = p.get("net_price", 0)
            realised_pnl = p.get("realised_pnl", 0)
            
            total_pnl += realised_pnl
            
            pnl_emoji = "🟢" if realised_pnl >= 0 else "🔴"
            
            output.append(f"{pnl_emoji} {symbol}")
            output.append(f"   Net Quantity: {qty:,}")
            output.append(f"   Avg Price: ₹{net_price:,.2f}")
            output.append(f"   Realised P&L: ₹{realised_pnl:,.2f}")
            output.append("")
        
        # Summary
        output.append("=" * 80)
        pnl_emoji = "🟢" if total_pnl >= 0 else "🔴"
        output.append(f"{pnl_emoji} Total Realised P&L: ₹{total_pnl:,.2f}")
        
        return "\n".join(output)

    @staticmethod
    def format_funds(data: Dict[str, Any]) -> str:
        """Format margin and funds availability."""
        if "error" in data:
            return f"❌ Unable to fetch funds: {data.get('error', 'Unknown error')}"

        payload = data.get("payload", {})
        
        output = ["💰 FUNDS & MARGIN\n" + "=" * 80 + "\n"]
        
        # Available cash
        clear_cash = payload.get("clear_cash", 0)
        net_margin_used = payload.get("net_margin_used", 0)
        collateral_available = payload.get("collateral_available", 0)
        collateral_used = payload.get("collateral_used", 0)
        adhoc_margin = payload.get("adhoc_margin", 0)
        
        output.append(f"💵 Clear Cash: ₹{clear_cash:,.2f}")
        output.append(f"📊 Net Margin Used: ₹{net_margin_used:,.2f}")
        output.append(f"💎 Collateral Available: ₹{collateral_available:,.2f}")
        output.append(f"🔒 Collateral Used: ₹{collateral_used:,.2f}")
        if adhoc_margin > 0:
            output.append(f"➕ Adhoc Margin: ₹{adhoc_margin:,.2f}")
        output.append("")
        
        # Equity margin details
        equity = payload.get("equity_margin_details", {})
        if equity:
            output.append("📈 EQUITY MARGIN:")
            output.append(f"   CNC Balance: ₹{equity.get('cnc_balance_available', 0):,.2f}")
            output.append(f"   MIS Balance: ₹{equity.get('mis_balance_available', 0):,.2f}")
            output.append("")
        
        # F&O margin details
        fno = payload.get("fno_margin_details", {})
        if fno:
            output.append("📊 F&O MARGIN:")
            output.append(f"   Future Balance: ₹{fno.get('future_balance_available', 0):,.2f}")
            output.append(f"   Option Buy: ₹{fno.get('option_buy_balance_available', 0):,.2f}")
            output.append(f"   Option Sell: ₹{fno.get('option_sell_balance_available', 0):,.2f}")
            output.append("")
        
        # Total available
        total_available = clear_cash + collateral_available
        output.append("=" * 80)
        output.append(f"💰 Total Available: ₹{total_available:,.2f}")
        
        return "\n".join(output)

    @staticmethod
    def format_orders(data: Dict[str, Any]) -> str:
        """Format order book with status indicators."""
        if "error" in data:
            return f"❌ Unable to fetch orders: {data.get('error', 'Unknown error')}"

        payload = data.get("payload", {})
        orders = payload.get("orders", [])

        if not orders:
            return "📋 No orders placed today."

        output = ["📋 ORDER BOOK\n" + "=" * 80 + "\n"]
        
        status_emoji = {
            "COMPLETE": "✅",
            "PENDING": "⏳",
            "REJECTED": "❌",
            "CANCELLED": "🚫",
            "OPEN": "🔵"
        }
        
        for o in orders:
            symbol = o.get("trading_symbol", "N/A")
            status = o.get("order_status", "UNKNOWN")
            qty = o.get("quantity", 0)
            filled = o.get("filled_quantity", 0)
            price = o.get("price", 0)
            order_type = o.get("order_type", "N/A")
            txn_type = o.get("transaction_type", "N/A")
            
            emoji = status_emoji.get(status, "⚪")
            
            output.append(f"{emoji} {symbol} | {txn_type} | {order_type}")
            output.append(f"   Status: {status}")
            output.append(f"   Quantity: {filled}/{qty} filled")
            output.append(f"   Price: ₹{price:,.2f}")
            output.append("")
        
        output.append("=" * 80)
        output.append(f"📊 Total Orders: {len(orders)}")
        
        return "\n".join(output)

    @staticmethod
    def format_live_quote(data: Dict[str, Any], symbol: str = None) -> str:
        """Format live market quote with OHLC and depth."""
        if "error" in data:
            return f"❌ Unable to fetch quote: {data.get('error', 'Unknown error')}"

        payload = data.get("payload", {})
        
        ltp = payload.get("last_price", 0)
        change = payload.get("day_change", 0)
        change_pct = payload.get("day_change_perc", 0)
        
        # OHLC
        ohlc = payload.get("ohlc", {})
        open_price = ohlc.get("open", 0)
        high = ohlc.get("high", 0)
        low = ohlc.get("low", 0)
        close = ohlc.get("close", 0)
        
        # Volume
        volume = payload.get("volume", 0)
        
        # Circuit limits
        upper = payload.get("upper_circuit_limit", 0)
        lower = payload.get("lower_circuit_limit", 0)
        
        # Determine trend
        trend_emoji = "🟢" if change >= 0 else "🔴"
        
        output = [f"📈 LIVE QUOTE: {symbol or 'Stock'}\n" + "=" * 80 + "\n"]
        
        output.append(f"{trend_emoji} LTP: ₹{ltp:,.2f}")
        output.append(f"   Change: ₹{change:,.2f} ({change_pct:+.2f}%)")
        output.append("")
        
        output.append("📊 OHLC:")
        output.append(f"   Open:  ₹{open_price:,.2f}")
        output.append(f"   High:  ₹{high:,.2f}")
        output.append(f"   Low:   ₹{low:,.2f}")
        output.append(f"   Close: ₹{close:,.2f}")
        output.append("")
        
        output.append(f"📦 Volume: {volume:,}")
        output.append("")
        
        output.append("⚠️  Circuit Limits:")
        output.append(f"   Upper: ₹{upper:,.2f}")
        output.append(f"   Lower: ₹{lower:,.2f}")
        
        return "\n".join(output)

    @staticmethod
    def format_ltp(data: Dict[str, Any]) -> str:
        """Format last traded prices for multiple symbols."""
        if "error" in data:
            return f"❌ Unable to fetch LTP: {data.get('error', 'Unknown error')}"

        payload = data.get("payload", {})
        
        if not payload:
            return "❌ No price data available."

        output = ["📈 LAST TRADED PRICES\n" + "=" * 80 + "\n"]
        
        for symbol, price_data in payload.items():
            ltp = price_data.get("ltp", 0)
            output.append(f"🔹 {symbol}: ₹{ltp:,.2f}")
        
        return "\n".join(output)

    @staticmethod
    def format_profile(data: Dict[str, Any]) -> str:
        """Format user profile information."""
        if "error" in data:
            return f"❌ Unable to fetch profile: {data.get('error', 'Unknown error')}"

        payload = data.get("payload", {})
        
        if not payload:
            return "❌ No profile data available."
        
        output = ["👤 ACCOUNT PROFILE\n" + "=" * 80 + "\n"]
        
        vendor_user_id = payload.get("vendor_user_id", "N/A")
        ucc = payload.get("ucc", "N/A")
        
        output.append(f"🆔 User ID: {vendor_user_id}")
        output.append(f"📋 UCC: {ucc}")
        output.append("")
        
        # Exchange access
        nse_enabled = payload.get("nse_enabled", False)
        bse_enabled = payload.get("bse_enabled", False)
        ddpi_enabled = payload.get("ddpi_enabled", False)
        
        output.append("🏦 EXCHANGE ACCESS:")
        output.append(f"   NSE: {'✅ Enabled' if nse_enabled else '❌ Disabled'}")
        output.append(f"   BSE: {'✅ Enabled' if bse_enabled else '❌ Disabled'}")
        output.append(f"   DDPI: {'✅ Enabled' if ddpi_enabled else '❌ Disabled'}")
        output.append("")
        
        # Active segments
        segments = payload.get("active_segments", [])
        if segments:
            output.append(f"📊 Active Segments: {', '.join(segments)}")
        
        return "\n".join(output)


# Singleton
investment_formatter = InvestmentResponseFormatter()
