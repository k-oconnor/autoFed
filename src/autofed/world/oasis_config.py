"""Runtime settings for OASIS / OpenAI social-economic layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class OasisConfig:
    enabled: bool = False
    model: str = "gpt-4o-mini"
    feed_max_posts: int = 200
    feed_context_posts: int = 20
    temperature: float = 0.4
    max_new_goods_per_tick: int = 5
    max_good_price: float = 1_000_000.0


def parse_oasis_yaml(raw: dict[str, Any] | None) -> OasisConfig:
    if not raw:
        return OasisConfig()
    return OasisConfig(
        enabled=bool(raw.get("enabled", False)),
        model=str(raw.get("model", "gpt-4o-mini")),
        feed_max_posts=int(raw.get("feed_max_posts", 200)),
        feed_context_posts=int(raw.get("feed_context_posts", 20)),
        temperature=float(raw.get("temperature", 0.4)),
        max_new_goods_per_tick=int(raw.get("max_new_goods_per_tick", 5)),
        max_good_price=float(raw.get("max_good_price", 1_000_000.0)),
    )
