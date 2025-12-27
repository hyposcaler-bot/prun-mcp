"""Tests for workforce module."""

from prun_mcp.resources.workforce import (
    HABITATION_CAPACITY,
    VALID_HABITATION,
    WORKFORCE_TYPES,
    format_habitation_capacity,
    get_habitation_capacity,
    get_workforce_types,
)


class TestWorkforceTypes:
    """Tests for workforce types data."""

    def test_workforce_types_count(self) -> None:
        """Should have 5 workforce types."""
        assert len(WORKFORCE_TYPES) == 5

    def test_workforce_types_order(self) -> None:
        """Should be ordered from lowest to highest tier."""
        expected = ["Pioneers", "Settlers", "Technicians", "Engineers", "Scientists"]
        assert WORKFORCE_TYPES == expected

    def test_get_workforce_types_returns_string(self) -> None:
        """Resource function should return a string."""
        result = get_workforce_types()
        assert isinstance(result, str)

    def test_get_workforce_types_contains_all(self) -> None:
        """Resource should contain all workforce types."""
        result = get_workforce_types()
        for wf_type in WORKFORCE_TYPES:
            assert wf_type in result


class TestHabitationCapacity:
    """Tests for habitation capacity data."""

    def test_valid_habitation_matches_keys(self) -> None:
        """VALID_HABITATION should match HABITATION_CAPACITY keys."""
        assert VALID_HABITATION == set(HABITATION_CAPACITY.keys())

    def test_habitation_count(self) -> None:
        """Should have 9 habitation buildings."""
        assert len(HABITATION_CAPACITY) == 9

    def test_single_type_buildings_have_100_capacity(self) -> None:
        """Single-type buildings (HB1-HB5) should have 100 capacity."""
        for building in ["HB1", "HB2", "HB3", "HB4", "HB5"]:
            cap = HABITATION_CAPACITY[building]
            assert sum(cap.values()) == 100
            assert len(cap) == 1

    def test_mixed_type_buildings_have_150_capacity(self) -> None:
        """Mixed-type buildings should have 150 total capacity."""
        for building in ["HBB", "HBC", "HBM", "HBL"]:
            cap = HABITATION_CAPACITY[building]
            assert sum(cap.values()) == 150
            assert len(cap) == 2

    def test_expected_buildings(self) -> None:
        """Should have the expected building tickers."""
        expected = {"HB1", "HB2", "HB3", "HB4", "HB5", "HBB", "HBC", "HBM", "HBL"}
        assert VALID_HABITATION == expected

    def test_workforce_types_in_capacity(self) -> None:
        """All capacity values should use valid workforce types."""
        valid_types = set(WORKFORCE_TYPES)
        for building, capacity in HABITATION_CAPACITY.items():
            for wf_type in capacity:
                assert wf_type in valid_types, f"{building} has invalid type {wf_type}"


class TestFormatHabitationCapacity:
    """Tests for format_habitation_capacity function."""

    def test_returns_string(self) -> None:
        """Should return a string."""
        result = format_habitation_capacity()
        assert isinstance(result, str)

    def test_contains_header(self) -> None:
        """Should contain header row."""
        result = format_habitation_capacity()
        assert "Building" in result
        assert "Capacity" in result

    def test_contains_all_buildings(self) -> None:
        """Should contain all building tickers."""
        result = format_habitation_capacity()
        for building in HABITATION_CAPACITY:
            assert building in result

    def test_get_habitation_capacity_matches_format(self) -> None:
        """Resource function should return same as format function."""
        assert get_habitation_capacity() == format_habitation_capacity()
