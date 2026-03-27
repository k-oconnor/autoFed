"""Validated economy mutations from LLM proposals (new goods, recipe updates)."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from autofed.world.firm import FirmRecipe

if TYPE_CHECKING:
    from autofed.world.oasis_config import OasisConfig
    from autofed.world.state import WorldState

_GOOD_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
_MAX_CATEGORY_LEN = 48


def apply_new_goods(world: WorldState, items: list[dict[str, Any]], cfg: OasisConfig) -> int:
    """Register new tracked goods (price + category). Returns count applied."""
    applied = 0
    cap = max(0, cfg.max_new_goods_per_tick)
    for item in items:
        if applied >= cap:
            break
        gid = str(item.get("good_id", "")).strip()
        if not _GOOD_ID_RE.match(gid):
            continue
        if gid in world.posted_unit_prices:
            continue
        try:
            price = float(item.get("initial_price", 0))
        except (TypeError, ValueError):
            continue
        if price <= 0 or price > cfg.max_good_price:
            continue
        cat = str(item.get("category", "normal")).strip()
        if not cat or len(cat) > _MAX_CATEGORY_LEN:
            continue
        world.posted_unit_prices[gid] = price
        world.good_categories[gid] = cat
        applied += 1
    return applied


def apply_recipe_adoptions(world: WorldState, items: list[dict[str, Any]]) -> int:
    """Replace recipe for an existing active firm; inputs must reference known goods."""
    n = 0
    for item in items:
        fid = item.get("firm_id")
        if not isinstance(fid, str) or fid not in world.firm_recipes:
            continue
        rc = item.get("recipe")
        if not isinstance(rc, dict):
            continue
        try:
            out_good = str(rc["output_good"])
            out_qty = int(rc["output_qty"])
            inputs_raw = rc.get("inputs") or {}
            inputs = {str(k): int(v) for k, v in inputs_raw.items()}
        except (KeyError, TypeError, ValueError):
            continue
        if not _GOOD_ID_RE.match(out_good):
            continue
        ok = all(g in world.posted_unit_prices for g in inputs) and out_good in world.posted_unit_prices
        if not ok:
            continue
        world.firm_recipes[fid] = FirmRecipe(
            output_good=out_good,
            output_qty=out_qty,
            inputs=inputs,
        )
        n += 1
    return n
