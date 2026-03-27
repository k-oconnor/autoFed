"""OpenAI-backed OASIS layer: social feed, emergent roles, economy patches, TickPlan merge."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, cast

from autofed.agents.backend import ManualAgentBackend
from autofed.agents.oasis.client import complete_json_object
from autofed.agents.oasis.schemas import (
    build_tick_plan_from_parsed,
    merge_tick_plans,
    parse_oasis_json,
    tick_plan_has_economic_content,
)
from autofed.agents.plan import TickPlan
from autofed.social.feed import FeedPost, FeedPostKind, append_social_feed, feed_post_to_dict
from autofed.world.patches import apply_new_goods, apply_recipe_adoptions

if TYPE_CHECKING:
    from autofed.world.state import WorldState

_SYSTEM_PROMPT = """You are coordinating autonomous agents in a closed-economy simulation.

Agents may adopt emergent social/economic roles (e.g. worker, entrepreneur, journalist, commentator).
Journalists and commentators primarily influence others via feed_posts (kind "journalism").
Innovators may propose new tracked goods when they perceive a market gap.

You MUST respond with a single JSON object only (no markdown), with this shape:
{
  "tick_plan": {
    "wages": [{"firm_id": "...", "household_id": "...", "amount": 0.0}],
    "sales": [{"buyer_id": "...", "seller_id": "...", "good_id": "...", "quantity": 1, "unit_price": 1.0}],
    "dividends": [{"firm_id": "...", "shareholder_id": "...", "amount": 0.0}],
    "price_updates": [{"good_id": "...", "price": 1.0}]
  },
  "feed_posts": [{"author_id": "...", "body": "...", "kind": "social|listing|marketing|journalism", "good_id": null, "quantity": null, "unit_price": null}],
  "role_declarations": [{"agent_id": "...", "declared_role": "...", "rationale": "..."}],
  "new_goods": [{"good_id": "slug_lowercase", "initial_price": 1.0, "category": "necessity|normal|luxury|...", "description": "..."}],
  "recipe_adoptions": [{"firm_id": "...", "recipe": {"output_good": "...", "output_qty": 1, "inputs": {"input_good": 1}}}]
}

Rules:
- good_id must match ^[a-z][a-z0-9_]{0,31}$ for new_goods.
- Only reference goods that exist in posted_unit_prices OR that you add in new_goods in this same response (new_goods are applied before recipe_adoptions).
- Only wage/sell between entities that exist in the user payload (households, active firms).
- If you are unsure about numeric economics, return empty tick_plan arrays and only feed_posts / role_declarations.
- Keep feed_posts concise (simulated social media).
"""


_KINDS = frozenset({"social", "listing", "marketing", "journalism"})


def build_oasis_user_payload(world: WorldState, tick: int, feed_context_posts: int) -> str:
    tail = world.social_feed[-feed_context_posts:] if feed_context_posts > 0 else []
    feed_ser = [feed_post_to_dict(p) for p in tail]
    personas: dict[str, Any] = {}
    for aid, p in world.agent_personas.items():
        personas[aid] = {
            "role": p.role,
            "risk_aversion": p.risk_aversion,
            "agency": p.agency,
            "goals": {"primary": p.goals.primary},
            "llm_profile": p.llm_profile,
            "declared_role": world.agent_declared_roles.get(aid),
        }
    body: dict[str, Any] = {
        "tick": tick,
        "household_ids": list(world.household_ids),
        "firm_ids_active": list(world.firm_recipes.keys()),
        "employment": dict(world.employment),
        "posted_unit_prices": dict(world.posted_unit_prices),
        "good_categories": dict(world.good_categories),
        "household_cash": {h: float(world.ledger.cash.get(h, 0.0)) for h in world.household_ids},
        "firm_cash": {f: float(world.ledger.cash.get(f, 0.0)) for f in world.firm_recipes.keys()},
        "agent_personas": personas,
        "social_feed_tail": feed_ser,
        "forward_guidance": world.forward_guidance[:300],
    }
    return json.dumps(body, separators=(",", ":"))


def _feed_posts_from_raw(raw_posts: list[Any], tick: int) -> list[FeedPost]:
    out: list[FeedPost] = []
    for p in raw_posts:
        if not isinstance(p, dict):
            continue
        author = str(p.get("author_id", "")).strip()
        body = str(p.get("body", "")).strip()[:4000]
        if not author or not body:
            continue
        kind = str(p.get("kind", "social"))
        if kind not in _KINDS:
            kind = "social"
        gid = p.get("good_id")
        good_id = str(gid) if gid is not None and str(gid) else None
        qty_raw = p.get("quantity")
        quantity = int(qty_raw) if qty_raw is not None else None
        up_raw = p.get("unit_price")
        unit_price = float(up_raw) if up_raw is not None else None
        out.append(
            FeedPost(
                tick=tick,
                author_id=author,
                body=body,
                kind=cast(FeedPostKind, kind),
                good_id=good_id,
                quantity=quantity,
                unit_price=unit_price,
            )
        )
    return out


class OasisOpenAIBackend:
    """One OpenAI JSON call per tick: patches + feed + optional TickPlan merged with manual policy."""

    __slots__ = ("_inner",)

    def __init__(self, inner: ManualAgentBackend | None = None) -> None:
        self._inner = inner or ManualAgentBackend()

    def plan_tick(self, world: WorldState, tick: int) -> TickPlan:
        cfg = world.oasis
        if not cfg.enabled:
            return self._inner.plan_tick(world, tick)

        user_payload = build_oasis_user_payload(world, tick, cfg.feed_context_posts)
        data = complete_json_object(
            system_prompt=_SYSTEM_PROMPT,
            user_content=user_payload,
            model=cfg.model,
            temperature=cfg.temperature,
        )
        parsed = parse_oasis_json(data)

        apply_new_goods(world, parsed.new_goods, cfg)
        apply_recipe_adoptions(world, parsed.recipe_adoptions)

        for rd in parsed.role_declarations:
            if not isinstance(rd, dict):
                continue
            aid = str(rd.get("agent_id", "")).strip()
            role = str(rd.get("declared_role", "")).strip()
            if aid and role:
                world.agent_declared_roles[aid] = role[:120]

        posts = _feed_posts_from_raw(parsed.feed_posts, tick)
        append_social_feed(world, posts, max_posts=cfg.feed_max_posts)

        if world.llm_budget is not None:
            world.llm_budget.consume(1)

        manual = self._inner.plan_tick(world, tick)
        if tick_plan_has_economic_content(parsed.tick_plan):
            llm_plan = build_tick_plan_from_parsed(parsed.tick_plan, world)
            return merge_tick_plans(llm_plan, manual)
        return manual
