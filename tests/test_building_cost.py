"""Tests for calculate_building_cost tool."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from mcp.types import TextContent
from toon_format import decode as toon_decode

from prun_mcp.cache import BuildingsCache
from prun_mcp.fio import FIOApiError, FIONotFoundError
from prun_mcp.tools.building_cost import calculate_building_cost


pytestmark = pytest.mark.anyio


# Sample building data
SAMPLE_FP_BUILDING = {
    "BuildingId": "fp-building-id",
    "Name": "foodProcessor",
    "Ticker": "FP",
    "Expertise": "FOOD_INDUSTRIES",
    "Pioneers": 40,
    "Settlers": 0,
    "Technicians": 0,
    "Engineers": 0,
    "Scientists": 0,
    "AreaCost": 12,
    "BuildingCosts": [
        {"CommodityTicker": "BSE", "Amount": 3},
        {"CommodityTicker": "BBH", "Amount": 3},
        {"CommodityTicker": "BDE", "Amount": 3},
    ],
}

SAMPLE_FRM_BUILDING = {
    "BuildingId": "frm-building-id",
    "Name": "farmland",
    "Ticker": "FRM",
    "Expertise": "AGRICULTURE",
    "Pioneers": 40,
    "Settlers": 0,
    "Technicians": 0,
    "Engineers": 0,
    "Scientists": 0,
    "AreaCost": 30,
    "BuildingCosts": [
        {"CommodityTicker": "BSE", "Amount": 4},
        {"CommodityTicker": "BBH", "Amount": 4},
    ],
}

# Sample planet data - Rocky, normal conditions (Promitor-like)
SAMPLE_ROCKY_PLANET = {
    "PlanetId": "rocky-planet-id",
    "PlanetNaturalId": "VH-331a",
    "PlanetName": "Promitor",
    "Surface": True,
    "Pressure": 1.0,
    "Gravity": 0.89,
    "Temperature": 16.0,
    "Fertility": 0.4,
}

# Gaseous planet
SAMPLE_GASEOUS_PLANET = {
    "PlanetId": "gaseous-planet-id",
    "PlanetNaturalId": "XK-456b",
    "PlanetName": "GasWorld",
    "Surface": False,
    "Pressure": 1.5,
    "Gravity": 1.0,
    "Temperature": 25.0,
    "Fertility": -1.0,
}

# Cold planet (low temperature)
SAMPLE_COLD_PLANET = {
    "PlanetId": "cold-planet-id",
    "PlanetNaturalId": "FM-123c",
    "PlanetName": "Frostheim",
    "Surface": True,
    "Pressure": 1.0,
    "Gravity": 1.0,
    "Temperature": -50.0,
    "Fertility": 0.0,
}

# Low pressure planet
SAMPLE_LOW_PRESSURE_PLANET = {
    "PlanetId": "low-pressure-id",
    "PlanetNaturalId": "LP-789d",
    "PlanetName": "ThinAir",
    "Surface": True,
    "Pressure": 0.1,
    "Gravity": 1.0,
    "Temperature": 20.0,
    "Fertility": 0.0,
}

# High gravity planet
SAMPLE_HIGH_GRAVITY_PLANET = {
    "PlanetId": "high-gravity-id",
    "PlanetNaturalId": "HG-111e",
    "PlanetName": "HeavyWorld",
    "Surface": True,
    "Pressure": 1.0,
    "Gravity": 3.0,
    "Temperature": 20.0,
    "Fertility": 0.0,
}

# Low gravity planet
SAMPLE_LOW_GRAVITY_PLANET = {
    "PlanetId": "low-gravity-id",
    "PlanetNaturalId": "LG-222f",
    "PlanetName": "LightWorld",
    "Surface": True,
    "Pressure": 1.0,
    "Gravity": 0.1,
    "Temperature": 20.0,
    "Fertility": 0.0,
}

# Hot planet
SAMPLE_HOT_PLANET = {
    "PlanetId": "hot-planet-id",
    "PlanetNaturalId": "HT-333g",
    "PlanetName": "Inferno",
    "Surface": True,
    "Pressure": 1.0,
    "Gravity": 1.0,
    "Temperature": 100.0,
    "Fertility": 0.0,
}

# Infertile planet (for testing agriculture building error)
# Note: None means no fertility, negative values are valid (reduced efficiency)
SAMPLE_INFERTILE_PLANET = {
    "PlanetId": "infertile-id",
    "PlanetNaturalId": "IF-444h",
    "PlanetName": "Barren",
    "Surface": True,
    "Pressure": 1.0,
    "Gravity": 1.0,
    "Temperature": 20.0,
    "Fertility": None,
}


def create_buildings_cache(tmp_path: Path) -> BuildingsCache:
    """Create a cache populated with test buildings."""
    cache = BuildingsCache(cache_dir=tmp_path)
    cache.refresh([SAMPLE_FP_BUILDING, SAMPLE_FRM_BUILDING])
    return cache


def mock_prices() -> dict[str, float]:
    """Return mock prices for testing."""
    return {
        "BSE": 120.0,
        "BBH": 450.0,
        "BDE": 800.0,
        "MCG": 12.0,
        "AEF": 2500.0,
        "INS": 15.0,
        "SEA": 300.0,
        "BL": 1500.0,
        "MGC": 500.0,
        "TSH": 3000.0,
        "HSE": 4000.0,
    }


class TestCalculateBuildingCost:
    """Tests for calculate_building_cost tool."""

    async def test_rocky_planet_mcg(self, tmp_path: Path) -> None:
        """Test building on rocky planet includes MCG infrastructure."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        mock_client = AsyncMock()
        mock_client.get_planet.return_value = SAMPLE_ROCKY_PLANET

        async def mock_ensure_cache() -> BuildingsCache:
            return buildings_cache

        with (
            patch(
                "prun_mcp.tools.building_cost.ensure_buildings_cache",
                mock_ensure_cache,
            ),
            patch(
                "prun_mcp.tools.building_cost.get_fio_client",
                return_value=mock_client,
            ),
        ):
            result = await calculate_building_cost(
                building_ticker="FP",
                planet="Promitor",
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert isinstance(decoded, dict)

        # Check structure
        assert decoded["building"] == "FP"  # type: ignore[index]
        assert decoded["planet_name"] == "Promitor"  # type: ignore[index]
        assert decoded["area"] == 12  # type: ignore[index]
        assert "rocky" in decoded["environment"]  # type: ignore[index]

        # Check materials include MCG (area * 4 = 48)
        materials = decoded["materials"]  # type: ignore[index]
        mcg_entry = next((m for m in materials if m["material"] == "MCG"), None)  # type: ignore[union-attr]
        assert mcg_entry is not None
        assert mcg_entry["amount"] == 48  # 12 * 4  # type: ignore[index]

        # Check base building costs present
        bse_entry = next((m for m in materials if m["material"] == "BSE"), None)  # type: ignore[union-attr]
        assert bse_entry is not None
        assert bse_entry["amount"] == 3  # type: ignore[index]

    async def test_gaseous_planet_aef(self, tmp_path: Path) -> None:
        """Test building on gaseous planet includes AEF infrastructure."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        mock_client = AsyncMock()
        mock_client.get_planet.return_value = SAMPLE_GASEOUS_PLANET

        async def mock_ensure_cache() -> BuildingsCache:
            return buildings_cache

        with (
            patch(
                "prun_mcp.tools.building_cost.ensure_buildings_cache",
                mock_ensure_cache,
            ),
            patch(
                "prun_mcp.tools.building_cost.get_fio_client",
                return_value=mock_client,
            ),
        ):
            result = await calculate_building_cost(
                building_ticker="FP",
                planet="GasWorld",
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)

        assert "gaseous" in decoded["environment"]  # type: ignore[index]

        # Check materials include AEF (ceil(12/3) = 4)
        materials = decoded["materials"]  # type: ignore[index]
        aef_entry = next((m for m in materials if m["material"] == "AEF"), None)  # type: ignore[union-attr]
        assert aef_entry is not None
        assert aef_entry["amount"] == 4  # ceil(12/3)  # type: ignore[index]

    async def test_cold_planet_ins(self, tmp_path: Path) -> None:
        """Test building on cold planet includes INS infrastructure."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        mock_client = AsyncMock()
        mock_client.get_planet.return_value = SAMPLE_COLD_PLANET

        async def mock_ensure_cache() -> BuildingsCache:
            return buildings_cache

        with (
            patch(
                "prun_mcp.tools.building_cost.ensure_buildings_cache",
                mock_ensure_cache,
            ),
            patch(
                "prun_mcp.tools.building_cost.get_fio_client",
                return_value=mock_client,
            ),
        ):
            result = await calculate_building_cost(
                building_ticker="FP",
                planet="Frostheim",
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)

        assert "cold" in decoded["environment"]  # type: ignore[index]

        # Check materials include INS (area * 10 = 120)
        materials = decoded["materials"]  # type: ignore[index]
        ins_entry = next((m for m in materials if m["material"] == "INS"), None)  # type: ignore[union-attr]
        assert ins_entry is not None
        assert ins_entry["amount"] == 120  # 12 * 10  # type: ignore[index]

    async def test_low_pressure_planet_sea(self, tmp_path: Path) -> None:
        """Test building on low-pressure planet includes SEA infrastructure."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        mock_client = AsyncMock()
        mock_client.get_planet.return_value = SAMPLE_LOW_PRESSURE_PLANET

        async def mock_ensure_cache() -> BuildingsCache:
            return buildings_cache

        with (
            patch(
                "prun_mcp.tools.building_cost.ensure_buildings_cache",
                mock_ensure_cache,
            ),
            patch(
                "prun_mcp.tools.building_cost.get_fio_client",
                return_value=mock_client,
            ),
        ):
            result = await calculate_building_cost(
                building_ticker="FP",
                planet="ThinAir",
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)

        assert "low-pressure" in decoded["environment"]  # type: ignore[index]

        # Check materials include SEA (area * 1 = 12)
        materials = decoded["materials"]  # type: ignore[index]
        sea_entry = next((m for m in materials if m["material"] == "SEA"), None)  # type: ignore[union-attr]
        assert sea_entry is not None
        assert sea_entry["amount"] == 12  # 12 * 1  # type: ignore[index]

    async def test_high_gravity_planet_bl(self, tmp_path: Path) -> None:
        """Test building on high-gravity planet includes BL infrastructure."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        mock_client = AsyncMock()
        mock_client.get_planet.return_value = SAMPLE_HIGH_GRAVITY_PLANET

        async def mock_ensure_cache() -> BuildingsCache:
            return buildings_cache

        with (
            patch(
                "prun_mcp.tools.building_cost.ensure_buildings_cache",
                mock_ensure_cache,
            ),
            patch(
                "prun_mcp.tools.building_cost.get_fio_client",
                return_value=mock_client,
            ),
        ):
            result = await calculate_building_cost(
                building_ticker="FP",
                planet="HeavyWorld",
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)

        assert "high-gravity" in decoded["environment"]  # type: ignore[index]

        # Check materials include BL (flat 1)
        materials = decoded["materials"]  # type: ignore[index]
        bl_entry = next((m for m in materials if m["material"] == "BL"), None)  # type: ignore[union-attr]
        assert bl_entry is not None
        assert bl_entry["amount"] == 1  # type: ignore[index]

    async def test_low_gravity_planet_mgc(self, tmp_path: Path) -> None:
        """Test building on low-gravity planet includes MGC infrastructure."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        mock_client = AsyncMock()
        mock_client.get_planet.return_value = SAMPLE_LOW_GRAVITY_PLANET

        async def mock_ensure_cache() -> BuildingsCache:
            return buildings_cache

        with (
            patch(
                "prun_mcp.tools.building_cost.ensure_buildings_cache",
                mock_ensure_cache,
            ),
            patch(
                "prun_mcp.tools.building_cost.get_fio_client",
                return_value=mock_client,
            ),
        ):
            result = await calculate_building_cost(
                building_ticker="FP",
                planet="LightWorld",
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)

        assert "low-gravity" in decoded["environment"]  # type: ignore[index]

        # Check materials include MGC (flat 1)
        materials = decoded["materials"]  # type: ignore[index]
        mgc_entry = next((m for m in materials if m["material"] == "MGC"), None)  # type: ignore[union-attr]
        assert mgc_entry is not None
        assert mgc_entry["amount"] == 1  # type: ignore[index]

    async def test_hot_planet_tsh(self, tmp_path: Path) -> None:
        """Test building on hot planet includes TSH infrastructure."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        mock_client = AsyncMock()
        mock_client.get_planet.return_value = SAMPLE_HOT_PLANET

        async def mock_ensure_cache() -> BuildingsCache:
            return buildings_cache

        with (
            patch(
                "prun_mcp.tools.building_cost.ensure_buildings_cache",
                mock_ensure_cache,
            ),
            patch(
                "prun_mcp.tools.building_cost.get_fio_client",
                return_value=mock_client,
            ),
        ):
            result = await calculate_building_cost(
                building_ticker="FP",
                planet="Inferno",
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)

        assert "hot" in decoded["environment"]  # type: ignore[index]

        # Check materials include TSH (flat 1)
        materials = decoded["materials"]  # type: ignore[index]
        tsh_entry = next((m for m in materials if m["material"] == "TSH"), None)  # type: ignore[union-attr]
        assert tsh_entry is not None
        assert tsh_entry["amount"] == 1  # type: ignore[index]

    async def test_soil_farm_on_infertile_planet_error(self, tmp_path: Path) -> None:
        """Test that FRM/ORC on infertile planet returns error (HYF is OK)."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        mock_client = AsyncMock()
        mock_client.get_planet.return_value = SAMPLE_INFERTILE_PLANET

        async def mock_ensure_cache() -> BuildingsCache:
            return buildings_cache

        with (
            patch(
                "prun_mcp.tools.building_cost.ensure_buildings_cache",
                mock_ensure_cache,
            ),
            patch(
                "prun_mcp.tools.building_cost.get_fio_client",
                return_value=mock_client,
            ),
        ):
            result = await calculate_building_cost(
                building_ticker="FRM",
                planet="Barren",
            )

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "fertility" in result[0].text.lower()
        assert "FRM" in result[0].text

    async def test_with_exchange_pricing(self, tmp_path: Path) -> None:
        """Test building cost with exchange pricing."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        mock_client = AsyncMock()
        mock_client.get_planet.return_value = SAMPLE_ROCKY_PLANET
        prices = mock_prices()

        async def mock_ensure_cache() -> BuildingsCache:
            return buildings_cache

        async def mock_fetch_prices(
            tickers: list[str], exchange: str
        ) -> dict[str, dict[str, float | None]]:
            return {t: {"ask": prices.get(t), "bid": prices.get(t)} for t in tickers}

        with (
            patch(
                "prun_mcp.tools.building_cost.ensure_buildings_cache",
                mock_ensure_cache,
            ),
            patch(
                "prun_mcp.tools.building_cost.get_fio_client",
                return_value=mock_client,
            ),
            patch(
                "prun_mcp.tools.building_cost.fetch_prices",
                mock_fetch_prices,
            ),
        ):
            result = await calculate_building_cost(
                building_ticker="FP",
                planet="Promitor",
                exchange="CI1",
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)

        # Check exchange is included
        assert decoded["exchange"] == "CI1"  # type: ignore[index]
        assert "total_cost" in decoded  # type: ignore[operator]

        # Check materials have prices and costs
        materials = decoded["materials"]  # type: ignore[index]
        for mat in materials:  # type: ignore[union-attr]
            assert "price" in mat  # type: ignore[operator]
            assert "cost" in mat  # type: ignore[operator]
            if mat["price"] is not None:  # type: ignore[index]
                assert mat["cost"] == mat["price"] * mat["amount"]  # type: ignore[index]

        # Verify total cost calculation
        total = sum(m["cost"] for m in materials if m["cost"] is not None)  # type: ignore[union-attr]
        assert decoded["total_cost"] == round(total, 2)  # type: ignore[index]

    async def test_invalid_exchange(self, tmp_path: Path) -> None:
        """Test building cost with invalid exchange returns error."""
        result = await calculate_building_cost(
            building_ticker="FP",
            planet="Promitor",
            exchange="INVALID",
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Invalid exchange" in result[0].text
        assert "CI1" in result[0].text  # Shows valid exchanges

    async def test_building_not_found(self, tmp_path: Path) -> None:
        """Test building not found returns error."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")

        async def mock_ensure_cache() -> BuildingsCache:
            return buildings_cache

        with patch(
            "prun_mcp.tools.building_cost.ensure_buildings_cache",
            mock_ensure_cache,
        ):
            result = await calculate_building_cost(
                building_ticker="NONEXISTENT",
                planet="Promitor",
            )

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "not found" in result[0].text.lower()
        assert "NONEXISTENT" in result[0].text

    async def test_planet_not_found(self, tmp_path: Path) -> None:
        """Test planet not found returns error."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        mock_client = AsyncMock()
        mock_client.get_planet.side_effect = FIONotFoundError("Planet", "FakePlanet")

        async def mock_ensure_cache() -> BuildingsCache:
            return buildings_cache

        with (
            patch(
                "prun_mcp.tools.building_cost.ensure_buildings_cache",
                mock_ensure_cache,
            ),
            patch(
                "prun_mcp.tools.building_cost.get_fio_client",
                return_value=mock_client,
            ),
        ):
            result = await calculate_building_cost(
                building_ticker="FP",
                planet="FakePlanet",
            )

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "not found" in result[0].text.lower()
        assert "FakePlanet" in result[0].text

    async def test_api_error(self, tmp_path: Path) -> None:
        """Test API error is handled gracefully."""

        async def mock_ensure_cache() -> BuildingsCache:
            raise FIOApiError("Server error", status_code=500)

        with patch(
            "prun_mcp.tools.building_cost.ensure_buildings_cache",
            mock_ensure_cache,
        ):
            result = await calculate_building_cost(
                building_ticker="FP",
                planet="Promitor",
            )

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "FIO API error" in result[0].text

    async def test_missing_prices_reported(self, tmp_path: Path) -> None:
        """Test that missing prices are reported when using exchange."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        mock_client = AsyncMock()
        mock_client.get_planet.return_value = SAMPLE_ROCKY_PLANET

        async def mock_ensure_cache() -> BuildingsCache:
            return buildings_cache

        # Only return some prices - MCG missing
        async def mock_fetch_prices(
            tickers: list[str], exchange: str
        ) -> dict[str, dict[str, float | None]]:
            prices_data: dict[str, dict[str, float | None]] = {
                "BSE": {"ask": 120.0, "bid": 120.0},
                "BBH": {"ask": 450.0, "bid": 450.0},
                "BDE": {"ask": 800.0, "bid": 800.0},
                "MCG": {"ask": None, "bid": None},  # Missing price
            }
            return {t: prices_data.get(t, {"ask": None, "bid": None}) for t in tickers}

        with (
            patch(
                "prun_mcp.tools.building_cost.ensure_buildings_cache",
                mock_ensure_cache,
            ),
            patch(
                "prun_mcp.tools.building_cost.get_fio_client",
                return_value=mock_client,
            ),
            patch(
                "prun_mcp.tools.building_cost.fetch_prices",
                mock_fetch_prices,
            ),
        ):
            result = await calculate_building_cost(
                building_ticker="FP",
                planet="Promitor",
                exchange="CI1",
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)

        assert "missing_prices" in decoded  # type: ignore[operator]
        assert "MCG" in decoded["missing_prices"]  # type: ignore[index]

    async def test_materials_sorted_alphabetically(self, tmp_path: Path) -> None:
        """Test that materials are sorted alphabetically."""
        buildings_cache = create_buildings_cache(tmp_path / "buildings")
        mock_client = AsyncMock()
        mock_client.get_planet.return_value = SAMPLE_ROCKY_PLANET

        async def mock_ensure_cache() -> BuildingsCache:
            return buildings_cache

        with (
            patch(
                "prun_mcp.tools.building_cost.ensure_buildings_cache",
                mock_ensure_cache,
            ),
            patch(
                "prun_mcp.tools.building_cost.get_fio_client",
                return_value=mock_client,
            ),
        ):
            result = await calculate_building_cost(
                building_ticker="FP",
                planet="Promitor",
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)

        materials = decoded["materials"]  # type: ignore[index]
        tickers = [m["material"] for m in materials]  # type: ignore[union-attr]
        assert tickers == sorted(tickers)
