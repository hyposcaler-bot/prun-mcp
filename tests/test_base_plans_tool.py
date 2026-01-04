"""Tests for base plan MCP tools."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from mcp.types import TextContent
from toon_format import decode as toon_decode

from prun_mcp.storage import BasePlanStorage
from prun_mcp.tools.base_plans import (
    calculate_plan_io,
    delete_base_plan,
    get_base_plan,
    get_base_plan_storage,
    list_base_plans,
    save_base_plan,
)

from tests.conftest import SAMPLE_BASE_PLAN, SAMPLE_BASE_PLAN_MINIMAL


pytestmark = pytest.mark.anyio


def create_storage_with_plans(tmp_path: Path) -> BasePlanStorage:
    """Create storage populated with sample plans."""
    storage = BasePlanStorage(storage_dir=tmp_path)
    storage.save_plan(dict(SAMPLE_BASE_PLAN))
    storage.save_plan(dict(SAMPLE_BASE_PLAN_MINIMAL))
    return storage


class TestSaveBasePlan:
    """Tests for save_base_plan tool."""

    async def test_save_new_plan(self, tmp_path: Path) -> None:
        """save_base_plan creates new plan."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await save_base_plan(
                name="New Plan",
                planet="XK-001a",
                habitation=[{"building": "HB1", "count": 3}],
                production=[{"recipe": "1xH2O=>4xGRN", "count": 2, "efficiency": 1.0}],
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert "plan" in decoded  # type: ignore[operator]
        plan = decoded["plan"]  # type: ignore[index]
        assert plan["name"] == "New Plan"  # type: ignore[index]
        assert "created_at" in plan  # type: ignore[operator]
        assert "updated_at" in plan  # type: ignore[operator]

    async def test_save_with_all_fields(self, tmp_path: Path) -> None:
        """save_base_plan works with all optional fields."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await save_base_plan(
                name="Full Plan",
                planet="KW-020c",
                planet_name="Milliways",
                cogc_program="FOOD",
                expertise={"FoodIndustries": 3},
                habitation=[{"building": "HB1", "count": 5}],
                storage=[{"building": "STO", "count": 2, "capacity": 1000}],
                production=[
                    {
                        "recipe": "1xGRN 1xALG 1xVEG=>10xRAT",
                        "count": 11,
                        "efficiency": 1.33,
                    }
                ],
                notes="Test notes",
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)
        plan = decoded["plan"]  # type: ignore[index]
        assert plan["planet_name"] == "Milliways"  # type: ignore[index]
        assert plan["cogc_program"] == "FOOD"  # type: ignore[index]
        assert plan["notes"] == "Test notes"  # type: ignore[index]

    async def test_save_existing_without_overwrite(self, tmp_path: Path) -> None:
        """save_base_plan returns error for existing plan without overwrite."""
        storage = create_storage_with_plans(tmp_path)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await save_base_plan(
                name="Test Plan",  # Already exists
                planet="XK-001a",
                habitation=[{"building": "HB1", "count": 1}],
                production=[{"recipe": "1xA=>1xB", "count": 1, "efficiency": 1.0}],
            )

        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "already exists" in result[0].text

    async def test_save_existing_with_overwrite(self, tmp_path: Path) -> None:
        """save_base_plan updates plan with overwrite=True."""
        storage = create_storage_with_plans(tmp_path)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await save_base_plan(
                name="Test Plan",
                planet="NEW-PLANET",
                habitation=[{"building": "HB2", "count": 10}],
                production=[{"recipe": "1xA=>1xB", "count": 5, "efficiency": 1.5}],
                overwrite=True,
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)
        plan = decoded["plan"]  # type: ignore[index]
        assert plan["planet"] == "NEW-PLANET"  # type: ignore[index]

    async def test_save_with_validation_warnings(self, tmp_path: Path) -> None:
        """save_base_plan returns warnings for unknown values."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await save_base_plan(
                name="Warning Plan",
                planet="XK-001a",
                habitation=[{"building": "HB99", "count": 1}],  # Unknown
                production=[{"recipe": "1xA=>1xB", "count": 1, "efficiency": 1.0}],
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert "warnings" in decoded  # type: ignore[operator]
        warnings = decoded["warnings"]  # type: ignore[index]
        assert len(warnings) > 0

    async def test_save_validation_errors(self, tmp_path: Path) -> None:
        """save_base_plan returns error for validation failures."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await save_base_plan(
                name="",  # Invalid: empty name
                planet="XK-001a",
                habitation=[{"building": "HB1", "count": 1}],
                production=[{"recipe": "1xA=>1xB", "count": 1, "efficiency": 1.0}],
            )

        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "error" in result[0].text.lower()

    async def test_save_with_active_true(self, tmp_path: Path) -> None:
        """save_base_plan stores active=True correctly."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await save_base_plan(
                name="Active Plan",
                planet="XK-001a",
                habitation=[{"building": "HB1", "count": 1}],
                production=[{"recipe": "1xA=>1xB", "count": 1, "efficiency": 1.0}],
                active=True,
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)
        plan = decoded["plan"]  # type: ignore[index]
        assert plan["active"] is True  # type: ignore[index]

        # Verify in storage
        retrieved = storage.get_plan("Active Plan")
        assert retrieved is not None
        assert retrieved["active"] is True

    async def test_save_with_active_false(self, tmp_path: Path) -> None:
        """save_base_plan stores active=False correctly (default)."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await save_base_plan(
                name="Inactive Plan",
                planet="XK-001a",
                habitation=[{"building": "HB1", "count": 1}],
                production=[{"recipe": "1xA=>1xB", "count": 1, "efficiency": 1.0}],
                # active defaults to False
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)
        plan = decoded["plan"]  # type: ignore[index]
        assert plan["active"] is False  # type: ignore[index]

        # Verify in storage
        retrieved = storage.get_plan("Inactive Plan")
        assert retrieved is not None
        assert retrieved["active"] is False


class TestGetBasePlan:
    """Tests for get_base_plan tool."""

    async def test_get_existing_plan(self, tmp_path: Path) -> None:
        """get_base_plan returns plan data."""
        storage = create_storage_with_plans(tmp_path)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await get_base_plan("Test Plan")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert decoded["name"] == "Test Plan"  # type: ignore[index]
        assert decoded["planet"] == "KW-020c"  # type: ignore[index]

    async def test_get_nonexistent_plan(self, tmp_path: Path) -> None:
        """get_base_plan returns error for unknown plan."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await get_base_plan("Nonexistent")

        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "not found" in result[0].text.lower()


