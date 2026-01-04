"""Persistent storage for base plan configurations."""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from prun_mcp.storage.validation import validate_base_plan

logger = logging.getLogger(__name__)

DEFAULT_CACHE_DIR = Path(os.environ.get("PRUN_MCP_CACHE_DIR", "cache"))


class BasePlanStorage:
    """Persistent storage for base plans as JSON.

    Stores plans in a single JSON file with atomic writes for data integrity.
    Unlike cache classes, storage has no TTL as this is user-generated data.
    """

    def __init__(self, storage_dir: Path | None = None) -> None:
        """Initialize base plan storage.

        Args:
            storage_dir: Directory for storage files. Defaults to PRUN_MCP_CACHE_DIR
                        env var or 'cache' in current directory.
        """
        self.storage_dir = storage_dir or DEFAULT_CACHE_DIR
        self.storage_file = self.storage_dir / "base_plans.json"
        self._plans: dict[str, dict[str, Any]] | None = None

    def _load(self) -> None:
        """Load plans from JSON file into memory."""
        if not self.storage_file.exists():
            self._plans = {}
            return

        try:
            with open(self.storage_file, encoding="utf-8") as f:
                data = json.load(f)
                self._plans = data.get("plans", {})
            assert self._plans is not None
            logger.info("Loaded %d base plans from storage", len(self._plans))
        except json.JSONDecodeError:
            logger.exception("Failed to parse base plans file")
            raise

    def _save(self) -> None:
        """Save plans to JSON file atomically.

        Uses temp file + rename for atomic write on POSIX systems.
        """
        if self._plans is None:
            self._plans = {}

        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Write to temp file first
        temp_path = self.storage_file.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump({"plans": self._plans}, f, indent=2)

        # Atomic rename
        temp_path.rename(self.storage_file)
        logger.info("Saved %d base plans to storage", len(self._plans))

    def _ensure_loaded(self) -> None:
        """Ensure plans are loaded into memory."""
        if self._plans is None:
            self._load()

    def get_plan(self, name: str) -> dict[str, Any] | None:
        """Get a single plan by name.

        Args:
            name: Plan identifier.

        Returns:
            Plan data dictionary or None if not found.
        """
        self._ensure_loaded()
        assert self._plans is not None
        return self._plans.get(name)

    def list_plans(self, active: bool | None = None) -> list[dict[str, Any]]:
        """List all plans with summary information.

        Args:
            active: Filter by active status. If None, returns all plans.
                   If True, returns only active plans.
                   If False, returns only inactive plans.

        Returns:
            List of plan summaries containing:
            - name
            - planet
            - planet_name (if set)
            - active
            - updated_at
        """
        self._ensure_loaded()
        assert self._plans is not None

        summaries = []
        for name, plan in self._plans.items():
            plan_active = plan.get("active", False)
            # Filter by active status if specified
            if active is not None and plan_active != active:
                continue

            summary: dict[str, Any] = {
                "name": name,
                "planet": plan.get("planet", ""),
                "active": plan_active,
                "updated_at": plan.get("updated_at", ""),
            }
            if plan.get("planet_name"):
                summary["planet_name"] = plan["planet_name"]
            summaries.append(summary)

        # Sort by updated_at descending (most recent first)
        summaries.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return summaries

    def save_plan(
        self, plan: dict[str, Any], overwrite: bool = False
    ) -> tuple[dict[str, Any], list[str]]:
        """Save a plan to storage.

        Args:
            plan: Plan data dictionary. Must include 'name' field.
            overwrite: If True, allows updating existing plan. If False,
                      raises ValueError if plan with same name exists.

        Returns:
            Tuple of (saved_plan, warnings) where:
            - saved_plan: The saved plan data with timestamps
            - warnings: List of validation warnings

        Raises:
            ValueError: If validation errors occur or plan exists without overwrite.
        """
        self._ensure_loaded()
        assert self._plans is not None

        # Validate the plan
        errors, warnings = validate_base_plan(plan)
        if errors:
            raise ValueError(f"Validation errors: {'; '.join(errors)}")

        name = plan["name"]

        # Check for existing plan
        if name in self._plans and not overwrite:
            raise ValueError(
                f"Plan '{name}' already exists. Set overwrite=True to update."
            )

        # Set timestamps
        now = datetime.now(timezone.utc).isoformat()
        plan_to_save = dict(plan)

        if name in self._plans:
            # Preserve created_at on update
            plan_to_save["created_at"] = self._plans[name].get("created_at", now)
            plan_to_save["updated_at"] = now
        else:
            # New plan
            plan_to_save["created_at"] = now
            plan_to_save["updated_at"] = now

        # Save to memory and disk
        self._plans[name] = plan_to_save
        self._save()

        return plan_to_save, warnings

    def delete_plan(self, name: str) -> bool:
        """Delete a plan from storage.

        Args:
            name: Plan identifier.

        Returns:
            True if plan was deleted, False if not found.
        """
        self._ensure_loaded()
        assert self._plans is not None

        if name not in self._plans:
            return False

        del self._plans[name]
        self._save()
        logger.info("Deleted base plan: %s", name)
        return True

    def plan_count(self) -> int:
        """Get the number of stored plans.

        Returns:
            Number of plans in storage.
        """
        self._ensure_loaded()
        assert self._plans is not None
        return len(self._plans)
