"""Saved chat history for logged-in customers, in the chat_messages table.

Every query is filtered by the user_id the server took from the session,
so a customer can only ever read or write their own messages.
"""

import json

from db import get_db
from models import ChatTurn, ProductCard, SavedChatMessage

AGENT_HISTORY_MESSAGES = 12  # Earlier messages given to the agent (trimmed further in agent.py).
PAGE_HISTORY_MESSAGES = 50  # Messages shown in the chat panel when it reloads.


def _cards(products_json: str | None) -> list[ProductCard]:
    # Cards saved as JSON. Older rows store full product dicts; extra keys are ignored.
    if not products_json:
        return []
    try:
        return [ProductCard.model_validate(p) for p in json.loads(products_json)]
    except (ValueError, TypeError):
        return []


def _recent_rows(user_id: int, limit: int) -> list:
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT role, content, products_json, created_at FROM chat_messages
            WHERE user_id = ? AND role IN ('user', 'assistant')
            ORDER BY id DESC LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return list(reversed(rows))


def load_for_page(user_id: int) -> list[SavedChatMessage]:
    return [
        SavedChatMessage(
            role=r["role"],
            content=r["content"],
            products=_cards(r["products_json"]),
            created_at=r["created_at"],
        )
        for r in _recent_rows(user_id, PAGE_HISTORY_MESSAGES)
    ]


def load_for_agent(user_id: int) -> list[ChatTurn]:
    return [ChatTurn(role=r["role"], content=r["content"]) for r in _recent_rows(user_id, AGENT_HISTORY_MESSAGES)]


def save_exchange(user_id: int, message: str, reply: str, cards: list[ProductCard]) -> None:
    products_json = json.dumps([c.model_dump() for c in cards]) if cards else None
    with get_db(write=True) as conn:
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content) VALUES (?, 'user', ?)",
            (user_id, message),
        )
        conn.execute(
            "INSERT INTO chat_messages (user_id, role, content, products_json) VALUES (?, 'assistant', ?, ?)",
            (user_id, reply, products_json),
        )