class TestListBasePlans:
    """Tests for list_base_plans tool."""

    async def test_list_empty(self, tmp_path: Path) -> None:
        """list_base_plans returns empty list when no plans."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await list_base_plans()

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert decoded["plans"] == []  # type: ignore[index]

    async def test_list_multiple(self, tmp_path: Path) -> None:
        """list_base_plans returns all plan summaries."""
        storage = create_storage_with_plans(tmp_path)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await list_base_plans()

        assert isinstance(result, str)
        decoded = toon_decode(result)
        plans = decoded["plans"]  # type: ignore[index]
        assert len(plans) == 2

        # Check summary fields only
        for plan in plans:
            assert "name" in plan
            assert "planet" in plan
            assert "updated_at" in plan
            # Full data should not be in summary
            assert "production" not in plan

    async def test_list_filter_active(self, tmp_path: Path) -> None:
        """list_base_plans filters by active status."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        # Save an active plan
        active_plan = dict(SAMPLE_BASE_PLAN)
        active_plan["active"] = True
        storage.save_plan(active_plan)

        # Save an inactive plan
        inactive_plan = dict(SAMPLE_BASE_PLAN_MINIMAL)
        inactive_plan["active"] = False
        storage.save_plan(inactive_plan)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await list_base_plans(active=True)

        assert isinstance(result, str)
        decoded = toon_decode(result)
        plans = decoded["plans"]  # type: ignore[index]
        assert len(plans) == 1
        assert plans[0]["name"] == "Test Plan"  # type: ignore[index]
        assert plans[0]["active"] is True  # type: ignore[index]

    async def test_list_filter_inactive(self, tmp_path: Path) -> None:
        """list_base_plans filters by inactive status."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        # Save an active plan
        active_plan = dict(SAMPLE_BASE_PLAN)
        active_plan["active"] = True
        storage.save_plan(active_plan)

        # Save an inactive plan
        inactive_plan = dict(SAMPLE_BASE_PLAN_MINIMAL)
        inactive_plan["active"] = False
        storage.save_plan(inactive_plan)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await list_base_plans(active=False)

        assert isinstance(result, str)
        decoded = toon_decode(result)
        plans = decoded["plans"]  # type: ignore[index]
        assert len(plans) == 1
        assert plans[0]["name"] == "Minimal Plan"  # type: ignore[index]
        assert plans[0]["active"] is False  # type: ignore[index]

    async def test_list_includes_active_in_summary(self, tmp_path: Path) -> None:
        """list_base_plans includes active field in summaries."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        plan = dict(SAMPLE_BASE_PLAN)
        plan["active"] = True
        storage.save_plan(plan)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await list_base_plans()

        assert isinstance(result, str)
        decoded = toon_decode(result)
        plans = decoded["plans"]  # type: ignore[index]
        assert len(plans) == 1
        assert "active" in plans[0]  # type: ignore[operator]
        assert plans[0]["active"] is True  # type: ignore[index]


