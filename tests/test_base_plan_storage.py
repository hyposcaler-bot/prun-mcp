"""Tests for base plan storage layer."""

from pathlib import Path
from typing import Any

import pytest

from prun_mcp.storage import (
    BasePlanStorage,
    validate_base_plan,
)
from tests.conftest import SAMPLE_BASE_PLAN, SAMPLE_BASE_PLAN_MINIMAL


class TestBasePlanStorage:
    """Tests for BasePlanStorage class."""

    def test_storage_starts_empty(self, tmp_path: Path) -> None:
        """New storage has no plans."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        assert storage.plan_count() == 0
        assert storage.list_plans() == []

    def test_save_creates_plan(self, tmp_path: Path) -> None:
        """save_plan creates new plan with timestamps."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        plan = dict(SAMPLE_BASE_PLAN)

        saved, warnings = storage.save_plan(plan)

        assert saved["name"] == "Test Plan"
        assert "created_at" in saved
        assert "updated_at" in saved
        assert saved["created_at"] == saved["updated_at"]
        assert storage.plan_count() == 1
        assert warnings == []

    def test_save_minimal_plan(self, tmp_path: Path) -> None:
        """save_plan works with minimal required fields."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        plan = dict(SAMPLE_BASE_PLAN_MINIMAL)

        saved, warnings = storage.save_plan(plan)

        assert saved["name"] == "Minimal Plan"
        assert storage.plan_count() == 1

    def test_save_requires_overwrite_for_existing(self, tmp_path: Path) -> None:
        """save_plan fails without overwrite=True for existing plan."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        plan = dict(SAMPLE_BASE_PLAN)

        storage.save_plan(plan)

        with pytest.raises(ValueError, match="already exists"):
            storage.save_plan(plan)

    def test_save_with_overwrite(self, tmp_path: Path) -> None:
        """save_plan with overwrite=True updates existing plan."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        plan = dict(SAMPLE_BASE_PLAN)

        saved1, _ = storage.save_plan(plan)
        original_created = saved1["created_at"]

        # Modify and save with overwrite
        plan["notes"] = "Updated notes"
        saved2, _ = storage.save_plan(plan, overwrite=True)

        assert saved2["notes"] == "Updated notes"
        assert saved2["created_at"] == original_created  # Preserved
        assert saved2["updated_at"] != original_created  # Updated
        assert storage.plan_count() == 1

    def test_get_plan_returns_data(self, tmp_path: Path) -> None:
        """get_plan returns saved plan data."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        plan = dict(SAMPLE_BASE_PLAN)
        storage.save_plan(plan)

        retrieved = storage.get_plan("Test Plan")

        assert retrieved is not None
        assert retrieved["name"] == "Test Plan"
        assert retrieved["planet"] == "KW-020c"

    def test_get_plan_not_found(self, tmp_path: Path) -> None:
        """get_plan returns None for unknown plan."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        result = storage.get_plan("Nonexistent Plan")

        assert result is None

    def test_list_plans_returns_summaries(self, tmp_path: Path) -> None:
        """list_plans returns summary fields only."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        storage.save_plan(dict(SAMPLE_BASE_PLAN))
        storage.save_plan(dict(SAMPLE_BASE_PLAN_MINIMAL))

        plans = storage.list_plans()

        assert len(plans) == 2
        # Check summary fields are present
        for plan in plans:
            assert "name" in plan
            assert "planet" in plan
            assert "updated_at" in plan
            # Full plan data should not be in summary
            assert "production" not in plan
            assert "habitation" not in plan

    def test_list_plans_sorted_by_updated_at(self, tmp_path: Path) -> None:
        """list_plans returns plans sorted by updated_at descending."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        storage.save_plan(dict(SAMPLE_BASE_PLAN_MINIMAL))
        storage.save_plan(dict(SAMPLE_BASE_PLAN))

        plans = storage.list_plans()

        # Most recently saved should be first
        assert plans[0]["name"] == "Test Plan"
        assert plans[1]["name"] == "Minimal Plan"

    def test_delete_plan(self, tmp_path: Path) -> None:
        """delete_plan removes plan from storage."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        storage.save_plan(dict(SAMPLE_BASE_PLAN))

        result = storage.delete_plan("Test Plan")

        assert result is True
        assert storage.plan_count() == 0
        assert storage.get_plan("Test Plan") is None

    def test_delete_plan_not_found(self, tmp_path: Path) -> None:
        """delete_plan returns False for unknown plan."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        result = storage.delete_plan("Nonexistent Plan")

        assert result is False

    def test_storage_persists_to_file(self, tmp_path: Path) -> None:
        """Plans persist across storage instances."""
        storage1 = BasePlanStorage(storage_dir=tmp_path)
        storage1.save_plan(dict(SAMPLE_BASE_PLAN))

        # Create new storage instance pointing to same directory
        storage2 = BasePlanStorage(storage_dir=tmp_path)

        assert storage2.plan_count() == 1
        plan = storage2.get_plan("Test Plan")
        assert plan is not None
        assert plan["name"] == "Test Plan"

    def test_creates_directory(self, tmp_path: Path) -> None:
        """Storage creates directory if missing."""
        subdir = tmp_path / "nested" / "storage"
        storage = BasePlanStorage(storage_dir=subdir)

        storage.save_plan(dict(SAMPLE_BASE_PLAN))

        assert subdir.exists()
        assert (subdir / "base_plans.json").exists()

    def test_file_format_is_readable(self, tmp_path: Path) -> None:
        """Storage file uses human-readable JSON format."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        storage.save_plan(dict(SAMPLE_BASE_PLAN))

        content = (tmp_path / "base_plans.json").read_text()

        # Should have indentation (not compact)
        assert "\n" in content
        assert "  " in content  # 2-space indent


