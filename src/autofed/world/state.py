from __future__ import annotations

from dataclasses import dataclass, field

from autofed.accounting.ledger import Ledger
from autofed.agents.batching import LLMCallBudget
from autofed.agents.expectations import ExpectationState
from autofed.agents.persona import DEFAULT_AGENT_PERSONA, AgentGoals, AgentPersona
from autofed.banking.layer import BankingLayer
from autofed.equity.cap_table import EquityCapTable
from autofed.social.feed import FeedPost
from autofed.social.graph import SocialGraph
from autofed.world.oasis_config import OasisConfig
from autofed.world.central_bank import TaylorParams, policy_rate
from autofed.world.firm import FirmGovernance, FirmRecipe
from autofed.world.firm_lifecycle import FirmEntryTemplate, FirmLifecycleParams


@dataclass
class WorldState:
    """Authoritative economy state: ledger, inventories, institutions."""

    ledger: Ledger
    inventory: dict[str, dict[str, int]] = field(default_factory=dict)
    employment: dict[str, str] = field(default_factory=dict)
    posted_unit_prices: dict[str, float] = field(default_factory=dict)
    # good_id -> category (necessity, normal, luxury, veblen, …) for market priority.
    good_categories: dict[str, str] = field(default_factory=dict)
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
    agent_personas: dict[str, AgentPersona] = field(default_factory=dict)
    social_feed: list[FeedPost] = field(default_factory=list)
    agent_declared_roles: dict[str, str] = field(default_factory=dict)
    oasis: OasisConfig = field(default_factory=OasisConfig)
    social_graph: SocialGraph | None = None
    llm_budget: LLMCallBudget | None = None
    banking: BankingLayer | None = None
    equity: EquityCapTable | None = None
    household_ids: tuple[str, ...] = ()
    firm_ids: tuple[str, ...] = ()
    exited_firm_ids: set[str] = field(default_factory=set)
    firm_negative_streak: dict[str, int] = field(default_factory=dict)
    firm_exit_log: list[str] = field(default_factory=list)
    firm_entry_log: list[str] = field(default_factory=list)
    lifecycle_params: FirmLifecycleParams = field(default_factory=FirmLifecycleParams)
    entry_template: FirmEntryTemplate | None = None
    entrant_seq: int = 0

    def persona(self, agent_id: str) -> AgentPersona:
        return self.agent_personas.get(agent_id, DEFAULT_AGENT_PERSONA)

    def firm_is_active(self, firm_id: str) -> bool:
        return firm_id in self.firm_recipes

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
        good_categories={"food": "necessity"},
        firm_recipes={
            # Zero-output placeholder so the demo firm counts as active without changing stocks.
            "firm": FirmRecipe(output_good="food", output_qty=0, inputs={}),
        },
        expectations=ex,
        household_ids=("hh_0", "hh_1"),
        firm_ids=("firm",),
        governance={
            "firm": FirmGovernance(firm_id="firm", ceo_agent_id="ceo_1", evaluate_every_n_ticks=5)
        },
        agent_personas={
            "hh_0": AgentPersona(
                role="worker",
                risk_aversion=0.65,
                agency=0.2,
                goals=AgentGoals(primary="stability"),
            ),
            "hh_1": AgentPersona(
                role="entrepreneur",
                risk_aversion=0.35,
                agency=0.55,
                goals=AgentGoals(primary="growth"),
            ),
            "ceo_1": AgentPersona(
                role="manager",
                risk_aversion=0.5,
                agency=0.4,
                goals=AgentGoals(primary="stability"),
            ),
        },
        forward_guidance="The committee remains data-dependent.",
        social_graph=SocialGraph([("hh_0", "hh_1")]),
        banking=None,
        equity=None,
    )
