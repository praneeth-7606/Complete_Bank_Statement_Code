"""MongoDB-backed, tenant-isolated memory for the financial chat."""

import datetime
from typing import Literal

from pymongo import ReturnDocument

from . import models


CHAT_CONTEXT_MESSAGE_LIMIT = 20


class ConversationNotFoundError(ValueError):
    """Raised when a caller asks for a conversation they do not own."""


def _utcnow() -> datetime.datetime:
    return datetime.datetime.utcnow()


async def resolve_conversation(
    user_id: str, conversation_id: str | None = None
) -> models.ChatConversation:
    """Create a conversation or resolve one belonging to the authenticated user."""
    if conversation_id is None:
        conversation = models.ChatConversation(user_id=user_id)
        await conversation.insert()
        return conversation

    conversation = await models.ChatConversation.find_one(
        models.ChatConversation.conversation_id == conversation_id,
        models.ChatConversation.user_id == user_id,
    )
    if conversation is None:
        raise ConversationNotFoundError("Conversation not found")
    return conversation


async def recent_history(
    user_id: str,
    conversation_id: str,
    limit: int = CHAT_CONTEXT_MESSAGE_LIMIT,
) -> list[dict[str, str]]:
    """Return the bounded, ordered context passed to the RAG pipeline."""
    messages = await (
        models.ChatMessage.find(
            models.ChatMessage.user_id == user_id,
            models.ChatMessage.conversation_id == conversation_id,
        )
        .sort("-sequence")
        .limit(limit)
        .to_list()
    )
    messages.reverse()
    return [{"role": message.role, "content": message.content} for message in messages]


async def append_message(
    conversation: models.ChatConversation,
    user_id: str,
    role: Literal["user", "assistant"],
    content: str,
) -> models.ChatMessage:
    """Append one message with an atomic, per-conversation sequence number."""
    text = content.strip()
    if not text:
        raise ValueError("Chat messages cannot be empty")

    now = _utcnow()
    collection = models.ChatConversation.get_pymongo_collection()
    updated = await collection.find_one_and_update(
        {
            "conversation_id": conversation.conversation_id,
            "user_id": user_id,
        },
        {
            "$inc": {"message_count": 1},
            "$set": {"updated_at": now},
        },
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise ConversationNotFoundError("Conversation not found")

    message_count = int(updated["message_count"])
    if message_count == 1:
        await collection.update_one(
            {"_id": updated["_id"]},
            {"$set": {"title": text[:80]}},
        )

    message = models.ChatMessage(
        conversation_id=conversation.conversation_id,
        user_id=user_id,
        sequence=message_count,
        role=role,
        content=text,
        created_at=now,
    )
    await message.insert()
    return message
