"""Unified exception classes for prun_lib.

This module provides common exception classes used across multiple prun_lib modules.
Module-specific exceptions should still be defined in their respective modules.
"""


class BuildingNotFoundError(Exception):
    """Building not found in cache.

    Accepts either a single building ticker or a list of identifiers.
    """

    def __init__(self, identifier: str | list[str]) -> None:
        if isinstance(identifier, list):
            self.identifiers = identifier
            msg = f"Buildings not found: {', '.join(identifier)}"
        else:
            self.identifiers = [identifier]
            msg = f"Building not found: {identifier}"
        super().__init__(msg)

    @property
    def building_ticker(self) -> str:
        """Return the first identifier (for single-building lookups)."""
        return self.identifiers[0]


class PlanetNotFoundError(Exception):
    """Planet not found in API.

    Accepts either a single planet identifier or a list of identifiers.
    """

    def __init__(self, identifier: str | list[str]) -> None:
        if isinstance(identifier, list):
            self.identifiers = identifier
            msg = f"Planets not found: {', '.join(identifier)}"
        else:
            self.identifiers = [identifier]
            msg = f"Planet not found: {identifier}"
        super().__init__(msg)

    @property
    def planet(self) -> str:
        """Return the first identifier (for single-planet lookups)."""
        return self.identifiers[0]


class RecipeNotFoundError(Exception):
    """Recipe not found in cache.

    Accepts either a single recipe name/ticker or a list.
    """

    def __init__(self, identifier: str | list[str]) -> None:
        if isinstance(identifier, list):
            self.identifiers = identifier
            msg = f"No recipes found that produce: {', '.join(identifier)}"
        else:
            self.identifiers = [identifier]
            msg = f"Recipe not found: {identifier}"
        super().__init__(msg)

    @property
    def recipe_name(self) -> str:
        """Return the first identifier (for single-recipe lookups)."""
        return self.identifiers[0]


class MaterialNotFoundError(Exception):
    """Material not found in cache.

    Accepts either a single material ticker or a list of identifiers.
    """

    def __init__(self, identifier: str | list[str]) -> None:
        if isinstance(identifier, list):
            self.identifiers = identifier
            msg = f"Materials not found: {', '.join(identifier)}"
        else:
            self.identifiers = [identifier]
            msg = f"Material not found: {identifier}"
        super().__init__(msg)

    @property
    def material_ticker(self) -> str:
        """Return the first identifier (for single-material lookups)."""
        return self.identifiers[0]
