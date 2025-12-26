"""HTTP client for the FIO REST API."""

import logging
from typing import Any

import httpx

from prun_mcp.fio.exceptions import FIOApiError, FIONotFoundError

logger = logging.getLogger(__name__)

FIO_BASE_URL = "https://rest.fnar.net"


def _log_api_error(response: httpx.Response, context: str) -> None:
    """Log API error with response body for debugging."""
    body = response.text[:500] if response.text else "(empty)"
    logger.error(
        "FIO API error during %s: status=%d body=%s",
        context,
        response.status_code,
        body,
    )


class FIOClient:
    """Async HTTP client for the FIO REST API."""

    def __init__(self, base_url: str = FIO_BASE_URL) -> None:
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(30.0, connect=10.0),
            )
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
                _log_api_error(response, f"get_material({ticker})")
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
                _log_api_error(response, "get_all_materials")
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
                _log_api_error(response, "get_all_buildings")
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
                _log_api_error(response, f"get_planet({planet})")
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
                _log_api_error(response, "get_all_recipes")
                raise FIOApiError(
                    f"FIO API error: {response.status_code}",
                    status_code=response.status_code,
                )

            return response.json()

        except httpx.HTTPError as e:
            logger.exception("HTTP error while fetching all recipes")
            raise FIOApiError(f"HTTP error: {e}") from e

    async def get_exchange_info(self, ticker: str, exchange: str) -> dict[str, Any]:
        """Get exchange data for a single material on a specific exchange.

        Args:
            ticker: Material ticker symbol (e.g., "RAT", "BSE")
            exchange: Exchange code (e.g., "CI1", "NC1")

        Returns:
            Exchange data dictionary with full order book, bid/ask, supply/demand.

        Raises:
            FIONotFoundError: If the ticker/exchange combination is not found
            FIOApiError: If the API returns an error
        """
        client = await self._get_client()
        try:
            response = await client.get(f"/exchange/{ticker}.{exchange}")

            if response.status_code == 204:
                raise FIONotFoundError("Exchange", f"{ticker}.{exchange}")

            if response.status_code != 200:
                _log_api_error(response, f"get_exchange_info({ticker}.{exchange})")
                raise FIOApiError(
                    f"FIO API error: {response.status_code}",
                    status_code=response.status_code,
                )

            return response.json()

        except httpx.HTTPError as e:
            logger.exception("HTTP error while fetching exchange info")
            raise FIOApiError(f"HTTP error: {e}") from e

    async def get_all_exchange_data(self) -> list[dict[str, Any]]:
        """Fetch all exchange summary data.

        Returns:
            List of exchange data dictionaries with bid/ask, supply/demand
            for all materials on all exchanges (summary only, no order book).

        Raises:
            FIOApiError: If the API returns an error.
        """
        client = await self._get_client()
        try:
            response = await client.get("/exchange/all")

            if response.status_code != 200:
                _log_api_error(response, "get_all_exchange_data")
                raise FIOApiError(
                    f"FIO API error: {response.status_code}",
                    status_code=response.status_code,
                )

            return response.json()

        except httpx.HTTPError as e:
            logger.exception("HTTP error while fetching all exchange data")
            raise FIOApiError(f"HTTP error: {e}") from e

    async def get_workforce_needs(self) -> list[dict[str, Any]]:
        """Fetch workforce consumption rates for all workforce types.

        Returns:
            List of workforce needs dictionaries, each containing workforce type
            and list of required materials with consumption amounts per 100 workers/day.

        Raises:
            FIOApiError: If the API returns an error.
        """
        client = await self._get_client()
        try:
            response = await client.get("/global/workforceneeds")

            if response.status_code != 200:
                _log_api_error(response, "get_workforce_needs")
                raise FIOApiError(
                    f"FIO API error: {response.status_code}",
                    status_code=response.status_code,
                )

            return response.json()

        except httpx.HTTPError as e:
            logger.exception("HTTP error while fetching workforce needs")
            raise FIOApiError(f"HTTP error: {e}") from e


# Singleton instance
_fio_client: FIOClient | None = None


def get_fio_client() -> FIOClient:
    """Get or create the shared FIO client singleton."""
    global _fio_client
    if _fio_client is None:
        _fio_client = FIOClient()
    return _fio_client