class TestDeleteBasePlan:
    """Tests for delete_base_plan tool."""

    async def test_delete_existing(self, tmp_path: Path) -> None:
        """delete_base_plan removes plan."""
        storage = create_storage_with_plans(tmp_path)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await delete_base_plan("Test Plan")

        assert isinstance(result, str)
        decoded = toon_decode(result)
        assert decoded["deleted"] == "Test Plan"  # type: ignore[index]
        assert decoded["success"] is True  # type: ignore[index]

        # Verify plan is actually deleted
        assert storage.get_plan("Test Plan") is None

    async def test_delete_nonexistent(self, tmp_path: Path) -> None:
        """delete_base_plan returns error for unknown plan."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await delete_base_plan("Nonexistent")

        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "not found" in result[0].text.lower()


class TestCalculatePlanIo:
    """Tests for calculate_plan_io tool."""

    async def test_plan_not_found(self, tmp_path: Path) -> None:
        """calculate_plan_io returns error for unknown plan."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await calculate_plan_io("Nonexistent", "CI1")

        assert isinstance(result, list)
        assert isinstance(result[0], TextContent)
        assert "not found" in result[0].text.lower()

    async def test_calls_calculate_permit_io(self, tmp_path: Path) -> None:
        """calculate_plan_io calls calculate_permit_io with correct args."""
        storage = create_storage_with_plans(tmp_path)

        mock_permit_io = AsyncMock(return_value="mock_result")

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            with patch("prun_mcp.tools.base_plans.calculate_permit_io", mock_permit_io):
                result = await calculate_plan_io("Test Plan", "CI1")

        # Verify calculate_permit_io was called
        mock_permit_io.assert_called_once()

        # Check the arguments
        call_kwargs = mock_permit_io.call_args.kwargs
        assert call_kwargs["exchange"] == "CI1"
        assert call_kwargs["permits"] == 1

        # Check production was extracted correctly
        production = call_kwargs["production"]
        assert len(production) == 1
        assert production[0]["recipe"] == "1xGRN 1xALG 1xVEG=>10xRAT"
        assert production[0]["count"] == 11
        assert production[0]["efficiency"] == 1.33

        # Check habitation was extracted correctly
        habitation = call_kwargs["habitation"]
        assert len(habitation) == 1
        assert habitation[0]["building"] == "HB1"
        assert habitation[0]["count"] == 5

        # Verify result is passed through
        assert result == "mock_result"

    async def test_default_efficiency(self, tmp_path: Path) -> None:
        """calculate_plan_io uses default efficiency 1.0 if not specified."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        # Create plan without efficiency in production
        plan: dict[str, Any] = {
            "name": "No Efficiency Plan",
            "planet": "XK-001a",
            "habitation": [{"building": "HB1", "count": 1}],
            "production": [{"recipe": "1xA=>1xB", "count": 1}],  # No efficiency
        }
        # Manually add to bypass validation
        storage._plans = {"No Efficiency Plan": plan}

        mock_permit_io = AsyncMock(return_value="mock_result")

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            with patch("prun_mcp.tools.base_plans.calculate_permit_io", mock_permit_io):
                await calculate_plan_io("No Efficiency Plan", "CI1")

        call_kwargs = mock_permit_io.call_args.kwargs
        production = call_kwargs["production"]
        assert production[0]["efficiency"] == 1.0  # Default


class TestCalculatePlanIoWithExtraction:
    """Tests for calculate_plan_io with extraction."""

    async def test_extraction_passed_to_permit_io(self, tmp_path: Path) -> None:
        """calculate_plan_io passes extraction to calculate_permit_io."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        # Create plan with extraction
        plan: dict[str, Any] = {
            "name": "Extraction Plan",
            "planet": "XK-001a",
            "habitation": [{"building": "HB1", "count": 1}],
            "production": [{"recipe": "1xA=>1xB", "count": 1, "efficiency": 1.0}],
            "extraction": [
                {"building": "EXT", "resource": "FEO", "count": 2, "efficiency": 1.4}
            ],
        }
        storage._plans = {"Extraction Plan": plan}

        mock_permit_io = AsyncMock(return_value="mock_result")

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            with patch("prun_mcp.tools.base_plans.calculate_permit_io", mock_permit_io):
                result = await calculate_plan_io("Extraction Plan", "CI1")

        # Verify extraction was passed
        call_kwargs = mock_permit_io.call_args.kwargs
        extraction = call_kwargs["extraction"]
        assert extraction is not None
        assert len(extraction) == 1
        assert extraction[0]["building"] == "EXT"  # type: ignore[index]
        assert extraction[0]["resource"] == "FEO"  # type: ignore[index]
        assert extraction[0]["count"] == 2  # type: ignore[index]
        assert extraction[0]["efficiency"] == 1.4  # type: ignore[index]

        # Verify planet was passed
        assert call_kwargs["planet"] == "XK-001a"

        assert result == "mock_result"

    async def test_no_extraction_passes_none(self, tmp_path: Path) -> None:
        """calculate_plan_io passes None for extraction if not in plan."""
        storage = BasePlanStorage(storage_dir=tmp_path)
        plan: dict[str, Any] = {
            "name": "No Extraction Plan",
            "planet": "XK-001a",
            "habitation": [{"building": "HB1", "count": 1}],
            "production": [{"recipe": "1xA=>1xB", "count": 1, "efficiency": 1.0}],
        }
        storage._plans = {"No Extraction Plan": plan}

        mock_permit_io = AsyncMock(return_value="mock_result")

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            with patch("prun_mcp.tools.base_plans.calculate_permit_io", mock_permit_io):
                await calculate_plan_io("No Extraction Plan", "CI1")

        call_kwargs = mock_permit_io.call_args.kwargs
        assert call_kwargs["extraction"] is None
        assert call_kwargs["planet"] is None


