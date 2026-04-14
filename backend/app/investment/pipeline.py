"""
Investment pipeline — Groww REST API via LangChain tools
---------------------------------------------------------
Flow: classify intent → fetch Groww access token (TOTP) → run agent with tools
      Falls back to plain LLM if token fetch fails.
"""
import asyncio
import json
import logging
from typing import Any, Dict, List

from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from .groww_client import groww_client
from .response_formatter import investment_formatter
from .memory import conversation_memory
from ..config import settings

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════════
# INTENT CLASSIFIER (keyword-based, fast)
# ════════════════════════════════════════════════════════════════════════════

INTENT_KEYWORDS: Dict[str, List[str]] = {
    "portfolio":   ["portfolio", "holdings", "my stocks", "demat", "shares", "investments", "p&l", "profit", "loss", "pnl"],
    "positions":   ["positions", "intraday", "today's trades", "open positions"],
    "live_price":  ["price", "ltp", "quote", "rate", "market", "live", "current price", "stock price"],
    "orders":      ["order", "buy", "sell", "trade", "cancel", "modify", "order status", "order book"],
    "margin":      ["margin", "funds", "available cash", "balance", "buying power"],
    "profile":     ["profile", "account", "user", "ucc", "exchange access"],
    "historical":  ["historical", "chart", "candle", "past data", "history"],
    "options":     ["option chain", "greeks", "delta", "theta", "vega", "call", "put", "f&o", "fno", "derivatives"],
}


def _classify_intent(query: str) -> str:
    q = query.lower()
    for intent, keywords in INTENT_KEYWORDS.items():
        if any(kw in q for kw in keywords):
            return intent
    return "general"


# ════════════════════════════════════════════════════════════════════════════
# LANGCHAIN TOOLS (call Groww REST API)
# ════════════════════════════════════════════════════════════════════════════

@tool
async def get_portfolio() -> str:
    """Get the user's equity holdings and portfolio from Groww with live P&L calculation."""
    data = await groww_client.get_holdings()
    return await investment_formatter.format_holdings_with_pnl(data)


@tool
async def get_portfolio_summary() -> str:
    """Get quick portfolio summary without detailed breakdown."""
    data = await groww_client.get_holdings()
    return investment_formatter.format_holdings(data)


@tool
async def get_positions() -> str:
    """Get current intraday positions from Groww with P&L analysis."""
    data = await groww_client.get_positions()
    return investment_formatter.format_positions(data)


@tool
async def get_position_by_symbol(trading_symbol: str, segment: str = "CASH") -> str:
    """Get position for a specific stock. trading_symbol: RELIANCE, segment: CASH/FNO"""
    data = await groww_client.get_position_by_symbol(trading_symbol, segment)
    return investment_formatter.format_positions(data)


@tool
async def get_funds() -> str:
    """Get available margin, funds, and cash balance from Groww."""
    data = await groww_client.get_funds()
    return investment_formatter.format_funds(data)


@tool
async def get_orders(segment: str = None) -> str:
    """Get the order book (all recent orders) from Groww. segment: CASH, FNO, COMMODITY or None for all"""
    data = await groww_client.get_orders(segment=segment)
    return investment_formatter.format_orders(data)


@tool
async def get_order_status(groww_order_id: str, segment: str = "CASH") -> str:
    """Get status of a specific order by Groww order ID."""
    data = await groww_client.get_order_status(groww_order_id, segment)
    return json.dumps(data, indent=2)


@tool
async def get_live_quote(exchange: str, trading_symbol: str) -> str:
    """Get live market price with OHLC and depth. exchange=NSE/BSE, trading_symbol=RELIANCE (without -EQ suffix)."""
    data = await groww_client.get_live_quote(exchange, trading_symbol, "CASH")
    return investment_formatter.format_live_quote(data, f"{exchange}:{trading_symbol}")


@tool
async def get_ltp_multiple(symbols: str) -> str:
    """Get last traded prices for multiple stocks. symbols: comma-separated like 'NSE_RELIANCE,NSE_INFY,NSE_TCS'"""
    symbol_list = [s.strip() for s in symbols.split(",")]
    data = await groww_client.get_ltp("CASH", symbol_list)
    return investment_formatter.format_ltp(data)


@tool
async def get_ohlc_multiple(symbols: str) -> str:
    """Get OHLC data for multiple stocks. symbols: comma-separated like 'NSE_RELIANCE,NSE_INFY'"""
    symbol_list = [s.strip() for s in symbols.split(",")]
    data = await groww_client.get_ohlc("CASH", symbol_list)
    return json.dumps(data, indent=2)


@tool
async def get_profile() -> str:
    """Get the user's Groww account profile and personal details."""
    data = await groww_client.get_profile()
    return investment_formatter.format_profile(data)


