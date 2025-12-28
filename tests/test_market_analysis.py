"""Tests for market analysis tools."""

from unittest.mock import AsyncMock, patch

import pytest
from mcp.types import TextContent
from toon_format import decode as toon_decode

from prun_mcp.fio import FIOApiError, FIONotFoundError
from prun_mcp.tools.market_analysis import (
    get_market_summary,
    analyze_fill_cost,
    get_price_history_summary,
    get_order_book_depth,
    get_price_history,
)

from tests.conftest import SAMPLE_EXCHANGE_RAT_CI1, SAMPLE_EXCHANGE_BSE_CI1


pytestmark = pytest.mark.anyio


# Sample exchange data with wide spread for warning tests
SAMPLE_EXCHANGE_WIDE_SPREAD = {
    "MaterialTicker": "COF",
    "ExchangeCode": "CI1",
    "Bid": 900.0,
    "Ask": 1000.0,  # 11.1% spread
    "Supply": 5000,
    "Demand": 1000,  # 5x supply/demand ratio
    "MMBuy": None,
    "MMSell": None,
    "BuyingOrders": [
        {"CompanyCode": "ACME", "ItemCount": 20, "ItemCost": 900.0},  # Thin depth
        {"CompanyCode": "BOBS", "ItemCount": 100, "ItemCost": 890.0},
    ],
    "SellingOrders": [
        {"CompanyCode": "CHEM", "ItemCount": 30, "ItemCost": 1000.0},  # Thin depth
        {"CompanyCode": "DELI", "ItemCount": 500, "ItemCost": 1050.0},
    ],
}

# Sample exchange data with Market Maker present
SAMPLE_EXCHANGE_WITH_MM = {
    "MaterialTicker": "RAT",
    "ExchangeCode": "CI1",
    "Bid": 163.0,
    "Ask": 174.0,
    "Supply": 67081,
    "Demand": 380930,
    "MMBuy": 32.0,
    "MMSell": 176.0,
    "BuyingOrders": [
        {"CompanyCode": "ACME", "ItemCount": 2492, "ItemCost": 163.0},
    ],
    "SellingOrders": [
        {"CompanyCode": "CHEM", "ItemCount": 586, "ItemCost": 174.0},
    ],
}

# Sample exchange data with price near MM ceiling
SAMPLE_EXCHANGE_NEAR_MM_CEILING = {
    "MaterialTicker": "RAT",
    "ExchangeCode": "CI1",
    "Bid": 163.0,
    "Ask": 175.0,  # Within 5% of MMSell (176)
    "Supply": 67081,
    "Demand": 380930,
    "MMBuy": 32.0,
    "MMSell": 176.0,
    "BuyingOrders": [
        {"CompanyCode": "ACME", "ItemCount": 2492, "ItemCost": 163.0},
    ],
    "SellingOrders": [
        {"CompanyCode": "CHEM", "ItemCount": 586, "ItemCost": 175.0},
    ],
}

# Sample exchange data with price near MM floor
SAMPLE_EXCHANGE_NEAR_MM_FLOOR = {
    "MaterialTicker": "RAT",
    "ExchangeCode": "CI1",
    "Bid": 33.0,  # Within 5% of MMBuy (32)
    "Ask": 40.0,
    "Supply": 67081,
    "Demand": 380930,
    "MMBuy": 32.0,
    "MMSell": 176.0,
    "BuyingOrders": [
        {"CompanyCode": "ACME", "ItemCount": 100, "ItemCost": 33.0},
    ],
    "SellingOrders": [
        {"CompanyCode": "CHEM", "ItemCount": 100, "ItemCost": 40.0},
    ],
}