class TestSaveBasePlanWithExtraction:
    """Tests for save_base_plan with extraction."""

    async def test_save_with_extraction(self, tmp_path: Path) -> None:
        """save_base_plan stores extraction data."""
        storage = BasePlanStorage(storage_dir=tmp_path)

        with patch(
            "prun_mcp.tools.base_plans.get_base_plan_storage", return_value=storage
        ):
            result = await save_base_plan(
                name="Extraction Plan",
                planet="XK-001a",
                habitation=[{"building": "HB1", "count": 1}],
                production=[{"recipe": "1xA=>1xB", "count": 1, "efficiency": 1.0}],
                extraction=[
                    {
                        "building": "EXT",
                        "resource": "FEO",
                        "count": 2,
                        "efficiency": 1.4,
                    }
                ],
            )

        assert isinstance(result, str)
        decoded = toon_decode(result)
        plan = decoded["plan"]  # type: ignore[index]
        assert "extraction" in plan  # type: ignore[operator]
        extraction = plan["extraction"]  # type: ignore[index]
        assert len(extraction) == 1
        assert extraction[0]["building"] == "EXT"  # type: ignore[index]


class TestGetBasePlanStorage:
    """Tests for singleton storage access."""

    def test_returns_same_instance(self) -> None:
        """get_base_plan_storage returns same instance."""
        # Clear any existing instance
        import prun_mcp.tools.base_plans as module

        module._base_plan_storage = None

        storage1 = get_base_plan_storage()
        storage2 = get_base_plan_storage()

        assert storage1 is storage2

        # Clean up
        module._base_plan_storage = None
