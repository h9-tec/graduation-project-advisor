from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from core.settings import get_settings

_SESSION_TTL_SECONDS = 60 * 60 * 6  # 6 hours


async def get_redis() -> Redis:
    return Redis.from_url(get_settings().redis_url, decode_responses=True)


def _session_key(sid: str) -> str:
    return f"sess:{sid}"


def _cards_key(sid: str) -> str:
    return f"sess:{sid}:cards"


def _blueprint_key(sid: str, card_id: str) -> str:
    return f"sess:{sid}:bp:{card_id}"


async def save_profile(sid: str, profile: dict[str, Any]) -> None:
    r = await get_redis()
    await r.set(_session_key(sid), json.dumps(profile), ex=_SESSION_TTL_SECONDS)


async def load_profile(sid: str) -> dict[str, Any] | None:
    r = await get_redis()
    raw = await r.get(_session_key(sid))
    return json.loads(raw) if raw else None


async def save_cards(sid: str, cards: list[dict[str, Any]]) -> None:
    r = await get_redis()
    await r.set(_cards_key(sid), json.dumps(cards), ex=_SESSION_TTL_SECONDS)


async def load_cards(sid: str) -> list[dict[str, Any]] | None:
    r = await get_redis()
    raw = await r.get(_cards_key(sid))
    return json.loads(raw) if raw else None


async def save_blueprint(sid: str, card_id: str, bp: dict[str, Any]) -> None:
    r = await get_redis()
    await r.set(_blueprint_key(sid, card_id), json.dumps(bp), ex=_SESSION_TTL_SECONDS)


async def load_blueprint(sid: str, card_id: str) -> dict[str, Any] | None:
    r = await get_redis()
    raw = await r.get(_blueprint_key(sid, card_id))
    return json.loads(raw) if raw else None


# ---------- Refinement history + rate limit ------------------------------

def _profile_history_key(sid: str) -> str:
    return f"sess:{sid}:profile_history"


def _refine_count_key(sid: str) -> str:
    return f"sess:{sid}:refine_count"


MAX_REFINEMENTS_PER_SESSION = 15


async def push_profile_history(sid: str, profile: dict[str, Any]) -> int:
    """Push the PREVIOUS profile onto a stack so the next refinement can be undone.

    Returns the new stack depth.
    """
    r = await get_redis()
    depth = await r.lpush(_profile_history_key(sid), json.dumps(profile))
    await r.expire(_profile_history_key(sid), _SESSION_TTL_SECONDS)
    return int(depth)


async def pop_profile_history(sid: str) -> dict[str, Any] | None:
    """Pop and return the most recent previous profile; None if the stack is empty."""
    r = await get_redis()
    raw = await r.lpop(_profile_history_key(sid))
    return json.loads(raw) if raw else None


async def profile_history_depth(sid: str) -> int:
    r = await get_redis()
    return int(await r.llen(_profile_history_key(sid)))


async def incr_refine_count(sid: str) -> int:
    r = await get_redis()
    count = int(await r.incr(_refine_count_key(sid)))
    await r.expire(_refine_count_key(sid), _SESSION_TTL_SECONDS)
    return count


async def get_refine_count(sid: str) -> int:
    r = await get_redis()
    raw = await r.get(_refine_count_key(sid))
    return int(raw) if raw else 0


async def decr_refine_count(sid: str) -> int:
    r = await get_redis()
    count = int(await r.decr(_refine_count_key(sid)))
    if count < 0:
        await r.set(_refine_count_key(sid), "0", ex=_SESSION_TTL_SECONDS)
        return 0
    return count
