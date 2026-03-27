"""Simulated social feed (OASIS-style public timeline)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from autofed.world.state import WorldState

FeedPostKind = Literal["social", "listing", "marketing", "journalism"]


@dataclass
class FeedPost:
    tick: int
    author_id: str
    body: str
    kind: FeedPostKind = "social"
    good_id: str | None = None
    quantity: int | None = None
    unit_price: float | None = None


def feed_post_to_dict(p: FeedPost) -> dict[str, Any]:
    return {
        "tick": p.tick,
        "author_id": p.author_id,
        "body": p.body,
        "kind": p.kind,
        "good_id": p.good_id,
        "quantity": p.quantity,
        "unit_price": p.unit_price,
    }


def append_social_feed(world: WorldState, posts: list[FeedPost], *, max_posts: int) -> None:
    """Append posts and trim to a ring buffer of length max_posts."""
    world.social_feed.extend(posts)
    if max_posts > 0 and len(world.social_feed) > max_posts:
        del world.social_feed[: len(world.social_feed) - max_posts]
