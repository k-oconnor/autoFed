from __future__ import annotations

from dataclasses import dataclass, field

from autofed.accounting.ledger import Ledger
from autofed.agents.batching import LLMCallBudget
from autofed.agents.expectations import ExpectationState
from autofed.banking.layer import BankingLayer
from autofed.equity.cap_table import EquityCapTable
from autofed.social.graph import SocialGraph
from autofed.world.central_bank import TaylorParams, policy_rate
from autofed.world.firm import FirmGovernance, FirmRecipe


@dataclass
class WorldState:
    """Authoritative economy state: ledger, inventories, institutions."""

    ledger: Ledger
    inventory: dict[str, dict[str, int]] = field(default_factory=dict)
    employment: dict[str, str] = field(default_factory=dict)
    posted_unit_prices: dict[str, float] = field(default_factory=dict)
    firm_recipes: dict[str, FirmRecipe] = field(default_factory=dict)
    taylor: TaylorParams = field(default_factory=TaylorParams)
    policy_rate: float = 0.05
    last_inflation: float = 0.0
    output_gap: float = 0.0
    cpi_level: float = 1.0
    _cpi_prev: float | None = field(default=None, repr=False)
    forward_guidance: str = ""
    governance: dict[str, FirmGovernance] = field(default_factory=dict)
    governance_log: list[str] = field(default_factory=list)
    expectations: dict[str, ExpectationState] = field(default_factory=dict)
    social_graph: SocialGraph | None = None
    llm_budget: LLMCallBudget | None = None
    banking: BankingLayer | None = None
    equity: EquityCapTable | None = None
    household_ids: tuple[str, ...] = ()
    firm_ids: tuple[str, ...] = ()

    def firm_inventory(self, firm_id: str, good_id: str) -> int:
        return self.inventory.get(firm_id, {}).get(good_id, 0)

    def add_inventory(self, firm_id: str, good_id: str, delta: int) -> None:
        if firm_id not in self.inventory:
            self.inventory[firm_id] = {}
        cur = self.inventory[firm_id].get(good_id, 0)
        new = cur + delta
        if new < 0:
            raise ValueError(f"inventory would go negative: {firm_id}/{good_id} {cur} + {delta}")
        self.inventory[firm_id][good_id] = new

    def apply_price_updates(self, updates: dict[str, float]) -> None:
        for gid, px in updates.items():
            if px <= 0:
                raise ValueError(f"price must be positive for {gid!r}")
            self.posted_unit_prices[gid] = px

    def refresh_price_level(self) -> None:
        if not self.posted_unit_prices:
            return
        px = sum(self.posted_unit_prices.values()) / len(self.posted_unit_prices)
        if self._cpi_prev is None:
            self._cpi_prev = px
            self.cpi_level = px
            self.last_inflation = 0.0
            return
        prev = self._cpi_prev
        self.last_inflation = (px - prev) / prev if prev else 0.0
        self.cpi_level = px
        self._cpi_prev = px

    def refresh_output_gap(self) -> None:
        if not self.household_ids:
            self.output_gap = 0.0
            return
        emp = sum(1 for h in self.household_ids if self.employment.get(h))
        rate = emp / len(self.household_ids)
        self.output_gap = rate - 0.95

    def refresh_policy_rate(self) -> None:
        self.policy_rate = policy_rate(self.last_inflation, self.output_gap, self.taylor)

    def update_expectations(self) -> None:
        if not self.expectations:
            return
        neighbor_inf = {aid: ex.inflation_expected for aid, ex in self.expectations.items()}
        for aid, ex in self.expectations.items():
            realized = self.last_inflation
            peer: float | None = None
            if self.social_graph is not None:
                peer = self.social_graph.mean_neighbor_value(aid, neighbor_inf)
            if peer is not None:
                ex.inflation_expected = 0.5 * realized + 0.5 * peer
            else:
                ex.inflation_expected = 0.7 * ex.inflation_expected + 0.3 * realized
            gl = self.forward_guidance.lower()
            if "dovish" in gl:
                ex.inflation_expected -= 0.002
            elif "hawkish" in gl:
                ex.inflation_expected += 0.002

    def governance_step(self, tick: int) -> None:
        for fid, gov in self.governance.items():
            n = gov.evaluate_every_n_ticks
            if n <= 0 or tick % n != 0:
                continue
            self.governance_log.append(
                f"tick {tick}: board at {fid} retains CEO {gov.ceo_agent_id}"
            )

    def expectation_dispersion(self) -> float | None:
        vals = [ex.inflation_expected for ex in self.expectations.values()]
        if len(vals) < 2:
            return None
        mean = sum(vals) / len(vals)
        var = sum((v - mean) ** 2 for v in vals) / len(vals)
        return var**0.5


def demo_world() -> WorldState:
    """Two households, one firm; CB nets to -1200 (private +1200)."""
    ledger = Ledger(
        {
            "cb": -1200.0,
            "firm": 1000.0,
            "hh_0": 100.0,
            "hh_1": 100.0,
        }
    )
    ex = {
        "hh_0": ExpectationState(0.02),
        "hh_1": ExpectationState(0.025),
    }
    return WorldState(
        ledger=ledger,
        inventory={"firm": {"food": 100}},
        employment={"hh_0": "firm", "hh_1": "firm"},
        posted_unit_prices={"food": 10.0},
        expectations=ex,
        household_ids=("hh_0", "hh_1"),
        firm_ids=("firm",),
        governance={
            "firm": FirmGovernance(firm_id="firm", ceo_agent_id="ceo_1", evaluate_every_n_ticks=5)
        },
        forward_guidance="The committee remains data-dependent.",
        social_graph=SocialGraph([("hh_0", "hh_1")]),
        banking=None,
        equity=None,
    )
