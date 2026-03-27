"""NF — Non-functional tests: file sizes, structure, build."""
import os

import pytest


_BACKEND_ROOT = os.path.join(os.path.dirname(__file__), "..")
_FRONTEND_ROOT = os.path.join(_BACKEND_ROOT, "..", "frontend", "nova-app")


class TestFileSizes:
    """All source files should be under 500 lines."""

    def _count_lines(self, path: str) -> int:
        with open(path, "r") as f:
            return sum(1 for _ in f)

    @pytest.mark.parametrize("rel_path", [
        "app/api/evidence.py",
        "app/api/reports.py",
        "app/api/calibration.py",
        "app/api/conversations.py",
        "app/api/price.py",
        "app/api/admin.py",
        "app/api/admin_ai.py",
        "app/pricing_v2/calibration/harness.py",
        "app/pricing_v2/calibration/parser.py",
        "app/pricing_v2/calibration/fixtures.py",
        "mcp_server.py",
    ])
    def test_backend_file_under_500_lines(self, rel_path):
        path = os.path.join(_BACKEND_ROOT, rel_path)
        if os.path.exists(path):
            lines = self._count_lines(path)
            assert lines <= 500, f"{rel_path} has {lines} lines (max 500)"


class TestRouterRegistration:
    """All routers are properly registered in main.py."""

    def test_all_routers_registered(self):
        main_path = os.path.join(_BACKEND_ROOT, "app", "main.py")
        with open(main_path, "r") as f:
            content = f.read()

        expected_modules = [
            "evidence",
            "reports",
            "conversations",
            "calibration",
        ]
        for module in expected_modules:
            assert module in content, f"Router '{module}' not found in main.py"


class TestRequirements:
    """requirements.txt has all needed packages."""

    def test_fastmcp_in_requirements(self):
        path = os.path.join(_BACKEND_ROOT, "requirements.txt")
        with open(path, "r") as f:
            content = f.read()
        assert "fastmcp" in content
