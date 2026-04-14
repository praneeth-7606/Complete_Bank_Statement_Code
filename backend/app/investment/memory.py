"""
Conversation Memory Manager for Investment Chat
------------------------------------------------
Stores conversation history per user for context-aware responses.
"""
import logging
from typing import Dict, List
from collections import defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversationMemory:
    """In-memory conversation storage with LRU-style cleanup."""
    
    def __init__(self, max_messages_per_user: int = 10):
        self.max_messages = max_messages_per_user
        self._conversations: Dict[str, List[Dict]] = defaultdict(list)
    
    def add_message(self, user_id: str, role: str, content: str):
        """Add a message to user's conversation history."""
        message = {
            "role": role,  # "user" or "assistant"
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        self._conversations[user_id].append(message)
        
        # Keep only last N messages
        if len(self._conversations[user_id]) > self.max_messages:
            self._conversations[user_id] = self._conversations[user_id][-self.max_messages:]
        
        logger.debug(f"Added {role} message for user {user_id[:8]}... | history size: {len(self._conversations[user_id])}")
    
    def get_history(self, user_id: str, last_n: int = None) -> List[Dict]:
        """Get conversation history for a user."""
        history = self._conversations.get(user_id, [])
        if last_n:
            return history[-last_n:]
        return history
    
    def get_formatted_history(self, user_id: str, last_n: int = 5) -> str:
        """Get formatted conversation history as string for context."""
        history = self.get_history(user_id, last_n)
        
        if not history:
            return ""
        
        formatted = ["Previous conversation:"]
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            content = msg["content"][:200]  # Truncate long messages
            formatted.append(f"{role}: {content}")
        
        return "\n".join(formatted)
    
    def clear_history(self, user_id: str):
        """Clear conversation history for a user."""
        if user_id in self._conversations:
            del self._conversations[user_id]
            logger.info(f"Cleared conversation history for user {user_id[:8]}...")
    
    def get_stats(self) -> Dict:
        """Get memory statistics."""
        return {
            "total_users": len(self._conversations),
            "total_messages": sum(len(msgs) for msgs in self._conversations.values()),
            "users_with_history": list(self._conversations.keys())
        }


# Singleton instance
conversation_memory = ConversationMemory(max_messages_per_user=10)
