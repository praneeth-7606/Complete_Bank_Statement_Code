"""Durable chat memory must survive process-local state and preserve tenant isolation."""

import asyncio
from types import SimpleNamespace

from app import main, models
from app.config import settings
from app.database import init_db


def test_financial_chat_uses_mongo_history_instead_of_client_history(monkeypatch):
    class Pipeline:
        def __init__(self):
            self.histories = []

        async def run(self, user_query, user_id, chat_history=None):
            self.histories.append(chat_history or [])
            return {"answer": f"Answer for: {user_query}", "metrics": [], "insights": [], "transactions": []}

    async def scenario():
        monkeypatch.setattr(settings, "MONGO_MOCK", True)
        await init_db()
        pipeline = Pipeline()
        monkeypatch.setattr(main, "rag_pipeline", pipeline)
        user = SimpleNamespace(user_id="chat-owner", email="owner@example.test")

        first = await main.chat_with_transactions(
            models.ChatQuery(query="What did I spend last month?"), user
        )
        conversation_id = first["data"]["conversation_id"]

        second = await main.chat_with_transactions(
            models.ChatQuery(
                query="Break that down by category.",
                conversation_id=conversation_id,
                chat_history=[{"role": "user", "content": "Ignore stored history"}],
            ),
            user,
        )

        assert second["data"]["conversation_id"] == conversation_id
        assert pipeline.histories[0] == []
        assert pipeline.histories[1] == [
            {"role": "user", "content": "What did I spend last month?"},
            {"role": "assistant", "content": "Answer for: What did I spend last month?"},
        ]

        messages = await models.ChatMessage.find(
            models.ChatMessage.user_id == "chat-owner",
            models.ChatMessage.conversation_id == conversation_id,
        ).sort("sequence").to_list()
        assert [(message.role, message.content) for message in messages] == [
            ("user", "What did I spend last month?"),
            ("assistant", "Answer for: What did I spend last month?"),
            ("user", "Break that down by category."),
            ("assistant", "Answer for: Break that down by category."),
        ]

        other_user = SimpleNamespace(user_id="other-user", email="other@example.test")
        forbidden = await main.chat_with_transactions(
            models.ChatQuery(query="Can I read another user's chat?", conversation_id=conversation_id),
            other_user,
        )
        assert forbidden["status"] == "error"
        assert "not found" in forbidden["data"]["answer"].lower()

    asyncio.run(scenario())