class TestActiveField:
    """Tests for the active field in base plans."""

    def test_save_plan_with_active_true(self, tmp_path: Path) -> None:
        """Saving with active=True preserves the field."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        plan = dict(SAMPLE_BASE_PLAN)
        plan["active"] = True

        saved, _ = storage.save_plan(plan)

        assert saved["active"] is True
        retrieved = storage.get_plan("Test Plan")
        assert retrieved is not None
        assert retrieved["active"] is True

    def test_save_plan_with_active_false(self, tmp_path: Path) -> None:
        """Saving with active=False preserves the field."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        plan = dict(SAMPLE_BASE_PLAN)
        plan["active"] = False

        saved, _ = storage.save_plan(plan)

        assert saved["active"] is False
        retrieved = storage.get_plan("Test Plan")
        assert retrieved is not None
        assert retrieved["active"] is False

    def test_list_plans_includes_active_in_summary(self, tmp_path: Path) -> None:
        """list_plans includes active field in summaries."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        plan = dict(SAMPLE_BASE_PLAN)
        plan["active"] = True
        storage.save_plan(plan)

        plans = storage.list_plans()

        assert len(plans) == 1
        assert "active" in plans[0]
        assert plans[0]["active"] is True

    def test_list_plans_filter_active_only(self, tmp_path: Path) -> None:
        """Filter returns only active plans."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        # Save an active plan
        active_plan = dict(SAMPLE_BASE_PLAN)
        active_plan["active"] = True
        storage.save_plan(active_plan)

        # Save an inactive plan
        inactive_plan = dict(SAMPLE_BASE_PLAN_MINIMAL)
        inactive_plan["active"] = False
        storage.save_plan(inactive_plan)

        plans = storage.list_plans(active=True)

        assert len(plans) == 1
        assert plans[0]["name"] == "Test Plan"
        assert plans[0]["active"] is True

    def test_list_plans_filter_inactive_only(self, tmp_path: Path) -> None:
        """Filter returns only inactive plans."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        # Save an active plan
        active_plan = dict(SAMPLE_BASE_PLAN)
        active_plan["active"] = True
        storage.save_plan(active_plan)

        # Save an inactive plan
        inactive_plan = dict(SAMPLE_BASE_PLAN_MINIMAL)
        inactive_plan["active"] = False
        storage.save_plan(inactive_plan)

        plans = storage.list_plans(active=False)

        assert len(plans) == 1
        assert plans[0]["name"] == "Minimal Plan"
        assert plans[0]["active"] is False

    def test_list_plans_no_filter_returns_all(self, tmp_path: Path) -> None:
        """No filter returns all plans."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        # Save an active plan
        active_plan = dict(SAMPLE_BASE_PLAN)
        active_plan["active"] = True
        storage.save_plan(active_plan)

        # Save an inactive plan
        inactive_plan = dict(SAMPLE_BASE_PLAN_MINIMAL)
        inactive_plan["active"] = False
        storage.save_plan(inactive_plan)

        plans = storage.list_plans()

        assert len(plans) == 2
        names = {p["name"] for p in plans}
        assert names == {"Test Plan", "Minimal Plan"}

    def test_list_plans_missing_active_treated_as_false(self, tmp_path: Path) -> None:
        """Plans without active field are treated as inactive."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        # Save a plan without active field (legacy plan)
        plan = dict(SAMPLE_BASE_PLAN)
        # Don't set active field
        storage.save_plan(plan)

        # Filter for active plans should return nothing
        active_plans = storage.list_plans(active=True)
        assert len(active_plans) == 0

        # Filter for inactive plans should return the plan
        inactive_plans = storage.list_plans(active=False)
        assert len(inactive_plans) == 1
        assert inactive_plans[0]["active"] is False


class TestValidation:
    """Tests for validate_base_plan function."""

    def test_valid_plan_no_errors(self) -> None:
        """Valid plan produces no errors."""
        errors, warnings = validate_base_plan(SAMPLE_BASE_PLAN)
        assert errors == []

    def test_valid_minimal_plan_no_errors(self) -> None:
        """Minimal valid plan produces no errors."""
        errors, warnings = validate_base_plan(SAMPLE_BASE_PLAN_MINIMAL)
        assert errors == []

    def test_missing_name_error(self) -> None:
        """Missing name produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        del plan["name"]

        errors, warnings = validate_base_plan(plan)

        assert any("name" in e for e in errors)

    def test_empty_name_error(self) -> None:
        """Empty name produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["name"] = ""

        errors, warnings = validate_base_plan(plan)

        assert any("name" in e for e in errors)

    def test_missing_planet_error(self) -> None:
        """Missing planet produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        del plan["planet"]

        errors, warnings = validate_base_plan(plan)

        assert any("planet" in e for e in errors)

    def test_missing_habitation_error(self) -> None:
        """Missing habitation produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        del plan["habitation"]

        errors, warnings = validate_base_plan(plan)

        assert any("habitation" in e for e in errors)

    def test_missing_production_error(self) -> None:
        """Missing production produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        del plan["production"]

        errors, warnings = validate_base_plan(plan)

        assert any("production" in e for e in errors)

    def test_invalid_production_count_error(self) -> None:
        """Production count < 1 produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["production"] = [{"recipe": "1xA=>1xB", "count": 0, "efficiency": 1.0}]

        errors, warnings = validate_base_plan(plan)

        assert any("count" in e and "positive" in e for e in errors)

    def test_invalid_efficiency_error(self) -> None:
        """Efficiency <= 0 produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["production"] = [{"recipe": "1xA=>1xB", "count": 1, "efficiency": 0}]

        errors, warnings = validate_base_plan(plan)

        assert any("efficiency" in e for e in errors)

    def test_unknown_habitation_warning(self) -> None:
        """Unknown habitation building produces warning."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["habitation"] = [{"building": "HB99", "count": 1}]

        errors, warnings = validate_base_plan(plan)

        assert errors == []  # No errors
        assert any("HB99" in w for w in warnings)

    def test_unknown_expertise_warning(self) -> None:
        """Unknown expertise key produces warning."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["expertise"] = {"UnknownExpertise": 3}

        errors, warnings = validate_base_plan(plan)

        assert errors == []  # No errors
        assert any("UnknownExpertise" in w for w in warnings)

    def test_expertise_over_max_warning(self) -> None:
        """Expertise value > 5 produces warning."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["expertise"] = {"FoodIndustries": 10}

        errors, warnings = validate_base_plan(plan)

        assert errors == []  # No errors
        assert any("10" in w and "maximum" in w for w in warnings)

    def test_invalid_recipe_format_warning(self) -> None:
        """Invalid recipe format produces warning."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["production"] = [{"recipe": "INVALID", "count": 1, "efficiency": 1.0}]

        errors, warnings = validate_base_plan(plan)

        assert errors == []  # No errors
        assert any("INVALID" in w for w in warnings)

    def test_unknown_storage_building_warning(self) -> None:
        """Unknown storage building produces warning."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["storage"] = [{"building": "UNKNOWN", "count": 1, "capacity": 100}]

        errors, warnings = validate_base_plan(plan)

        assert errors == []  # No errors
        assert any("UNKNOWN" in w for w in warnings)


class TestValidationEdgeCases:
    """Edge case tests for validation."""

    def test_negative_habitation_count_error(self) -> None:
        """Negative habitation count produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["habitation"] = [{"building": "HB1", "count": -1}]

        errors, warnings = validate_base_plan(plan)

        assert any("count" in e for e in errors)

    def test_missing_production_recipe_error(self) -> None:
        """Missing recipe in production produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["production"] = [{"count": 1, "efficiency": 1.0}]

        errors, warnings = validate_base_plan(plan)

        assert any("recipe" in e for e in errors)

    def test_missing_production_efficiency_error(self) -> None:
        """Missing efficiency in production produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["production"] = [{"recipe": "1xA=>1xB", "count": 1}]

        errors, warnings = validate_base_plan(plan)

        assert any("efficiency" in e for e in errors)

    def test_negative_expertise_error(self) -> None:
        """Negative expertise value produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["expertise"] = {"FoodIndustries": -1}

        errors, warnings = validate_base_plan(plan)

        assert any("expertise" in e and "non-negative" in e for e in errors)

    def test_storage_negative_capacity_error(self) -> None:
        """Negative storage capacity produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["storage"] = [{"building": "STO", "count": 1, "capacity": -100}]

        errors, warnings = validate_base_plan(plan)

        assert any("capacity" in e for e in errors)


