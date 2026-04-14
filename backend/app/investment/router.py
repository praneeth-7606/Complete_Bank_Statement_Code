import logging
from fastapi import APIRouter, Depends, HTTPException

from .pipeline import run_investment_pipeline
from .. import models, auth_utils

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/investment", tags=["Investment"])


@router.post("/chat")
async def investment_chat(
    query: models.ChatQuery,
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    """
    Investment & brokerage queries via Groww MCP.

    Response modes (see `data.mode`):
      - mcp_agent                     : live data via Groww MCP tools
      - llm_fallback_not_configured   : MCP not set up in .env
      - llm_fallback_connection_failed: MCP configured but server unreachable
      - llm_fallback_no_tools         : MCP connected but returned no tools
    """
    user_id = str(current_user.user_id)
    logger.info(f"Investment chat | user={user_id} | query={query.query[:80]}")

    result = await run_investment_pipeline(query=query.query, user_id=user_id)

    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("error", "Unknown error"))

    return {"status": "success", "data": result}


@router.post("/clear-history")
async def clear_conversation_history(
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    """Clear conversation history for the current user."""
    from .pipeline import conversation_memory
    
    user_id = str(current_user.user_id)
    conversation_memory.clear_history(user_id)
    logger.info(f"Cleared conversation history | user={user_id}")
    
    return {"status": "success", "message": "Conversation history cleared"}


@router.get("/memory-stats")
async def get_memory_stats(
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    """Get conversation memory statistics (admin only)."""
    from .pipeline import conversation_memory
    
    stats = conversation_memory.get_stats()
    return {"status": "success", "data": stats}
