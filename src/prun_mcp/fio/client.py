"""HTTP client for the FIO REST API."""

import logging
from typing import Any

import httpx

from prun_mcp.fio.exceptions import FIOApiError, FIONotFoundError

logger = logging.getLogger(__name__)

FIO_BASE_URL = "https://rest.fnar.net"


class FIOClient:
    """Async HTTP client for the FIO REST API."""

    def __init__(self, base_url: str = FIO_BASE_URL) -> None:
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def get_material(self, ticker: str) -> dict[str, Any]:
        """Get material information by ticker.

        Args:
            ticker: Material ticker symbol (e.g., "BSE", "RAT")

        Returns:
            Material data dictionary

        Raises:
            FIONotFoundError: If the material ticker is not found
            FIOApiError: If the API returns an error
        """
        client = await self._get_client()
        try:
            response = await client.get(f"/material/{ticker}")

            if response.status_code == 204:
                raise FIONotFoundError("Material", ticker)

            if response.status_code != 200:
                raise FIOApiError(
                    f"FIO API error: {response.status_code}",
                    status_code=response.status_code,
                )

            return response.json()

        except httpx.HTTPError as e:
            logger.exception("HTTP error while fetching material")
            raise FIOApiError(f"HTTP error: {e}") from e

    async def get_all_materials(self) -> list[dict[str, Any]]:
        """Fetch all materials as JSON.

        Returns:
            List of material dictionaries with full details.

        Raises:
            FIOApiError: If the API returns an error.
        """
        client = await self._get_client()
        try:
            response = await client.get("/material/allmaterials")

            if response.status_code != 200:
                raise FIOApiError(
                    f"FIO API error: {response.status_code}",
                    status_code=response.status_code,
                )

            return response.json()

        except httpx.HTTPError as e:
            logger.exception("HTTP error while fetching all materials")
            raise FIOApiError(f"HTTP error: {e}") from e

    async def get_all_buildings(self) -> list[dict[str, Any]]:
        """Fetch all buildings as JSON.

        Returns:
            List of building dictionaries with full details including
            BuildingCosts, Recipes, and workforce requirements.

        Raises:
            FIOApiError: If the API returns an error.
        """
        client = await self._get_client()
        try:
            response = await client.get("/building/allbuildings")

            if response.status_code != 200:
                raise FIOApiError(
                    f"FIO API error: {response.status_code}",
                    status_code=response.status_code,
                )

            return response.json()

        except httpx.HTTPError as e:
            logger.exception("HTTP error while fetching all buildings")
            raise FIOApiError(f"HTTP error: {e}") from e

    async def get_planet(self, planet: str) -> dict[str, Any]:
        """Get planet information by ID, NaturalId, or Name.

        Args:
            planet: Planet identifier (e.g., "Katoa", "XK-745b", or PlanetId)

        Returns:
            Planet data dictionary with resources, buildings, workforce, etc.

        Raises:
            FIONotFoundError: If the planet is not found
            FIOApiError: If the API returns an error
        """
        client = await self._get_client()
        try:
            response = await client.get(f"/planet/{planet}")

            if response.status_code == 204:
                raise FIONotFoundError("Planet", planet)

            if response.status_code != 200:
                raise FIOApiError(
                    f"FIO API error: {response.status_code}",
                    status_code=response.status_code,
                )

            return response.json()

        except httpx.HTTPError as e:
            logger.exception("HTTP error while fetching planet")
            raise FIOApiError(f"HTTP error: {e}") from e

    async def get_all_recipes(self) -> list[dict[str, Any]]:
        """Fetch all recipes as JSON.

        Returns:
            List of recipe dictionaries with inputs, outputs, building, and duration.

        Raises:
            FIOApiError: If the API returns an error.
        """
        client = await self._get_client()
        try:
            response = await client.get("/recipes/allrecipes")

            if response.status_code != 200:
                raise FIOApiError(
                    f"FIO API error: {response.status_code}",
                    status_code=response.status_code,
                )

            return response.json()

        except httpx.HTTPError as e:
            logger.exception("HTTP error while fetching all recipes")
            raise FIOApiError(f"HTTP error: {e}") from e