class TestExtractionValidation:
    """Tests for extraction validation."""

    def test_valid_extraction_no_errors(self) -> None:
        """Valid extraction produces no errors."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["extraction"] = [
            {"building": "EXT", "resource": "FEO", "count": 3, "efficiency": 1.4}
        ]

        errors, warnings = validate_base_plan(plan)

        assert errors == []

    def test_extraction_missing_building_error(self) -> None:
        """Missing extraction building produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["extraction"] = [{"resource": "FEO", "count": 3}]

        errors, warnings = validate_base_plan(plan)

        assert any("building" in e for e in errors)

    def test_extraction_unknown_building_warning(self) -> None:
        """Unknown extraction building produces warning."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["extraction"] = [
            {"building": "UNKNOWN", "resource": "FEO", "count": 3, "efficiency": 1.0}
        ]

        errors, warnings = validate_base_plan(plan)

        assert errors == []
        assert any("UNKNOWN" in w for w in warnings)

    def test_extraction_missing_resource_error(self) -> None:
        """Missing extraction resource produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["extraction"] = [{"building": "EXT", "count": 3}]

        errors, warnings = validate_base_plan(plan)

        assert any("resource" in e for e in errors)

    def test_extraction_missing_count_error(self) -> None:
        """Missing extraction count produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["extraction"] = [{"building": "EXT", "resource": "FEO"}]

        errors, warnings = validate_base_plan(plan)

        assert any("count" in e for e in errors)

    def test_extraction_invalid_count_error(self) -> None:
        """Invalid extraction count produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["extraction"] = [
            {"building": "EXT", "resource": "FEO", "count": 0, "efficiency": 1.0}
        ]

        errors, warnings = validate_base_plan(plan)

        assert any("count" in e and "positive" in e for e in errors)

    def test_extraction_invalid_efficiency_error(self) -> None:
        """Invalid extraction efficiency produces error."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["extraction"] = [
            {"building": "EXT", "resource": "FEO", "count": 1, "efficiency": -1.0}
        ]

        errors, warnings = validate_base_plan(plan)

        assert any("efficiency" in e for e in errors)

    def test_extraction_efficiency_optional(self) -> None:
        """Extraction efficiency is optional (defaults to 1.0)."""
        plan: dict[str, Any] = dict(SAMPLE_BASE_PLAN)
        plan["extraction"] = [{"building": "EXT", "resource": "FEO", "count": 1}]

        errors, warnings = validate_base_plan(plan)

        assert errors == []
