from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autofed.world.firm import FirmRecipe
    from autofed.world.state import WorldState


def run_batch_production(world: WorldState) -> None:
    """For each firm with a recipe, produce one batch if inputs are available."""
    for firm_id, recipe in world.firm_recipes.items():
        _produce_one_batch(world, firm_id, recipe)


def _produce_one_batch(world: WorldState, firm_id: str, recipe: FirmRecipe) -> None:
    for good_id, need in recipe.inputs.items():
        if world.firm_inventory(firm_id, good_id) < need:
            return
    for good_id, need in recipe.inputs.items():
        world.add_inventory(firm_id, good_id, -need)
    world.add_inventory(firm_id, recipe.output_good, recipe.output_qty)
