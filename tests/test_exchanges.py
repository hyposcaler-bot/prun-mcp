"""Tests for exchanges module."""

from prun_mcp.resources.exchanges import (
    EXCHANGES,
    VALID_EXCHANGES,
    format_exchange_list,
)


class TestExchangeData:
    """Tests for exchange data constants."""

    def test_valid_exchanges_matches_keys(self) -> None:
        """VALID_EXCHANGES should match EXCHANGES keys."""
        assert VALID_EXCHANGES == set(EXCHANGES.keys())

    def test_all_exchanges_have_names(self) -> None:
        """All exchanges should have names."""
        for code, name in EXCHANGES.items():
            assert isinstance(name, str), f"{code} name should be string"
            assert len(name) > 0, f"{code} name should not be empty"

    def test_exchange_count(self) -> None:
        """Should have 6 exchanges."""
        assert len(EXCHANGES) == 6

    def test_expected_exchanges(self) -> None:
        """Should have the expected exchange codes."""
        expected = {"AI1", "CI1", "CI2", "IC1", "NC1", "NC2"}
        assert VALID_EXCHANGES == expected


class TestFormatExchangeList:
    """Tests for format_exchange_list function."""

    def test_returns_string(self) -> None:
        """Should return a string."""
        result = format_exchange_list()
        assert isinstance(result, str)

    def test_contains_header(self) -> None:
        """Should contain header row."""
        result = format_exchange_list()
        assert "Code" in result
        assert "Name" in result

    def test_contains_all_exchanges(self) -> None:
        """Should contain all exchange codes."""
        result = format_exchange_list()
        for code in EXCHANGES:
            assert code in result

    def test_contains_all_names(self) -> None:
        """Should contain all exchange names."""
        result = format_exchange_list()
        for name in EXCHANGES.values():
            assert name in result
