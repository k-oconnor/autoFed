"""Agent archetypes, goals, and seed-stable stochastic traits."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal, cast

if TYPE_CHECKING:
    from autofed.world.firm import FirmGovernance

PrimaryGoal = Literal["stability", "growth", "status"]

_VALID_PRIMARY: frozenset[str] = frozenset({"stability", "growth", "status"})


@dataclass
class AgentGoals:
    primary: PrimaryGoal = "stability"
    target_wealth: float | None = None
    min_consumption_units: int | None = None


@dataclass
class AgentPersona:
    role: str = "worker"
    risk_aversion: float = 0.5
    agency: float = 0.25
    goals: AgentGoals = field(default_factory=AgentGoals)
    #: Optional narrative JSON for LLM prompts (display_name, bio, voice, …).
    llm_profile: dict[str, Any] | None = None


# Role -> (risk_lo, risk_hi, agency_lo, agency_hi, goal_weights stability/growth/status)
_ROLE_RANGES: dict[str, tuple[float, float, float, float, tuple[float, float, float]]] = {
    "worker": (0.42, 0.82, 0.08, 0.32, (0.55, 0.35, 0.10)),
    "entrepreneur": (0.12, 0.48, 0.42, 0.88, (0.15, 0.70, 0.15)),
    "manager": (0.32, 0.68, 0.22, 0.58, (0.45, 0.40, 0.15)),
    "rentier": (0.58, 0.92, 0.08, 0.28, (0.70, 0.20, 0.10)),
}


def _role_table_row(role: str) -> tuple[float, float, float, float, tuple[float, float, float]]:
    return _ROLE_RANGES.get(role.lower(), _ROLE_RANGES["worker"])


def _default_persona_for_role(role: str) -> AgentPersona:
    r_lo, r_hi, a_lo, a_hi, gw = _role_table_row(role)
    risk = 0.5 * (r_lo + r_hi)
    ag = 0.5 * (a_lo + a_hi)
    im = max(range(3), key=lambda j: gw[j])
    primary: PrimaryGoal = ("stability", "growth", "status")[im]
    return AgentPersona(role=role.lower(), risk_aversion=risk, agency=ag, goals=AgentGoals(primary=primary))


DEFAULT_AGENT_PERSONA = _default_persona_for_role("worker")


def _rng_for_agent(base_seed: int, agent_id: str) -> random.Random:
    h = hashlib.sha256(f"{base_seed}:{agent_id}".encode()).digest()
    return random.Random(int.from_bytes(h[:8], "little"))


def _sample_primary(rng: random.Random, weights: tuple[float, float, float]) -> PrimaryGoal:
    keys: tuple[PrimaryGoal, PrimaryGoal, PrimaryGoal] = ("stability", "growth", "status")
    r = rng.random() * sum(weights)
    acc = 0.0
    for k, w in zip(keys, weights):
        acc += w
        if r <= acc:
            return k
    return keys[-1]


def draw_persona_traits(role: str, rng: random.Random) -> tuple[float, float, AgentGoals]:
    r_lo, r_hi, a_lo, a_hi, gw = _role_table_row(role)
    risk = rng.uniform(r_lo, r_hi)
    ag = rng.uniform(a_lo, a_hi)
    primary = _sample_primary(rng, gw)
    return risk, ag, AgentGoals(primary=primary)


def _merge_goals_partial(raw: dict[str, Any], base: AgentGoals) -> AgentGoals:
    primary = str(raw.get("primary", base.primary))
    if primary not in _VALID_PRIMARY:
        primary = base.primary
    target_wealth = float(raw["target_wealth"]) if "target_wealth" in raw else base.target_wealth
    min_consumption_units = (
        int(raw["min_consumption_units"])
        if "min_consumption_units" in raw
        else base.min_consumption_units
    )
    return AgentGoals(
        primary=cast(PrimaryGoal, primary),
        target_wealth=target_wealth,
        min_consumption_units=min_consumption_units,
    )


def _llm_profile_from_yaml(yaml_block: dict[str, Any]) -> dict[str, Any] | None:
    lp = yaml_block.get("llm_profile")
    return dict(lp) if isinstance(lp, dict) else None


def merge_yaml_persona(
    agent_id: str,
    yaml_block: dict[str, Any],
    *,
    stochastic: bool,
    base_seed: int,
    default_role: str,
) -> AgentPersona:
    """Build persona from YAML block; optionally draw unspecified traits from role ranges."""
    role = str(yaml_block.get("role", default_role)).lower()
    det = _default_persona_for_role(role)
    llm_profile = _llm_profile_from_yaml(yaml_block)
    if stochastic:
        rng = _rng_for_agent(base_seed, agent_id)
        dr, da, dg = draw_persona_traits(role, rng)
        risk = float(yaml_block["risk_aversion"]) if "risk_aversion" in yaml_block else dr
        agency = float(yaml_block["agency"]) if "agency" in yaml_block else da
        g_raw = yaml_block.get("goals")
        if isinstance(g_raw, dict):
            goals = _merge_goals_partial(g_raw, dg)
        else:
            goals = dg
        return AgentPersona(
            role=role, risk_aversion=risk, agency=agency, goals=goals, llm_profile=llm_profile
        )

    risk = float(yaml_block["risk_aversion"]) if "risk_aversion" in yaml_block else det.risk_aversion
    agency = float(yaml_block["agency"]) if "agency" in yaml_block else det.agency
    g_raw = yaml_block.get("goals")
    if isinstance(g_raw, dict):
        goals = _merge_goals_partial(g_raw, det.goals)
    else:
        goals = det.goals
    return AgentPersona(
        role=role, risk_aversion=risk, agency=agency, goals=goals, llm_profile=llm_profile
    )


def default_role_for_agent_id(agent_id: str) -> str:
    return "worker" if agent_id.startswith("hh_") else "manager"


def collect_referenced_agent_ids(
    household_ids: tuple[str, ...],
    governance: dict[str, FirmGovernance],
    explicit_yaml_agents: dict[str, Any],
) -> list[str]:
    s: set[str] = set(household_ids)
    s.update(explicit_yaml_agents.keys())
    for gov in governance.values():
        s.add(gov.ceo_agent_id)
        s.update(gov.board_agent_ids)
    return sorted(s)


def build_agent_personas(
    *,
    household_ids: tuple[str, ...],
    governance: dict[str, FirmGovernance],
    agents_yaml: dict[str, Any] | None,
    agent_generation: dict[str, Any] | None,
    economy_seed: int,
) -> dict[str, AgentPersona]:
    """Populate personas for households, governance actors, and any explicit YAML keys."""
    raw_agents = agents_yaml or {}
    gen = agent_generation or {}
    stochastic = bool(gen.get("stochastic", False))
    base_seed = int(gen["base_seed"]) if gen.get("base_seed") is not None else int(economy_seed)

    ids = collect_referenced_agent_ids(household_ids, governance, raw_agents)
    out: dict[str, AgentPersona] = {}
    for aid in ids:
        block = raw_agents.get(aid, {})
        if not isinstance(block, dict):
            block = {}
        dr = default_role_for_agent_id(aid)
        out[aid] = merge_yaml_persona(aid, block, stochastic=stochastic, base_seed=base_seed, default_role=dr)
    return out


def persona_to_snapshot_dict(p: AgentPersona) -> dict[str, Any]:
    d: dict[str, Any] = {
        "role": p.role,
        "risk_aversion": float(p.risk_aversion),
        "agency": float(p.agency),
        "goals": {
            "primary": p.goals.primary,
            "target_wealth": p.goals.target_wealth,
            "min_consumption_units": p.goals.min_consumption_units,
        },
    }
    if p.llm_profile is not None:
        d["llm_profile"] = p.llm_profile
    return d


def persona_prompt_json(p: AgentPersona) -> str:
    """Compact JSON snippet for LLM system/user context."""
    block: dict[str, Any] = {
        "role": p.role,
        "risk_aversion": p.risk_aversion,
        "agency": p.agency,
        "goals": {
            "primary": p.goals.primary,
            "target_wealth": p.goals.target_wealth,
            "min_consumption_units": p.goals.min_consumption_units,
        },
    }
    if p.llm_profile:
        block["llm_profile"] = p.llm_profile
    return json.dumps(block, separators=(",", ":"))
