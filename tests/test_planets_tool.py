"""Tests for planet tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import TextContent
from toon_format import decode as toon_decode

from prun_mcp.fio import FIOApiError, FIONotFoundError
from prun_mcp.tools.planets import get_planet_info, search_planets

from tests.conftest import (
    SAMPLE_MATERIALS_EXTENDED,
    SAMPLE_PLANET_KATOA,
    SAMPLE_PLANET_MONTEM,
    SAMPLE_SEARCH_PLANETS,
)


pytestmark = pytest.mark.anyio


class TestGetPlanetInfo:
    """Tests for get_planet_info tool."""

    async def test_returns_toon_encoded_data(self) -> None:
        """Test successful planet lookup returns TOON-encoded data."""
        mock_client = AsyncMock()
        mock_client.get_planet.return_value = SAMPLE_PLANET_KATOA

        mock_cache = MagicMock()
        mock_cache.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        with (
            patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client),
            patch(
                "prun_mcp.tools.planets.ensure_materials_cache",
                AsyncMock(return_value=mock_cache),
            ),
        ):
            result = await get_planet_info("Katoa")

        assert isinstance(result, str)

        decoded = toon_decode(result)
        assert isinstance(decoded, dict)
        assert "planets" in decoded  # type: ignore[operator]

        planets = decoded["planets"]  # type: ignore[index]
        assert len(planets) == 1

        planet = planets[0]
        assert planet["PlanetName"] == "Katoa"
        assert planet["PlanetNaturalId"] == "XK-745b"

    async def test_lookup_by_natural_id(self) -> None:
        """Test planet lookup by natural ID."""
        mock_client = AsyncMock()
        mock_client.get_planet.return_value = SAMPLE_PLANET_KATOA

        mock_cache = MagicMock()
        mock_cache.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        with (
            patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client),
            patch(
                "prun_mcp.tools.planets.ensure_materials_cache",
                AsyncMock(return_value=mock_cache),
            ),
        ):
            result = await get_planet_info("XK-745b")

        assert isinstance(result, str)
        mock_client.get_planet.assert_called_once_with("XK-745b")

    async def test_multiple_planets(self) -> None:
        """Test comma-separated planets returns multiple results."""
        mock_client = AsyncMock()
        mock_client.get_planet.side_effect = [SAMPLE_PLANET_KATOA, SAMPLE_PLANET_MONTEM]

        mock_cache = MagicMock()
        mock_cache.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        with (
            patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client),
            patch(
                "prun_mcp.tools.planets.ensure_materials_cache",
                AsyncMock(return_value=mock_cache),
            ),
        ):
            result = await get_planet_info("Katoa,Montem")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        planets = decoded["planets"]  # type: ignore[index]
        assert len(planets) == 2

        names = [p["PlanetName"] for p in planets]  # type: ignore[index]
        assert "Katoa" in names
        assert "Montem" in names

    async def test_multiple_planets_with_spaces(self) -> None:
        """Test comma-separated planets with spaces are handled."""
        mock_client = AsyncMock()
        mock_client.get_planet.side_effect = [SAMPLE_PLANET_KATOA, SAMPLE_PLANET_MONTEM]

        mock_cache = MagicMock()
        mock_cache.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        with (
            patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client),
            patch(
                "prun_mcp.tools.planets.ensure_materials_cache",
                AsyncMock(return_value=mock_cache),
            ),
        ):
            result = await get_planet_info("Katoa, Montem")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        planets = decoded["planets"]  # type: ignore[index]
        assert len(planets) == 2

    async def test_partial_match_includes_not_found(self) -> None:
        """Test partial matches return found planets plus not_found list."""
        mock_client = AsyncMock()
        mock_client.get_planet.side_effect = [
            SAMPLE_PLANET_KATOA,
            FIONotFoundError("Planet", "INVALID"),
            SAMPLE_PLANET_MONTEM,
        ]

        mock_cache = MagicMock()
        mock_cache.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        with (
            patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client),
            patch(
                "prun_mcp.tools.planets.ensure_materials_cache",
                AsyncMock(return_value=mock_cache),
            ),
        ):
            result = await get_planet_info("Katoa,INVALID,Montem")

        assert isinstance(result, str)
        decoded = toon_decode(result)

        # Should have found planets
        planets = decoded["planets"]  # type: ignore[index]
        assert len(planets) == 2
        names = [p["PlanetName"] for p in planets]  # type: ignore[index]
        assert "Katoa" in names
        assert "Montem" in names

        # Should have not_found list
        not_found = decoded["not_found"]  # type: ignore[index]
        assert "INVALID" in not_found

    async def test_all_not_found(self) -> None:
        """Test all planets not found returns error content."""
        mock_client = AsyncMock()
        mock_client.get_planet.side_effect = [
            FIONotFoundError("Planet", "INVALID1"),
            FIONotFoundError("Planet", "INVALID2"),
        ]

        mock_cache = MagicMock()
        mock_cache.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        with (
            patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client),
            patch(
                "prun_mcp.tools.planets.ensure_materials_cache",
                AsyncMock(return_value=mock_cache),
            ),
        ):
            result = await get_planet_info("INVALID1,INVALID2")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "not found" in result[0].text.lower()
        assert "INVALID1" in result[0].text
        assert "INVALID2" in result[0].text

    async def test_api_error_returns_error_content(self) -> None:
        """Test FIO API error returns error content."""
        mock_client = AsyncMock()
        mock_client.get_planet.side_effect = FIOApiError(
            "Server error", status_code=500
        )

        mock_cache = MagicMock()
        mock_cache.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        with (
            patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client),
            patch(
                "prun_mcp.tools.planets.ensure_materials_cache",
                AsyncMock(return_value=mock_cache),
            ),
        ):
            result = await get_planet_info("Katoa")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "FIO API error" in result[0].text


class TestSearchPlanets:
    """Tests for search_planets tool."""

    async def test_returns_toon_encoded_results(self) -> None:
        """Test successful search returns TOON-encoded planet list."""
        mock_client = AsyncMock()
        mock_client.search_planets.return_value = SAMPLE_SEARCH_PLANETS
        mock_client.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = False
        mock_cache.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        with (
            patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client),
            patch(
                "prun_mcp.tools.planets.ensure_materials_cache",
                AsyncMock(return_value=mock_cache),
            ),
        ):
            result = await search_planets(include_resources="FEO")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert isinstance(decoded, list)
        assert len(decoded) == 3  # All planets from mock (API filtering is mocked)

    async def test_include_resources_filters_by_material(self) -> None:
        """Test include_resources parameter filters planets."""
        mock_client = AsyncMock()
        mock_client.search_planets.return_value = SAMPLE_SEARCH_PLANETS
        mock_client.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = False
        mock_cache.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        with (
            patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client),
            patch(
                "prun_mcp.tools.planets.ensure_materials_cache",
                AsyncMock(return_value=mock_cache),
            ),
        ):
            result = await search_planets(include_resources="FEO,LST")

        # API should be called with materials list
        mock_client.search_planets.assert_called_once_with(materials=["FEO", "LST"])
        assert isinstance(result, str)

    async def test_exclude_resources_filters_client_side(self) -> None:
        """Test exclude_resources filters planets client-side."""
        mock_client = AsyncMock()
        mock_client.search_planets.return_value = SAMPLE_SEARCH_PLANETS
        mock_client.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = False
        mock_cache.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        with (
            patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client),
            patch(
                "prun_mcp.tools.planets.ensure_materials_cache",
                AsyncMock(return_value=mock_cache),
            ),
        ):
            # Exclude H2O - should filter out Promitor and Berthier
            result = await search_planets(exclude_resources="H2O")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert isinstance(decoded, list)
        # Only Vallis should remain (has FEO, SI, O but no H2O)
        assert len(decoded) == 1
        assert decoded[0]["name"] == "Vallis"

    async def test_limit_parameter(self) -> None:
        """Test limit parameter restricts result count."""
        mock_client = AsyncMock()
        mock_client.search_planets.return_value = SAMPLE_SEARCH_PLANETS
        mock_client.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = False
        mock_cache.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        with (
            patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client),
            patch(
                "prun_mcp.tools.planets.ensure_materials_cache",
                AsyncMock(return_value=mock_cache),
            ),
        ):
            result = await search_planets(limit=1)

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert isinstance(decoded, list)
        assert len(decoded) == 1

    async def test_top_resources_parameter(self) -> None:
        """Test top_resources limits resources shown per planet."""
        mock_client = AsyncMock()
        mock_client.search_planets.return_value = SAMPLE_SEARCH_PLANETS
        mock_client.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = False
        mock_cache.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        with (
            patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client),
            patch(
                "prun_mcp.tools.planets.ensure_materials_cache",
                AsyncMock(return_value=mock_cache),
            ),
        ):
            result = await search_planets(top_resources=2, limit=1)

        assert isinstance(result, str)
        decoded = toon_decode(result)
        planet = decoded[0]  # type: ignore[index]
        # Resources string should have at most 2 entries
        resources = planet["resources"].split(",")  # type: ignore[index]
        assert len(resources) <= 2

    async def test_resources_sorted_by_factor_descending(self) -> None:
        """Test resources are sorted by factor in descending order."""
        mock_client = AsyncMock()
        mock_client.search_planets.return_value = SAMPLE_SEARCH_PLANETS
        mock_client.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = False
        mock_cache.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        with (
            patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client),
            patch(
                "prun_mcp.tools.planets.ensure_materials_cache",
                AsyncMock(return_value=mock_cache),
            ),
        ):
            result = await search_planets(limit=1)

        assert isinstance(result, str)
        decoded = toon_decode(result)
        # Promitor has FEO:0.35, LST:0.28, H2O:0.12 - should be in that order
        resources_str = decoded[0]["resources"]  # type: ignore[index]
        # Parse the resources string
        parts = resources_str.split(",")
        factors = [float(p.split(":")[1]) for p in parts]
        # Verify descending order
        assert factors == sorted(factors, reverse=True)

    async def test_invalid_limit_returns_error(self) -> None:
        """Test limit < 1 returns error."""
        result = await search_planets(limit=0)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "limit must be at least 1" in result[0].text

    async def test_invalid_top_resources_returns_error(self) -> None:
        """Test top_resources < 1 returns error."""
        result = await search_planets(top_resources=0)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "top_resources must be at least 1" in result[0].text

    async def test_max_four_include_resources(self) -> None:
        """Test more than 4 include_resources returns error."""
        result = await search_planets(include_resources="FEO,LST,H2O,SI,O")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "Maximum 4 materials" in result[0].text

    async def test_api_error_returns_error_content(self) -> None:
        """Test FIO API error returns error content."""
        mock_client = AsyncMock()
        mock_client.search_planets.side_effect = FIOApiError(
            "Server error", status_code=500
        )

        with patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client):
            result = await search_planets()

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "FIO API error" in result[0].text

    async def test_output_format(self) -> None:
        """Test output contains expected fields."""
        mock_client = AsyncMock()
        mock_client.search_planets.return_value = SAMPLE_SEARCH_PLANETS
        mock_client.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        mock_cache = MagicMock()
        mock_cache.is_valid.return_value = False
        mock_cache.get_all_materials.return_value = SAMPLE_MATERIALS_EXTENDED

        with (
            patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client),
            patch(
                "prun_mcp.tools.planets.ensure_materials_cache",
                AsyncMock(return_value=mock_cache),
            ),
        ):
            result = await search_planets(limit=1)

        assert isinstance(result, str)
        decoded = toon_decode(result)
        planet = decoded[0]  # type: ignore[index]

        # Check expected fields
        assert "name" in planet  # type: ignore[operator]
        assert "id" in planet  # type: ignore[operator]
        assert "gravity" in planet  # type: ignore[operator]
        assert "temperature" in planet  # type: ignore[operator]
        assert "fertility" in planet  # type: ignore[operator]
        assert "resources" in planet  # type: ignore[operator]

        # Check field types/values
        assert planet["name"] == "Promitor"  # type: ignore[index]
        assert planet["id"] == "AB-123a"  # type: ignore[index]
        assert planet["gravity"] == 0.92  # type: ignore[index]
        assert planet["temperature"] == 22.5  # type: ignore[index]
        assert planet["fertility"] == 0.95  # type: ignore[index]
