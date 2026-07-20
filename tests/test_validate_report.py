from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_report", ROOT / "scripts" / "validate_report.py"
)
assert SPEC and SPEC.loader
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class ValidateReportTests(unittest.TestCase):
    def test_checked_in_example_passes(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        errors, _warnings = VALIDATOR.validate(text)
        self.assertEqual([], errors)

    def test_incomplete_report_fails(self) -> None:
        errors, _warnings = VALIDATOR.validate("# 嗅探结果\n\n暂无。\n")
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
