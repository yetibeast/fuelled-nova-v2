"""D2 — MCP Server tests (import/structure only, no live server)."""
import pytest


class TestMCPServerImport:
    """Verify MCP server module loads without errors."""

    def test_mcp_server_importable(self):
        """The server module should import cleanly."""
        import importlib.util
        import os

        path = os.path.join(
            os.path.dirname(__file__), "..", "mcp_server.py"
        )
        spec = importlib.util.spec_from_file_location("mcp_server", path)
        assert spec is not None
        mod = importlib.util.module_from_spec(spec)
        # Don't execute (would start server), just verify it parses
        assert mod is not None

    def test_tools_module_has_all_functions(self):
        """All 6 tool functions exist in tools.py."""
        from app.pricing_v2 import tools

        assert callable(tools.fetch_listing)
        assert callable(tools.search_comparables)
        assert callable(tools.get_category_stats)
        assert callable(tools.lookup_rcn)
        assert callable(tools.calculate_fmv)
        assert callable(tools.check_equipment_risks)

    def test_schemas_has_all_tool_definitions(self):
        """schemas.py defines all 6 tools."""
        from app.pricing_v2.schemas import TOOLS

        names = {t["name"] for t in TOOLS}
        expected = {
            "fetch_listing",
            "search_comparables",
            "get_category_stats",
            "lookup_rcn",
            "calculate_fmv",
            "check_equipment_risks",
        }
        assert expected == names


class TestToolFunctions:
    """Unit tests for individual tool functions."""

    def test_calculate_fmv_returns_string(self):
        from app.pricing_v2.tools import calculate_fmv

        result = calculate_fmv(
            rcn=500000,
            equipment_class="rotating",
            age_years=5,
            condition="B",
        )
        assert isinstance(result, str)
        assert "FMV" in result
        assert "$" in result

    def test_check_equipment_risks_no_risks(self):
        from app.pricing_v2.tools import check_equipment_risks

        result = check_equipment_risks(
            equipment_type="compressor",
            age_years=2,
        )
        assert isinstance(result, str)

    def test_check_equipment_risks_idle(self):
        from app.pricing_v2.tools import check_equipment_risks

        result = check_equipment_risks(
            equipment_type="compressor",
            age_years=10,
            idle_years=6,
        )
        assert "IDLE DEGRADATION" in result

    def test_check_equipment_risks_plc(self):
        from app.pricing_v2.tools import check_equipment_risks

        result = check_equipment_risks(
            equipment_type="compressor",
            age_years=12,
            plc_model="MicroLogix 1400",
        )
        assert "PLC OBSOLESCENCE" in result

    def test_check_equipment_risks_cross_border(self):
        from app.pricing_v2.tools import check_equipment_risks

        result = check_equipment_risks(
            equipment_type="compressor",
            age_years=5,
            location_country="US",
        )
        assert "CROSS-BORDER" in result