# Sample price history from CXPC endpoint
SAMPLE_PRICE_HISTORY = [
    {
        "Interval": "DAY_ONE",
        "DateEpochMs": 1735344000000,  # 2024-12-28
        "Open": 165.0,
        "High": 170.0,
        "Low": 160.0,
        "Close": 166.0,
        "Volume": 83000.0,
        "Traded": 500,
    },
    {
        "Interval": "DAY_ONE",
        "DateEpochMs": 1735257600000,  # 2024-12-27
        "Open": 162.0,
        "High": 168.0,
        "Low": 158.0,
        "Close": 165.0,
        "Volume": 75000.0,
        "Traded": 450,
    },
    {
        "Interval": "DAY_ONE",
        "DateEpochMs": 1735171200000,  # 2024-12-26
        "Open": 160.0,
        "High": 165.0,
        "Low": 155.0,
        "Close": 162.0,
        "Volume": 68000.0,
        "Traded": 400,
    },
]


class TestGetMarketSummary:
    """Tests for get_market_summary tool."""

    async def test_returns_plain_text(self) -> None:
        """Test successful market summary returns plain text."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_RAT_CI1

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_market_summary("RAT", "CI1")

        assert isinstance(result, str)
        assert "RAT on CI1:" in result
        assert "Bid:" in result
        assert "Ask:" in result
        assert "Spread:" in result
        assert "Supply:" in result

    async def test_lowercase_ticker_and_exchange(self) -> None:
        """Test lowercase inputs are converted to uppercase."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_RAT_CI1

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_market_summary("rat", "ci1")

        assert isinstance(result, str)
        mock_client.get_exchange_info.assert_called_once_with("RAT", "CI1")

    async def test_multiple_tickers(self) -> None:
        """Test comma-separated tickers returns multiple sections."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.side_effect = [
            SAMPLE_EXCHANGE_RAT_CI1,
            SAMPLE_EXCHANGE_BSE_CI1,
        ]

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_market_summary("RAT,BSE", "CI1")

        assert isinstance(result, str)
        assert "RAT on CI1:" in result
        assert "BSE on CI1:" in result
        assert "---" in result  # Separator between sections

    async def test_wide_spread_warning(self) -> None:
        """Test wide spread generates warning."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_WIDE_SPREAD

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_market_summary("COF", "CI1")

        assert isinstance(result, str)
        assert "Wide spread" in result
        assert "Warnings:" in result

    async def test_thin_depth_warning(self) -> None:
        """Test thin depth at bid generates warning."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_WIDE_SPREAD

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_market_summary("COF", "CI1")

        assert isinstance(result, str)
        assert "Thin bid depth" in result

    async def test_supply_imbalance_warning(self) -> None:
        """Test heavy supply pressure generates warning."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_WIDE_SPREAD

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_market_summary("COF", "CI1")

        assert isinstance(result, str)
        assert "supply pressure" in result

    async def test_partial_not_found(self) -> None:
        """Test partial matches include not found tickers."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.side_effect = [
            SAMPLE_EXCHANGE_RAT_CI1,
            FIONotFoundError("Exchange", "INVALID.CI1"),
        ]

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_market_summary("RAT,INVALID", "CI1")

        assert isinstance(result, str)
        assert "RAT on CI1:" in result
        assert "Not found: INVALID" in result

    async def test_all_not_found(self) -> None:
        """Test all tickers not found returns error."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.side_effect = FIONotFoundError(
            "Exchange", "INVALID.CI1"
        )

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_market_summary("INVALID", "CI1")

        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "no exchange data" in result[0].text.lower()

    async def test_invalid_exchange(self) -> None:
        """Test invalid exchange returns error."""
        result = await get_market_summary("RAT", "INVALID")

        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "invalid exchange" in result[0].text.lower()

    async def test_api_error(self) -> None:
        """Test API error returns error content."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.side_effect = FIOApiError("Server error")

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_market_summary("RAT", "CI1")

        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "FIO API error" in result[0].text

    async def test_mm_displayed_when_present(self) -> None:
        """Test Market Maker info displayed when present."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_WITH_MM

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_market_summary("RAT", "CI1")

        assert isinstance(result, str)
        assert "MM:" in result
        assert "Buy 32" in result
        assert "Sell 176" in result

    async def test_mm_not_displayed_when_null(self) -> None:
        """Test Market Maker info not displayed when null."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_RAT_CI1

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_market_summary("RAT", "CI1")

        assert isinstance(result, str)
        assert "MM:" not in result

    async def test_mm_ceiling_warning(self) -> None:
        """Test warning when price is near MM ceiling."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_NEAR_MM_CEILING

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_market_summary("RAT", "CI1")

        assert isinstance(result, str)
        assert "MM ceiling" in result
        assert "limited upside" in result

    async def test_mm_floor_warning(self) -> None:
        """Test warning when price is near MM floor."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_NEAR_MM_FLOOR

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_market_summary("RAT", "CI1")

        assert isinstance(result, str)
        assert "MM floor" in result
        assert "limited downside" in result


class TestAnalyzeFillCost:
    """Tests for analyze_fill_cost tool."""

    async def test_returns_toon_encoded_data(self) -> None:
        """Test successful fill analysis returns TOON-encoded data."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_RAT_CI1

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await analyze_fill_cost("RAT", "CI1", 100, "buy")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        assert decoded["ticker"] == "RAT"  # type: ignore[index]
        assert decoded["exchange"] == "CI1"  # type: ignore[index]
        assert decoded["direction"] == "buy"  # type: ignore[index]
        assert decoded["quantity"] == 100  # type: ignore[index]
        assert "can_fill" in decoded  # type: ignore[operator]
        assert "vwap" in decoded  # type: ignore[operator]
        assert "fills" in decoded  # type: ignore[operator]

    async def test_buy_walks_sell_orders(self) -> None:
        """Test buying walks the sell order book ascending."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_RAT_CI1

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await analyze_fill_cost("RAT", "CI1", 100, "buy")

        decoded = toon_decode(result)
        assert decoded["can_fill"] is True  # type: ignore[index]
        assert decoded["best_price"] == 175.0  # type: ignore[index]

    async def test_sell_walks_buy_orders(self) -> None:
        """Test selling walks the buy order book descending."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_RAT_CI1

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await analyze_fill_cost("RAT", "CI1", 50, "sell")

        decoded = toon_decode(result)
        assert decoded["can_fill"] is True  # type: ignore[index]
        assert decoded["best_price"] == 166.0  # type: ignore[index]

    async def test_partial_fill_warning(self) -> None:
        """Test insufficient depth shows partial fill warning."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_RAT_CI1

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            # Try to buy more than available (sample has 250 units for sale)
            result = await analyze_fill_cost("RAT", "CI1", 1000, "buy")

        decoded = toon_decode(result)
        assert decoded["can_fill"] is False  # type: ignore[index]
        assert decoded["unfilled"] > 0  # type: ignore[index]
        assert "warnings" in decoded  # type: ignore[operator]

    async def test_recommendations_generated(self) -> None:
        """Test limit price recommendations are generated."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_RAT_CI1

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await analyze_fill_cost("RAT", "CI1", 200, "buy")

        decoded = toon_decode(result)
        assert "recommendations" in decoded  # type: ignore[operator]
        assert len(decoded["recommendations"]) > 0  # type: ignore[index]

    async def test_invalid_direction(self) -> None:
        """Test invalid direction returns error."""
        result = await analyze_fill_cost("RAT", "CI1", 100, "hold")

        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "invalid direction" in result[0].text.lower()

    async def test_invalid_quantity(self) -> None:
        """Test non-positive quantity returns error."""
        result = await analyze_fill_cost("RAT", "CI1", 0, "buy")

        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "invalid quantity" in result[0].text.lower()

    async def test_not_found(self) -> None:
        """Test ticker not found returns error."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.side_effect = FIONotFoundError(
            "Exchange", "INVALID.CI1"
        )

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await analyze_fill_cost("INVALID", "CI1", 100, "buy")

        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "no exchange data" in result[0].text.lower()


class TestGetPriceHistorySummary:
    """Tests for get_price_history_summary tool."""

    async def test_returns_plain_text(self) -> None:
        """Test successful summary returns plain text."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_RAT_CI1
        mock_client.get_price_history.return_value = SAMPLE_PRICE_HISTORY

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_price_history_summary("RAT", "CI1", days=7)

        assert isinstance(result, str)
        assert "RAT on CI1" in result
        assert "7-day history" in result
        assert "Current:" in result
        assert "Historical:" in result

    async def test_multiple_tickers(self) -> None:
        """Test comma-separated tickers returns multiple sections."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.side_effect = [
            SAMPLE_EXCHANGE_RAT_CI1,
            SAMPLE_EXCHANGE_BSE_CI1,
        ]
        mock_client.get_price_history.side_effect = [
            SAMPLE_PRICE_HISTORY,
            SAMPLE_PRICE_HISTORY,
        ]

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_price_history_summary("RAT,BSE", "CI1")

        assert isinstance(result, str)
        assert "RAT on CI1" in result
        assert "BSE on CI1" in result
        assert "---" in result

    async def test_invalid_days(self) -> None:
        """Test invalid days parameter returns error."""
        result = await get_price_history_summary("RAT", "CI1", days=100)

        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "invalid days" in result[0].text.lower()

    async def test_no_history_available(self) -> None:
        """Test no history data returns appropriate message."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_RAT_CI1
        mock_client.get_price_history.return_value = []

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_price_history_summary("RAT", "CI1")

        assert isinstance(result, str)
        assert "No history available" in result


