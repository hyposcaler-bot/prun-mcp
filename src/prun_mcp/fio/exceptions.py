"""Custom exceptions for FIO API client."""


class FIOApiError(Exception):
    """Base exception for FIO API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class FIONotFoundError(FIOApiError):
    """Raised when a requested resource is not found (HTTP 204)."""

    def __init__(self, resource_type: str, identifier: str) -> None:
        super().__init__(f"{resource_type} '{identifier}' not found", status_code=204)
        self.resource_type = resource_type
        self.identifier = identifier
