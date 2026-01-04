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
