"""Typed goal model contracts for satiation success predicates."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from animetta.tools.minecraft.voyager.goal_models import FoodAtLeast, HealthAtLeast, SurviveGoal


def test_food_at_least_is_a_valid_success_predicate() -> None:
    goal = SurviveGoal(
        intent="survive",
        target="food-recovery",
        success_predicates=(
            HealthAtLeast(kind="health_at_least", health=8),
            FoodAtLeast(kind="food_at_least", food=18),
        ),
    )

    assert [predicate.kind for predicate in goal.success_predicates] == [
        "health_at_least",
        "food_at_least",
    ]


def test_food_at_least_bounds_are_inclusive() -> None:
    assert FoodAtLeast(kind="food_at_least", food=0).food == 0
    assert FoodAtLeast(kind="food_at_least", food=20).food == 20


@pytest.mark.parametrize("food", [-1, 21])
def test_food_at_least_rejects_out_of_range_food(food: int) -> None:
    with pytest.raises(ValidationError):
        FoodAtLeast(kind="food_at_least", food=food)