class TestGetOrderBookDepth:
    """Tests for get_order_book_depth tool."""

    async def test_returns_toon_encoded_data(self) -> None:
        """Test successful order book returns TOON-encoded data."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_RAT_CI1

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_order_book_depth("RAT", "CI1")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        assert decoded["ticker"] == "RAT"  # type: ignore[index]
        assert "sell_orders" in decoded  # type: ignore[operator]
        assert "buy_orders" in decoded  # type: ignore[operator]
        assert "summary" in decoded  # type: ignore[operator]

    async def test_side_filter_sell_only(self) -> None:
        """Test filtering to sell side only."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_RAT_CI1

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_order_book_depth("RAT", "CI1", side="sell")

        decoded = toon_decode(result)
        assert "sell_orders" in decoded  # type: ignore[operator]
        assert "buy_orders" not in decoded  # type: ignore[operator]

    async def test_side_filter_buy_only(self) -> None:
        """Test filtering to buy side only."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_RAT_CI1

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_order_book_depth("RAT", "CI1", side="buy")

        decoded = toon_decode(result)
        assert "buy_orders" in decoded  # type: ignore[operator]
        assert "sell_orders" not in decoded  # type: ignore[operator]

    async def test_multiple_tickers_wraps_in_envelope(self) -> None:
        """Test multiple tickers returns wrapped response."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.side_effect = [
            SAMPLE_EXCHANGE_RAT_CI1,
            SAMPLE_EXCHANGE_BSE_CI1,
        ]

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_order_book_depth("RAT,BSE", "CI1")

        decoded = toon_decode(result)
        assert "order_books" in decoded  # type: ignore[operator]
        assert len(decoded["order_books"]) == 2  # type: ignore[index]

    async def test_multi_ticker_level_cap(self) -> None:
        """Test multiple tickers caps levels at 10."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.side_effect = [
            SAMPLE_EXCHANGE_RAT_CI1,
            SAMPLE_EXCHANGE_BSE_CI1,
        ]

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_order_book_depth("RAT,BSE", "CI1", levels=50)

        decoded = toon_decode(result)
        # Should include levels_returned field showing cap applied
        for book in decoded["order_books"]:  # type: ignore[index]
            assert book["levels_returned"] == 10  # type: ignore[index]

    async def test_cumulative_calculations(self) -> None:
        """Test order levels include cumulative calculations."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_RAT_CI1

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_order_book_depth("RAT", "CI1")

        decoded = toon_decode(result)
        if decoded["sell_orders"]:  # type: ignore[index]
            first_level = decoded["sell_orders"][0]  # type: ignore[index]
            assert "cumulative_units" in first_level  # type: ignore[operator]
            assert "cumulative_cost" in first_level  # type: ignore[operator]
            assert "vwap_to_here" in first_level  # type: ignore[operator]

    async def test_invalid_side(self) -> None:
        """Test invalid side parameter returns error."""
        result = await get_order_book_depth("RAT", "CI1", side="middle")

        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "invalid side" in result[0].text.lower()

    async def test_invalid_levels(self) -> None:
        """Test invalid levels parameter returns error."""
        result = await get_order_book_depth("RAT", "CI1", levels=0)

        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "invalid levels" in result[0].text.lower()

    async def test_summary_includes_mm_fields(self) -> None:
        """Test summary includes Market Maker fields when present."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_WITH_MM

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_order_book_depth("RAT", "CI1")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        summary = decoded["summary"]  # type: ignore[index]
        assert summary["mm_buy"] == 32.0  # type: ignore[index]
        assert summary["mm_sell"] == 176.0  # type: ignore[index]

    async def test_summary_mm_fields_null_when_absent(self) -> None:
        """Test summary MM fields are null when not present in data."""
        mock_client = AsyncMock()
        mock_client.get_exchange_info.return_value = SAMPLE_EXCHANGE_WIDE_SPREAD

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_order_book_depth("COF", "CI1")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        summary = decoded["summary"]  # type: ignore[index]
        assert summary["mm_buy"] is None  # type: ignore[index]
        assert summary["mm_sell"] is None  # type: ignore[index]


class TestGetPriceHistory:
    """Tests for get_price_history tool."""

    async def test_returns_toon_encoded_data(self) -> None:
        """Test successful price history returns TOON-encoded data."""
        mock_client = AsyncMock()
        mock_client.get_price_history.return_value = SAMPLE_PRICE_HISTORY

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_price_history("RAT", "CI1")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        assert decoded["ticker"] == "RAT"  # type: ignore[index]
        assert decoded["exchange"] == "CI1"  # type: ignore[index]
        assert "daily" in decoded  # type: ignore[operator]
        assert "summary" in decoded  # type: ignore[operator]

    async def test_daily_data_format(self) -> None:
        """Test daily data includes expected fields."""
        mock_client = AsyncMock()
        mock_client.get_price_history.return_value = SAMPLE_PRICE_HISTORY

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_price_history("RAT", "CI1")

        decoded = toon_decode(result)
        if decoded["daily"]:  # type: ignore[index]
            candle = decoded["daily"][0]  # type: ignore[index]
            assert "date" in candle  # type: ignore[operator]
            assert "open" in candle  # type: ignore[operator]
            assert "high" in candle  # type: ignore[operator]
            assert "low" in candle  # type: ignore[operator]
            assert "close" in candle  # type: ignore[operator]
            assert "volume" in candle  # type: ignore[operator]

    async def test_summary_statistics(self) -> None:
        """Test summary includes statistics."""
        mock_client = AsyncMock()
        mock_client.get_price_history.return_value = SAMPLE_PRICE_HISTORY

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_price_history("RAT", "CI1")

        decoded = toon_decode(result)
        summary = decoded["summary"]  # type: ignore[index]
        assert "avg_price" in summary  # type: ignore[operator]
        assert "high" in summary  # type: ignore[operator]
        assert "low" in summary  # type: ignore[operator]
        assert "total_volume" in summary  # type: ignore[operator]

    async def test_multiple_tickers_wraps_in_envelope(self) -> None:
        """Test multiple tickers returns wrapped response."""
        mock_client = AsyncMock()
        mock_client.get_price_history.side_effect = [
            SAMPLE_PRICE_HISTORY,
            SAMPLE_PRICE_HISTORY,
        ]

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_price_history("RAT,BSE", "CI1")

        decoded = toon_decode(result)
        assert "histories" in decoded  # type: ignore[operator]
        assert len(decoded["histories"]) == 2  # type: ignore[index]

    async def test_not_found(self) -> None:
        """Test ticker not found returns error."""
        mock_client = AsyncMock()
        mock_client.get_price_history.side_effect = FIONotFoundError(
            "PriceHistory", "INVALID.CI1"
        )

        with patch(
            "prun_mcp.tools.market_analysis.get_fio_client",
            return_value=mock_client,
        ):
            result = await get_price_history("INVALID", "CI1")

        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "no price history" in result[0].text.lower()

    async def test_invalid_days(self) -> None:
        """Test invalid days parameter returns error."""
        result = await get_price_history("RAT", "CI1", days=0)

        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "invalid days" in result[0].text.lower()
