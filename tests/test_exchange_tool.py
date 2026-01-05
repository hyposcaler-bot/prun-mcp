"""Tests for exchange tools."""

from unittest.mock import AsyncMock, patch

import pytest
from mcp.types import TextContent
from toon_format import decode as toon_decode

from prun_mcp.fio import FIOApiError, FIONotFoundError
from prun_mcp.tools.exchange import get_exchange_all, get_exchange_prices

from tests.conftest import (
    SAMPLE_EXCHANGE_ALL,
    SAMPLE_EXCHANGE_BSE_CI1,
    SAMPLE_EXCHANGE_RAT_CI1,
)


pytestmark = pytest.mark.anyio


class TestGetExchangePrices:
    """Tests for get_exchange_prices tool."""

    async def test_returns_toon_encoded_data(self) -> None:
        """Test successful exchange lookup returns TOON-encoded data."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_RAT_CI1

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            result = await get_exchange_prices("RAT", "CI1")

        assert isinstance(result, str)

        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        assert "prices" in decoded  # type: ignore[operator]

        prices = decoded["prices"]  # type: ignore[index]
        assert len(prices) == 1

        price = prices[0]
        assert price["MaterialTicker"] == "RAT"
        assert price["ExchangeCode"] == "CI1"
        assert "BuyingOrders" in price
        assert "SellingOrders" in price

    async def test_lowercase_ticker_and_exchange(self) -> None:
        """Test that lowercase tickers/exchanges are converted to uppercase."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_RAT_CI1

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            result = await get_exchange_prices("rat", "ci1")

        assert isinstance(result, str)
        mock_client.get_exchange_info.assert_called_once_with("RAT", "CI1")

    async def test_multiple_tickers(self) -> None:
        """Test comma-separated tickers returns multiple results."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.side_effect = [
            SAMPLE_EXCHANGE_RAT_CI1,
            SAMPLE_EXCHANGE_BSE_CI1,
        ]

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            result = await get_exchange_prices("RAT,BSE", "CI1")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        prices = decoded["prices"]  # type: ignore[index]
        assert len(prices) == 2

        tickers = [p["MaterialTicker"] for p in prices]  # type: ignore[index]
        assert "RAT" in tickers
        assert "BSE" in tickers

    async def test_multiple_tickers_with_spaces(self) -> None:
        """Test comma-separated tickers with spaces are handled."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.side_effect = [
            SAMPLE_EXCHANGE_RAT_CI1,
            SAMPLE_EXCHANGE_BSE_CI1,
        ]

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            result = await get_exchange_prices("RAT, BSE", "CI1")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        prices = decoded["prices"]  # type: ignore[index]
        assert len(prices) == 2

    async def test_partial_match_includes_not_found(self) -> None:
        """Test partial matches return found prices plus not_found list."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.side_effect = [
            SAMPLE_EXCHANGE_RAT_CI1,
            FIONotFoundError("Exchange", "INVALID.CI1"),
            SAMPLE_EXCHANGE_BSE_CI1,
        ]

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            result = await get_exchange_prices("RAT,INVALID,BSE", "CI1")

        assert isinstance(result, str)
        decoded = toon_decode(result)

        # Should have found prices
        prices = decoded["prices"]  # type: ignore[index]
        assert len(prices) == 2
        tickers = [p["MaterialTicker"] for p in prices]  # type: ignore[index]
        assert "RAT" in tickers
        assert "BSE" in tickers

        # Should have not_found list (format: "TICKER.EXCHANGE")
        not_found = decoded["not_found"]  # type: ignore[index]
        assert "INVALID.CI1" in not_found

    async def test_all_not_found(self) -> None:
        """Test all tickers not found returns error content."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.side_effect = [
            FIONotFoundError("Exchange", "INVALID1.CI1"),
            FIONotFoundError("Exchange", "INVALID2.CI1"),
        ]

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            result = await get_exchange_prices("INVALID1,INVALID2", "CI1")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "no exchange data found" in result[0].text.lower()
        assert "INVALID1" in result[0].text
        assert "INVALID2" in result[0].text

    async def test_invalid_exchange_returns_error(self) -> None:
        """Test invalid exchange code returns error content."""
        result = await get_exchange_prices("RAT", "INVALID")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid exchange" in result[0].text.lower()
        assert "AI1" in result[0].text  # Should list valid exchanges

    async def test_api_error_returns_error_content(self) -> None:
        """Test FIO API error returns error content."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.side_effect = FIOApiError(
            "Server error", status_code=500
        )

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            result = await get_exchange_prices("RAT", "CI1")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "FIO API error" in result[0].text


class TestGetExchangeAll:
    """Tests for get_exchange_all tool."""

    async def test_returns_filtered_prices(self) -> None:
        """Test returns only prices for specified exchange."""
        mock_client = AsyncMock()
        mock_client.get_all_exchange_data.return_value = SAMPLE_EXCHANGE_ALL

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            result = await get_exchange_all("CI1")

        assert isinstance(result, str)

        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        assert "prices" in decoded  # type: ignore[operator]

        prices = decoded["prices"]  # type: ignore[index]
        # SAMPLE_EXCHANGE_ALL has 2 CI1 entries and 1 NC1 entry
        assert len(prices) == 2

        for price in prices:
            assert price["ExchangeCode"] == "CI1"  # type: ignore[index]

    async def test_lowercase_exchange(self) -> None:
        """Test that lowercase exchange is converted to uppercase."""
        mock_client = AsyncMock()
        mock_client.get_all_exchange_data.return_value = SAMPLE_EXCHANGE_ALL

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            result = await get_exchange_all("ci1")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        prices = decoded["prices"]  # type: ignore[index]
        assert len(prices) == 2

    async def test_different_exchange(self) -> None:
        """Test filtering to different exchange."""
        mock_client = AsyncMock()
        mock_client.get_all_exchange_data.return_value = SAMPLE_EXCHANGE_ALL

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            result = await get_exchange_all("NC1")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        prices = decoded["prices"]  # type: ignore[index]
        # SAMPLE_EXCHANGE_ALL has 1 NC1 entry
        assert len(prices) == 1
        assert prices[0]["ExchangeCode"] == "NC1"  # type: ignore[index]

    async def test_invalid_exchange_returns_error(self) -> None:
        """Test invalid exchange code returns error content."""
        result = await get_exchange_all("INVALID")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid exchange" in result[0].text.lower()
        assert "AI1" in result[0].text  # Should list valid exchanges

    async def test_api_error_returns_error_content(self) -> None:
        """Test FIO API error returns error content."""
        mock_client = AsyncMock()
        mock_client.get_all_exchange_data.side_effect = FIOApiError(
            "Server error", status_code=500
        )

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            result = await get_exchange_all("CI1")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "FIO API error" in result[0].text

    async def test_multiple_exchanges(self) -> None:
        """Test comma-separated exchanges returns prices from all."""
        mock_client = AsyncMock()
        mock_client.get_all_exchange_data.return_value = SAMPLE_EXCHANGE_ALL

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            result = await get_exchange_all("CI1,NC1")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        prices = decoded["prices"]  # type: ignore[index]
        # SAMPLE_EXCHANGE_ALL has 2 CI1 entries and 1 NC1 entry
        assert len(prices) == 3

        exchange_codes = [p["ExchangeCode"] for p in prices]  # type: ignore[index]
        assert "CI1" in exchange_codes
        assert "NC1" in exchange_codes

    async def test_multiple_exchanges_with_spaces(self) -> None:
        """Test comma-separated exchanges with spaces are handled."""
        mock_client = AsyncMock()
        mock_client.get_all_exchange_data.return_value = SAMPLE_EXCHANGE_ALL

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            result = await get_exchange_all("CI1, NC1")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        prices = decoded["prices"]  # type: ignore[index]
        assert len(prices) == 3


class TestGetExchangePricesMultiExchange:
    """Tests for get_exchange_prices with multiple exchanges."""

    async def test_single_ticker_multiple_exchanges(self) -> None:
        """Test single ticker with multiple exchanges."""
        mock_client = AsyncMock()
        # RAT on CI1, then RAT on NC1
        rat_nc1 = dict(SAMPLE_EXCHANGE_RAT_CI1)
        rat_nc1["ExchangeCode"] = "NC1"
        mock_client.get_exchange_info.side_effect = [SAMPLE_EXCHANGE_RAT_CI1, rat_nc1]

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            result = await get_exchange_prices("RAT", "CI1,NC1")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        prices = decoded["prices"]  # type: ignore[index]
        assert len(prices) == 2

        exchange_codes = [p["ExchangeCode"] for p in prices]  # type: ignore[index]
        assert "CI1" in exchange_codes
        assert "NC1" in exchange_codes

    async def test_multiple_tickers_multiple_exchanges(self) -> None:
        """Test multiple tickers with multiple exchanges (cross-product)."""
        mock_client = AsyncMock()
        # RAT.CI1, RAT.NC1, BSE.CI1, BSE.NC1
        rat_nc1 = dict(SAMPLE_EXCHANGE_RAT_CI1)
        rat_nc1["ExchangeCode"] = "NC1"
        bse_nc1 = dict(SAMPLE_EXCHANGE_BSE_CI1)
        bse_nc1["ExchangeCode"] = "NC1"
        mock_client.get_exchange_info.side_effect = [
            SAMPLE_EXCHANGE_RAT_CI1,
            rat_nc1,
            SAMPLE_EXCHANGE_BSE_CI1,
            bse_nc1,
        ]

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            result = await get_exchange_prices("RAT,BSE", "CI1,NC1")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        prices = decoded["prices"]  # type: ignore[index]
        assert len(prices) == 4

        # Check we have all combinations
        combos = [(p["MaterialTicker"], p["ExchangeCode"]) for p in prices]  # type: ignore[index]
        assert ("RAT", "CI1") in combos
        assert ("RAT", "NC1") in combos
        assert ("BSE", "CI1") in combos
        assert ("BSE", "NC1") in combos

    async def test_partial_not_found_multi_exchange(self) -> None:
        """Test partial not found with multiple exchanges."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.side_effect = [
            SAMPLE_EXCHANGE_RAT_CI1,
            FIONotFoundError("Exchange", "RAT.NC1"),
        ]

        with patch("prun_mcp.fio.get_fio_client", return_value=mock_client):
            result = await get_exchange_prices("RAT", "CI1,NC1")

        assert isinstance(result, str)
        decoded = toon_decode(result)

        prices = decoded["prices"]  # type: ignore[index]
        assert len(prices) == 1
        assert prices[0]["ExchangeCode"] == "CI1"  # type: ignore[index]

        not_found = decoded["not_found"]  # type: ignore[index]
        assert "RAT.NC1" in not_found

    async def test_invalid_exchange_in_list(self) -> None:
        """Test that invalid exchange in comma-separated list returns error."""
        result = await get_exchange_prices("RAT", "CI1,INVALID")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "invalid exchange" in result[0].text.lower()
        assert "INVALID" in result[0].text
