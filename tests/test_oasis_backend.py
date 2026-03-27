from unittest.mock import patch

from autofed.agents.oasis.backend import OasisOpenAIBackend
from autofed.agents.backend import ManualAgentBackend
from autofed.world.state import demo_world


@patch("autofed.agents.oasis.backend.complete_json_object")
def test_oasis_applies_new_good_feed_and_role(mock_complete) -> None:
    mock_complete.return_value = {
        "tick_plan": {"wages": [], "sales": [], "dividends": [], "price_updates": []},
        "feed_posts": [
            {"author_id": "hh_0", "body": "Market watch: flour up.", "kind": "journalism"}
        ],
        "role_declarations": [{"agent_id": "hh_0", "declared_role": "journalist"}],
        "new_goods": [{"good_id": "tea", "initial_price": 3.0, "category": "normal"}],
        "recipe_adoptions": [],
    }
    w = demo_world()
    w.oasis.enabled = True
    w.oasis.feed_context_posts = 5
    OasisOpenAIBackend(ManualAgentBackend()).plan_tick(w, 0)
    assert "tea" in w.posted_unit_prices
    assert w.agent_declared_roles.get("hh_0") == "journalist"
    assert len(w.social_feed) == 1
    assert w.social_feed[0].body.startswith("Market watch")


@patch("autofed.agents.oasis.backend.complete_json_object")
def test_oasis_disabled_skips_openai(mock_complete) -> None:
    w = demo_world()
    w.oasis.enabled = False
    OasisOpenAIBackend(ManualAgentBackend()).plan_tick(w, 0)
    mock_complete.assert_not_called()