@tool
async def get_historical_data(exchange: str, trading_symbol: str, start_time: str, end_time: str, interval: int = 1) -> str:
    """Get historical candle data. start_time/end_time: 'YYYY-MM-DD HH:mm:ss', interval: minutes (1,5,10,60,240,1440)"""
    data = await groww_client.get_historical_candles(exchange, "CASH", trading_symbol, start_time, end_time, interval)
    return json.dumps(data, indent=2)


@tool
async def get_option_chain(exchange: str, underlying: str, expiry_date: str) -> str:
    """Get option chain with Greeks for F&O. exchange: NSE/BSE, underlying: NIFTY/BANKNIFTY, expiry_date: YYYY-MM-DD"""
    data = await groww_client.get_option_chain(exchange, underlying, expiry_date)
    return json.dumps(data, indent=2)


@tool
async def get_greeks(exchange: str, underlying: str, trading_symbol: str, expiry: str) -> str:
    """Get Greeks for F&O contract. exchange: NSE, underlying: NIFTY, trading_symbol: NIFTY25APR24100PE, expiry: YYYY-MM-DD"""
    data = await groww_client.get_greeks(exchange, underlying, trading_symbol, expiry)
    return json.dumps(data, indent=2)


GROWW_TOOLS = [
    get_portfolio, 
    get_portfolio_summary,
    get_positions, 
    get_position_by_symbol,
    get_funds, 
    get_orders, 
    get_order_status,
    get_live_quote, 
    get_ltp_multiple, 
    get_ohlc_multiple,
    get_profile, 
    get_historical_data,
    get_option_chain,
    get_greeks
]


# ════════════════════════════════════════════════════════════════════════════
# LLM + AGENT
# ════════════════════════════════════════════════════════════════════════════

def _build_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=settings.GEMINI_API_KEY,
        temperature=0,
    )


def _build_agent(tools: list, llm, conversation_context: str = ""):
    from langchain.agents import AgentExecutor, create_tool_calling_agent
    from langchain_core.prompts import ChatPromptTemplate

    system_message = (
        "You are a professional Groww Investment Assistant and Financial Analyst. "
        "Use the available tools to fetch REAL live data from the user's Groww account. "
        "The tools already return beautifully formatted data - present it directly to the user. "
        "Never fabricate prices or holdings. "
        "Format numbers in INR (₹). Use Indian market context (NSE/BSE, SEBI rules). "
        "Be concise and professional like a financial analyst."
    )
    
    if conversation_context:
        system_message += f"\n\n{conversation_context}"
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True,
                         handle_parsing_errors=True, max_iterations=6)


# ════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ════════════════════════════════════════════════════════════════════════════

async def run_investment_pipeline(query: str, user_id: str) -> Dict[str, Any]:
    """
    Returns: {answer, source, intent, status}
    source = "groww_api" | "llm_fallback"
    """
    intent = _classify_intent(query)
    logger.info("Investment plan | intent=%s | user=%s", intent, user_id)

    # Add user query to memory
    conversation_memory.add_message(user_id, "user", query)
    
    # Get conversation context
    conversation_context = conversation_memory.get_formatted_history(user_id, last_n=5)

    llm = _build_llm()

    # ── Try Groww REST API path ───────────────────────────────────────────
    try:
        # Verify token is available before building agent
        from .auth import groww_auth
        token = await groww_auth.get_token()

        if token:
            agent_executor = _build_agent(GROWW_TOOLS, llm, conversation_context)
            result = await agent_executor.ainvoke({"input": query})
            answer = result.get("output", "")
            
            # Add assistant response to memory
            conversation_memory.add_message(user_id, "assistant", answer)
            
            return {
                "answer": answer,
                "source": "groww_api",
                "intent": intent,
                "status": "success",
            }
        else:
            logger.warning("No Groww access token — using LLM fallback.")

    except Exception as exc:
        logger.warning("Groww API path failed (%s) — using LLM fallback.", exc)

    # ── LLM-only fallback ─────────────────────────────────────────────────
    fallback_prompt = (
        f"The user asked about their Groww investments: {query}\n\n"
        "You do not have access to their live account right now (authentication failed). "
        "Clearly state this limitation, then answer as helpfully as possible "
        "using general investment knowledge and Indian market context."
    )
    
    if conversation_context:
        fallback_prompt = f"{conversation_context}\n\n{fallback_prompt}"
    
    response = await llm.ainvoke([HumanMessage(content=fallback_prompt)])
    answer = response.content
    
    # Add assistant response to memory
    conversation_memory.add_message(user_id, "assistant", answer)
    
    return {
        "answer": answer,
        "source": "llm_fallback",
        "intent": intent,
        "status": "success",
    }