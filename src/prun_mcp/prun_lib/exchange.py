"""Exchange validation and data."""

# Exchange code to name mapping - canonical source of exchange data
EXCHANGES: dict[str, str] = {
    "AI1": "Antares Station",
    "CI1": "Benten Station",
    "CI2": "Arclight Exchange",
    "IC1": "Hortus Station",
    "NC1": "Moria Station",
    "NC2": "Hubur Exchange",
}

VALID_EXCHANGES = frozenset(EXCHANGES.keys())


class InvalidExchangeError(ValueError):
    """Invalid exchange code provided."""

    def __init__(self, exchange: str) -> None:
        self.exchange = exchange
        self.valid_exchanges = VALID_EXCHANGES
        valid_list = ", ".join(sorted(VALID_EXCHANGES))
        super().__init__(f"Invalid exchange: {exchange}. Valid: {valid_list}")


def validate_exchange(exchange: str | None) -> str | None:
    """Validate and normalize an exchange code.

    Args:
        exchange: Exchange code to validate, or None.

    Returns:
        Normalized (uppercase) exchange code, or None if input was None.

    Raises:
        InvalidExchangeError: If exchange is not a valid code.
    """
    if exchange is None:
        return None

    normalized = exchange.strip().upper()
    if normalized not in VALID_EXCHANGES:
        raise InvalidExchangeError(normalized)

    return normalized


def format_exchange_list() -> str:
    """Format exchange list for display.

    Returns:
        Human-readable table of exchanges.
    """
    lines = ["Code  Name"]
    lines.append("-" * 25)
    for code, name in EXCHANGES.items():
        lines.append(f"{code}   {name}")
    return "\n".join(lines)


def validate_exchanges(exchange: str) -> list[str]:
    """Validate comma-separated exchanges.

    Args:
        exchange: Comma-separated exchange codes.

    Returns:
        List of validated exchange codes.

    Raises:
        InvalidExchangeError: If any exchange code is invalid.
    """
    exchanges = [e.strip().upper() for e in exchange.split(",")]
    invalid = [e for e in exchanges if e not in VALID_EXCHANGES]
    if invalid:
        valid_list = ", ".join(sorted(VALID_EXCHANGES))
        raise InvalidExchangeError(
            f"Invalid exchange(s): {', '.join(invalid)}. Valid: {valid_list}"
        )
    return exchanges


async def get_exchange_prices_async(
    ticker: str, exchange: str
) -> dict[str, list | list[str]]:
    """Get current market prices with full order book for material(s).

    Args:
        ticker: Material ticker symbol(s). Single or comma-separated.
        exchange: Exchange code(s). Single or comma-separated.

    Returns:
        Dict with 'prices' list and optional 'not_found' list.

    Raises:
        InvalidExchangeError: If any exchange code is invalid.
    """
    import asyncio
    from typing import Any

    from prun_mcp.fio import FIONotFoundError, get_fio_client
    from prun_mcp.models.fio import FIOExchangeData

    exchanges = validate_exchanges(exchange)

    client = get_fio_client()
    tickers = [t.strip().upper() for t in ticker.split(",")]

    async def fetch_one(t: str, ex: str) -> tuple[str, str, dict[str, Any] | None]:
        try:
            data = await client.get_exchange_info(t, ex)
            return (t, ex, data)
        except FIONotFoundError:
            return (t, ex, None)

    results = await asyncio.gather(
        *[fetch_one(t, ex) for t in tickers for ex in exchanges]
    )

    prices: list[dict[str, Any]] = []
    not_found: list[str] = []

    for ticker_name, exchange_code, data in results:
        if data is None:
            not_found.append(f"{ticker_name}.{exchange_code}")
        else:
            price = FIOExchangeData.model_validate(data)
            prices.append(price.model_dump(by_alias=True))

    output: dict[str, Any] = {"prices": prices}
    if not_found:
        output["not_found"] = not_found

    return output


async def get_exchange_all_async(exchange: str) -> dict[str, list]:
    """Get summary prices for all materials on a specific exchange.

    Args:
        exchange: Exchange code(s). Single or comma-separated.

    Returns:
        Dict with 'prices' list.

    Raises:
        InvalidExchangeError: If any exchange code is invalid.
    """
    from typing import Any

    from prun_mcp.fio import get_fio_client
    from prun_mcp.models.fio import FIOExchangeData

    exchanges = validate_exchanges(exchange)

    client = get_fio_client()
    all_data = await client.get_all_exchange_data()

    exchange_set = set(exchanges)
    prices: list[dict[str, Any]] = []
    for item in all_data:
        if item.get("ExchangeCode") in exchange_set:
            price = FIOExchangeData.model_validate(item)
            prices.append(price.model_dump(by_alias=True))

    return {"prices": prices}
