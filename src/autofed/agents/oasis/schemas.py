"""Parse and validate OASIS JSON from the model."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from autofed.agents.plan import DividendPayment, GoodsSale, PostedPrice, TickPlan, WagePayment


@dataclass
class ParsedOasis:
    tick_plan: dict[str, Any] = field(default_factory=dict)
    feed_posts: list[dict[str, Any]] = field(default_factory=list)
    role_declarations: list[dict[str, Any]] = field(default_factory=list)
    new_goods: list[dict[str, Any]] = field(default_factory=list)
    recipe_adoptions: list[dict[str, Any]] = field(default_factory=list)


def parse_oasis_json(raw: str | dict[str, Any]) -> ParsedOasis:
    if isinstance(raw, str):
        data = json.loads(raw)
    else:
        data = raw
    if not isinstance(data, dict):
        return ParsedOasis()

    tp = data.get("tick_plan")
    tick_plan = tp if isinstance(tp, dict) else {}

    def _list(key: str) -> list[Any]:
        v = data.get(key)
        return v if isinstance(v, list) else []

    return ParsedOasis(
        tick_plan=tick_plan,
        feed_posts=_list("feed_posts"),
        role_declarations=_list("role_declarations"),
        new_goods=_list("new_goods"),
        recipe_adoptions=_list("recipe_adoptions"),
    )


def tick_plan_has_economic_content(tp: dict[str, Any]) -> bool:
    if not tp:
        return False
    for key in ("wages", "sales", "dividends", "price_updates"):
        v = tp.get(key)
        if isinstance(v, list) and len(v) > 0:
            return True
    return False


def _safe_wages(tp: dict[str, Any], world: Any) -> tuple[WagePayment, ...]:
    out: list[WagePayment] = []
    for w in tp.get("wages") or []:
        if not isinstance(w, dict):
            continue
        try:
            fid = str(w["firm_id"])
            hid = str(w["household_id"])
            amt = float(w["amount"])
        except (KeyError, TypeError, ValueError):
            continue
        if amt <= 0 or not world.firm_is_active(fid):
            continue
        out.append(WagePayment(fid, hid, amt))
    return tuple(out)


def _safe_sales(tp: dict[str, Any], world: Any) -> tuple[GoodsSale, ...]:
    out: list[GoodsSale] = []
    for s in tp.get("sales") or []:
        if not isinstance(s, dict):
            continue
        try:
            buyer = str(s["buyer_id"])
            seller = str(s["seller_id"])
            good = str(s["good_id"])
            qty = int(s["quantity"])
            price = float(s["unit_price"])
        except (KeyError, TypeError, ValueError):
            continue
        if qty <= 0 or price <= 0:
            continue
        if good not in world.posted_unit_prices or not world.firm_is_active(seller):
            continue
        out.append(GoodsSale(buyer, seller, good, qty, price))
    return tuple(out)


def _safe_dividends(tp: dict[str, Any], world: Any) -> tuple[DividendPayment, ...]:
    out: list[DividendPayment] = []
    for d in tp.get("dividends") or []:
        if not isinstance(d, dict):
            continue
        try:
            fid = str(d["firm_id"])
            shr = str(d["shareholder_id"])
            amt = float(d["amount"])
        except (KeyError, TypeError, ValueError):
            continue
        if amt <= 0 or not world.firm_is_active(fid):
            continue
        out.append(DividendPayment(fid, shr, amt))
    return tuple(out)


def _safe_price_updates(tp: dict[str, Any], world: Any) -> tuple[PostedPrice, ...]:
    out: list[PostedPrice] = []
    for p in tp.get("price_updates") or []:
        if not isinstance(p, dict):
            continue
        try:
            gid = str(p["good_id"])
            px = float(p["price"])
        except (KeyError, TypeError, ValueError):
            continue
        if px <= 0 or gid not in world.posted_unit_prices:
            continue
        out.append(PostedPrice(gid, px))
    return tuple(out)


def build_tick_plan_from_parsed(tp: dict[str, Any], world: Any) -> TickPlan:
    return TickPlan(
        wages=_safe_wages(tp, world),
        sales=_safe_sales(tp, world),
        dividends=_safe_dividends(tp, world),
        price_updates=_safe_price_updates(tp, world),
    )


def merge_tick_plans(llm: TickPlan, manual: TickPlan) -> TickPlan:
    """Prefer LLM legs when non-empty; otherwise manual."""
    wages = llm.wages if llm.wages else manual.wages
    sales = llm.sales if llm.sales else manual.sales
    dividends = llm.dividends if llm.dividends else manual.dividends
    price_updates = llm.price_updates + manual.price_updates
    return TickPlan(
        wages=wages,
        sales=sales,
        dividends=dividends,
        price_updates=price_updates,
    )
