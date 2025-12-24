"""Tests for planet tools."""

from unittest.mock import AsyncMock, patch

import pytest
from mcp.types import TextContent
from toon_format import decode as toon_decode

from prun_mcp.fio import FIOApiError, FIONotFoundError
from prun_mcp.tools.planets import get_planet_info

from tests.conftest import SAMPLE_PLANET_KATOA, SAMPLE_PLANET_MONTEM


pytestmark = pytest.mark.anyio


class TestGetPlanetInfo:
    """Tests for get_planet_info tool."""

    async def test_returns_toon_encoded_data(self) -> None:
        """Test successful planet lookup returns TOON-encoded data."""
        mock_client = AsyncMock()
        mock_client.get_planet.return_value = SAMPLE_PLANET_KATOA

        with patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client):
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

        with patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client):
            result = await get_planet_info("XK-745b")

        assert isinstance(result, str)
        mock_client.get_planet.assert_called_once_with("XK-745b")

    async def test_multiple_planets(self) -> None:
        """Test comma-separated planets returns multiple results."""
        mock_client = AsyncMock()
        mock_client.get_planet.side_effect = [SAMPLE_PLANET_KATOA, SAMPLE_PLANET_MONTEM]

        with patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client):
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

        with patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client):
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

        with patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client):
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

        with patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client):
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

        with patch("prun_mcp.tools.planets.get_fio_client", return_value=mock_client):
            result = await get_planet_info("Katoa")

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert "FIO API error" in result[0].text
