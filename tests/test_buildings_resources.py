"""Tests for building efficiency resources."""

from prun_mcp.resources.buildings import (
    get_efficiency_cogc,
    get_efficiency_condition,
    get_efficiency_experts,
    get_efficiency_overview,
    get_efficiency_workforce,
)


class TestEfficiencyResources:
    """Tests for efficiency documentation resources."""

    def test_overview_contains_formula(self) -> None:
        """Overview should contain the efficiency formula."""
        result = get_efficiency_overview()
        assert "Efficiency = Base" in result
        assert "Expert%" in result
        assert "CoGC%" in result

    def test_overview_lists_factors(self) -> None:
        """Overview should list all four efficiency factors."""
        result = get_efficiency_overview()
        assert "Workforce Satisfaction" in result
        assert "Building Condition" in result
        assert "Experts" in result
        assert "CoGC Programs" in result

    def test_workforce_resource(self) -> None:
        """Workforce resource should explain satisfaction mechanics."""
        result = get_efficiency_workforce()
        assert "Workforce Satisfaction" in result
        assert "100%" in result
        assert "consumables" in result.lower()

    def test_experts_resource(self) -> None:
        """Experts resource should list expert types and bonuses."""
        result = get_efficiency_experts()
        assert "FOOD_INDUSTRIES" in result
        assert "28.4%" in result
        assert "Diminishing returns" in result

    def test_cogc_resource(self) -> None:
        """CoGC resource should list ADVERTISING programs."""
        result = get_efficiency_cogc()
        assert "ADVERTISING_FOOD_INDUSTRIES" in result
        assert "25%" in result
        assert "get_planet_info" in result

    def test_condition_resource(self) -> None:
        """Condition resource should explain maintenance."""
        result = get_efficiency_condition()
        assert "Building Condition" in result
        assert "Maintenance" in result
        assert "Degradation" in result
