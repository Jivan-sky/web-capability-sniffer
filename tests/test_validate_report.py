from __future__ import annotations

import importlib.util
import re
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
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        errors, _warnings = VALIDATOR.validate(text)
        self.assertEqual([], errors)

    def test_incomplete_report_fails(self) -> None:
        errors, _warnings = VALIDATOR.validate("# 探查结果\n\n暂无。\n")
        self.assertTrue(errors)

    def test_secret_like_report_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        errors, _warnings = VALIDATOR.validate(text + "\nAuthorization: Bearer abcdefghijklmnop\n")
        self.assertTrue(any("敏感信息" in error for error in errors))

    def test_missing_preflight_authorization_check_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace(
            "- 运行前权限边界确认：已询问并记录目标、同前缀范围、账号性质、允许操作类别、禁止操作类别和最终确认边界。\n",
            "",
        )
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("运行前权限边界确认" in error for error in errors))

    def test_preflight_question_template_uses_operation_classes(self) -> None:
        text = (ROOT / "references" / "boundaries.md").read_text(encoding="utf-8")
        match = re.search(r"询问模板：\n\n```text\n(.*?)\n```", text, re.S)
        self.assertIsNotNone(match)
        template = match.group(1)
        self.assertIn("操作类别", template)
        self.assertNotIn("生图", template)
        self.assertNotIn("API Key", template)

    def test_preflight_question_template_omits_runtime_only_details(self) -> None:
        text = (ROOT / "references" / "boundaries.md").read_text(encoding="utf-8")
        match = re.search(r"询问模板：\n\n```text\n(.*?)\n```", text, re.S)
        self.assertIsNotNone(match)
        template = match.group(1)
        self.assertIn("同前缀", template)
        self.assertNotIn("数据和预算边界", template)
        self.assertNotIn("停止条件", template)

    def test_cli_ready_example_passes(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        errors, _warnings = VALIDATOR.validate(text)
        self.assertEqual([], errors)

    def test_cli_ready_report_without_request_index_fails(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("## 7. 请求契约索引", "## 7. 接口清单")
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("请求契约索引" in error for error in errors))

    def test_cli_ready_report_with_unknown_capability_id_fails(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        head, _, tail = text.partition("## 5. CLI-ready 契约表")
        text = head + "## 5. CLI-ready 契约表" + tail.replace("IMPL-LIST-01", "IMPL-LIST-99", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("IMPL-LIST-99" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
