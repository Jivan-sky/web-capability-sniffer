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

    def test_missing_write_zero_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("- 探索阶段写操作执行：0\n", "")
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("探索阶段写操作执行" in error for error in errors))

    def test_nonzero_write_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace(
            "- 探索阶段写操作执行：0\n",
            "- 探索阶段写操作执行：1\n",
        )
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("探索阶段写操作执行不为 0" in error for error in errors))

    def test_authorization_boundary_must_be_no(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("授权是否改变执行边界：否", "授权是否改变执行边界：是")
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("授权是否改变执行边界" in error for error in errors))

    def test_missing_runtime_guard_declaration_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace(
            "- 运行时写保护：已启用（BrowserContext 级默认拒绝；"
            "`allowReadPostPaths` 与 `allowSessionPostPaths` 均为空；本次阻断 0 次）。\n",
            "",
        )
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("运行时写保护" in error for error in errors))

    def test_disabled_runtime_guard_requires_compensating_controls(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace(
            "- 运行时写保护：已启用（BrowserContext 级默认拒绝；"
            "`allowReadPostPaths` 与 `allowSessionPostPaths` 均为空；本次阻断 0 次）。\n",
            "- 运行时写保护：未启用。\n",
        )
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("补偿控制" in error for error in errors))

    def test_enabled_runtime_guard_must_name_both_allowlists(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("`allowSessionPostPaths` 均为空", "`allowSessionPostPaths` 未声明")
        text = text.replace("`allowSessionPostPaths` 未声明", "")
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("allowSessionPostPaths" in error for error in errors))

    def test_missing_database_boundary_declaration_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("- 数据库直连：否。\n", "")
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("数据库直连" in error for error in errors))

    def test_preflight_question_template_uses_operation_classes(self) -> None:
        text = (ROOT / "references" / "boundaries.md").read_text(encoding="utf-8")
        match = re.search(r"询问模板：\n\n```text\n(.*?)\n```", text, re.S)
        self.assertIsNotNone(match)
        template = match.group(1)
        self.assertIn("操作类别", template)
        self.assertNotIn("生图", template)
        self.assertNotIn("FoxAPI", template)
        self.assertNotIn("API Key", template)

    def test_preflight_question_template_omits_runtime_only_details(self) -> None:
        text = (ROOT / "references" / "boundaries.md").read_text(encoding="utf-8")
        match = re.search(r"询问模板：\n\n```text\n(.*?)\n```", text, re.S)
        self.assertIsNotNone(match)
        template = match.group(1)
        self.assertIn("同 origin", template)
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

    def test_cli_ready_report_missing_write_zero_fails(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("| 探索阶段写操作执行 | 0 |\n", "")
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("探索阶段写操作执行" in error for error in errors))

    def test_cli_ready_write_risk_cannot_be_ready(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        old = "| WRITE-CONFIG-01 | 二级菜单 | 配置列与黑名单维护 | 写操作未执行 | 低 | 权限或配置变更 | 禁用占位 | `customer config`（禁用） |"
        new = "| WRITE-CONFIG-01 | 二级菜单 | 配置列与黑名单维护 | 写操作未执行 | 低 | 权限或配置变更 | 是 | `customer config`（禁用） |"
        self.assertIn(old, text)
        text = text.replace(old, new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("写风险能力" in error for error in errors))

    def test_deprecated_waiting_authorization_value_fails(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("| 禁用占位 |", "| 待授权验证 |", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("待授权验证" in error for error in errors))

    def test_traceability_placeholder_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        old = "| FEAT-002 | 导出客户列表 | 数据导出 | 未取得 | 未取得 | 未取得 | 未演练 | 不可逆（文件离开系统） | 未取得 | 不可写 |"
        new = "| FEAT-002 | 导出客户列表 | 数据导出 | 待填 | 未取得 | 未取得 | 未演练 | 不可逆（文件离开系统） | 未取得 | 不可写 |"
        self.assertIn(old, text)
        text = text.replace(old, new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("占位值" in error for error in errors))

    def test_full_write_feature_cannot_be_verified(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        old = "| FEAT-002 | 客户管理 | 客户列表工具栏 | 导出客户列表 | 运营角色，待确认 | 未执行 | 数据导出 |"
        new = "| FEAT-002 | 客户管理 | 客户列表工具栏 | 导出客户列表 | 运营角色，待确认 | 已验证 | 数据导出 |"
        self.assertIn(old, text)
        text = text.replace(old, new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("写风险能力" in error for error in errors))

    def test_full_write_flow_cannot_be_replayable(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("| FEAT-001 | 已登录运营角色", "| FEAT-001, FEAT-002 | 已登录运营角色", 1)
        text = text.replace("| 部分可重放 |", "| 可重放 |", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("写风险能力" in error for error in errors))

    def test_full_write_step_cannot_be_marked_read_only(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("| FEAT-001 | 已登录运营角色", "| FEAT-001, FEAT-002 | 已登录运营角色", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(
            any("副作用判断只能是 只识别不执行/未知风险" in error for error in errors)
        )

    def test_full_write_traceability_cannot_be_read_only(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        old = "| FEAT-002 | 导出客户列表 | 数据导出 | 未取得 | 未取得 | 未取得 | 未演练 | 不可逆（文件离开系统） | 未取得 | 不可写 |"
        new = "| FEAT-002 | 导出客户列表 | 数据导出 | 未取得 | 未取得 | 未取得 | 未演练 | 不可逆（文件离开系统） | 未取得 | 只读安全 |"
        self.assertIn(old, text)
        text = text.replace(old, new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("不能得出 只读安全" in error for error in errors))

    def test_full_traceability_unknown_feature_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("| FEAT-002 | 导出客户列表 |", "| FEAT-999 | 导出客户列表 |", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("不存在的对象" in error for error in errors))

    def test_full_missing_traceability_for_write_feature_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        old = "| FEAT-002 | 导出客户列表 | 数据导出 | 未取得 | 未取得 | 未取得 | 未演练 | 不可逆（文件离开系统） | 未取得 | 不可写 |\n"
        self.assertIn(old, text)
        text = text.replace(old, "", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("缺少写风险对象" in error for error in errors))

    def test_full_snapshot_claim_requires_snapshot_and_rehearsal_evidence(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        old = "| FEAT-002 | 导出客户列表 | 数据导出 | 未取得 | 未取得 | 未取得 | 未演练 | 不可逆（文件离开系统） | 未取得 | 不可写 |"
        new = "| FEAT-002 | 导出客户列表 | 数据导出 | 未取得 | 未取得 | 未取得 | 未演练 | 不可逆（文件离开系统） | 未取得 | 可写但需快照 |"
        self.assertIn(old, text)
        text = text.replace(old, new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("没有快照/备份证据" in error for error in errors))

    def test_cli_write_contract_status_cannot_be_verified(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        old = "| WRITE-CONFIG-01 | 客户/项目/通知 | 配置列与黑名单维护 | 写操作未执行 |"
        new = "| WRITE-CONFIG-01 | 客户/项目/通知 | 配置列与黑名单维护 | 已验证 API |"
        self.assertIn(old, text)
        text = text.replace(old, new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("状态只能是 写操作未执行" in error for error in errors))

    def test_cli_write_contract_cannot_be_ready(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        old = "| 配置权限待确认 | 高 | 禁用占位 | `customer config`（禁用） |"
        new = "| 配置权限待确认 | 高 | 是 | `customer config`（禁用） |"
        self.assertIn(old, text)
        text = text.replace(old, new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("写风险能力" in error for error in errors))

    def test_cli_missing_traceability_for_write_feature_fails(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        old = "| WRITE-CONFIG-01 | 权限或配置变更 | 未取得 | 未取得 | 未取得 | 未演练 | 不适用 | 未取得 | 未知 |\n"
        self.assertIn(old, text)
        text = text.replace(old, "", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("缺少写风险对象" in error for error in errors))

    def test_cli_traceability_unknown_capability_fails(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("| WRITE-CONFIG-01 | 权限或配置变更 |", "| WRITE-UNKNOWN-01 | 权限或配置变更 |", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("不存在的对象" in error for error in errors))

    def test_cli_write_traceability_cannot_be_read_only(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        old = "| WRITE-CONFIG-01 | 权限或配置变更 | 未取得 | 未取得 | 未取得 | 未演练 | 不适用 | 未取得 | 未知 |"
        new = "| WRITE-CONFIG-01 | 权限或配置变更 | 未取得 | 未取得 | 未取得 | 未演练 | 不适用 | 未取得 | 只读安全 |"
        self.assertIn(old, text)
        text = text.replace(old, new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("不能得出 只读安全" in error for error in errors))

    def test_full_missing_traceability_table_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        marker = "### 10.1 可追溯与可回滚评估"
        start = text.index(marker)
        end = text.index("## 11. 验收结论", start)
        text = text[:start] + text[end:]
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("缺少写风险对象" in error for error in errors))

    def test_missing_request_provenance_fails(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        text = text.replace(
            "- 请求来源：页面自身触发；未复制、未重放、未导出 HAR、未保存完整请求/响应。\n",
            "",
        )
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("请求来源声明" in error for error in errors))

    def test_missing_request_provenance_detail_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace(
            "请求来源：页面自身触发；未复制、未重放、未导出 HAR、未保存完整请求/响应。",
            "请求来源：页面自身触发。",
        )
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("只读取证声明" in error for error in errors))

    def test_cli_missing_evidence_source_fails(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("runtime_observed", "unknown_source")
        text = text.replace("user_confirmed", "unknown_source")
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("证据来源类型" in error for error in errors))

    def test_full_invalid_evidence_source_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("| EVID-001 | runtime_observed |", "| EVID-001 | unknown_source |", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("来源类型不合法" in error for error in errors))

    def test_full_missing_write_operation_list_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("- 写操作执行清单：无\n", "")
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("写操作执行清单" in error for error in errors))

    def test_global_placeholder_outside_table_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text += "\nTODO\n"
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("占位值" in error for error in errors))

    def test_full_report_nonzero_production_side_effect_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("- 生产副作用：0\n", "- 生产副作用：1\n")
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("生产副作用不为 0" in error for error in errors))

    def test_cli_unknown_risk_is_treated_as_guarded(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        capability_old = (
            "| IMPL-LIST-01 | 一级导航 | 项目工单列表 | 已验证 API | 高 | 敏感查询 | 草案 |"
        )
        contract_old = (
            "| IMPL-LIST-01 | 项目 | 项目工单列表 | 已验证 API | 高 | 敏感查询 | GET |"
        )
        self.assertIn(capability_old, text)
        self.assertIn(contract_old, text)
        text = text.replace(capability_old, capability_old.replace("敏感查询", "未知风险"), 1)
        text = text.replace(contract_old, contract_old.replace("敏感查询", "未知风险"), 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("未知风险能力" in error for error in errors))
        self.assertTrue(any("缺少写风险对象：IMPL-LIST-01" in error for error in errors))

    def test_cli_cross_table_risk_mismatch_fails(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        old = (
            "| WRITE-CONFIG-01 | 客户/项目/通知 | 配置列与黑名单维护 | 写操作未执行 | 低 | 权限或配置变更 |"
        )
        new = (
            "| WRITE-CONFIG-01 | 客户/项目/通知 | 配置列与黑名单维护 | 写操作未执行 | 低 | 敏感查询 |"
        )
        self.assertIn(old, text)
        text = text.replace(old, new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("风险分类" in error and "不一致" in error for error in errors))

    def test_full_unknown_risk_cannot_be_verified(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        old = (
            "| FEAT-001 | 客户管理 | 客户列表 | 查询客户列表 | 运营角色，待确认 | 已验证 | 敏感查询 |"
        )
        new = (
            "| FEAT-001 | 客户管理 | 客户列表 | 查询客户列表 | 运营角色，待确认 | 已验证 | 未知风险 |"
        )
        self.assertIn(old, text)
        text = text.replace(old, new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("写风险能力" in error for error in errors))

    def test_full_unknown_risk_flow_cannot_be_replayable(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        old = (
            "| FEAT-001 | 客户管理 | 客户列表 | 查询客户列表 | 运营角色，待确认 | 已验证 | 敏感查询 |"
        )
        new = (
            "| FEAT-001 | 客户管理 | 客户列表 | 查询客户列表 | 运营角色，待确认 | 已验证 | 未知风险 |"
        )
        self.assertIn(old, text)
        text = text.replace(old, new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("可重放状态只能是 不可重放/未验证" in error for error in errors))

    def test_full_snapshot_claim_requires_audit_evidence(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        old = (
            "| FEAT-002 | 导出客户列表 | 数据导出 | 未取得 | 未取得 | 未取得 | 未演练 | 不可逆（文件离开系统） | 未取得 | 不可写 |"
        )
        new = (
            "| FEAT-002 | 导出客户列表 | 数据导出 | 未取得 | 未取得 | 有快照 | 已演练 | 不可逆（文件离开系统） | 未取得 | 可写但需快照 |"
        )
        self.assertIn(old, text)
        text = text.replace(old, new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("没有审计日志证据" in error for error in errors))

    def test_decorated_missing_evidence_is_rejected(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        old = (
            "| FEAT-002 | 导出客户列表 | 数据导出 | 未取得 | 未取得 | 未取得 | 未演练 | 不可逆（文件离开系统） | 未取得 | 不可写 |"
        )
        new = (
            "| FEAT-002 | 导出客户列表 | 数据导出 | 有审计 | 未取得 | 未取得（待补） | 已演练 | 不可逆（文件离开系统） | 未取得 | 可写但需快照 |"
        )
        self.assertIn(old, text)
        text = text.replace(old, new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("没有快照/备份证据" in error for error in errors))

    def test_cli_duplicate_safety_metric_nonzero_fails(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        old = "| 权限、验证码、风控或反爬绕过 | 0 |\n"
        self.assertIn(old, text)
        text = text.replace(old, old + "| 凭据输出 | 1 |\n", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("凭据或载荷输出 不为 0" in error for error in errors))

    def test_full_flow_without_feature_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace(
            "| FLOW-001 | 按条件查询客户列表 | FEAT-001 |",
            "| FLOW-001 | 按条件查询客户列表 | 无 |",
            1,
        )
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("未关联 feature_id" in error for error in errors))

    def test_full_step_without_flow_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace(
            "| STEP-001 | FLOW-001 | 打开 |", "| STEP-001 | 无 | 打开 |", 1
        )
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("未关联 flow_id" in error for error in errors))

    def test_missing_action_audit_log_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        text = text.replace("### 2.1 动作审计日志", "### 2.1 动作记录", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("动作审计日志" in error for error in errors))

    def test_b_action_cannot_be_marked_executed(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        old = "| B | 未执行 |"
        self.assertIn(old, text)
        text = text.replace(old, "| B | 已执行（只读） |", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("B 类动作执行状态只能是 未执行/阻断" in error for error in errors))

    def test_b_action_cannot_claim_page_triggered_request(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        old = "| B | 未执行 | 入口可见 | 未触发 |"
        self.assertIn(old, text)
        text = text.replace(old, "| B | 未执行 | 入口可见 | 页面自身触发 |", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("B 类动作的请求来源必须是未触发" in error for error in errors))

    def test_a_action_must_be_read_only_safe(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        old = "| 已执行（只读） | 成功 | 页面自身触发 | 只读安全 |"
        self.assertIn(old, text)
        text = text.replace(old, "| 已执行（只读） | 成功 | 页面自身触发 | 未知风险 |", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("A 类已执行动作的副作用判断必须是只读安全" in error for error in errors))

    def test_action_total_must_match_audit_rows(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("`动作总数：5`", text)
        text = text.replace("`动作总数：5`", "`动作总数：6`", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("动作总数=6 与实际记录数 5 不一致" in error for error in errors))

    def test_unknown_risk_cannot_conclude_snapshot_required(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        feature_old = "| FEAT-002 | 客户管理 | 客户列表工具栏 | 导出客户列表 | 运营角色，待确认 | 未执行 | 数据导出 |"
        feature_new = "| FEAT-002 | 客户管理 | 客户列表工具栏 | 导出客户列表 | 运营角色，待确认 | 未执行 | 未知风险 |"
        trace_old = "| FEAT-002 | 导出客户列表 | 数据导出 | 未取得 | 未取得 | 未取得 | 未演练 | 不可逆（文件离开系统） | 未取得 | 不可写 |"
        trace_new = "| FEAT-002 | 导出客户列表 | 数据导出 | 未取得 | 未取得 | 未取得 | 未演练 | 不可逆（文件离开系统） | 未取得 | 可写但需快照 |"
        self.assertIn(feature_old, text)
        self.assertIn(trace_old, text)
        text = text.replace(feature_old, feature_new, 1)
        text = text.replace(trace_old, trace_new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("补证前不能得出任何可写结论" in error for error in errors))

    def test_cli_ready_requires_all_contract_evidence(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        old = (
            "| IMPL-LIST-01 | 项目 | 项目工单列表 | 已验证 API | 高 | 敏感查询 | GET | "
            "`[业务服务]/api/projects/list` | `issue_type,current_page,page_size,stage`；"
            "凭据字段已省略 | `current_page/page_size:number`，其余待确认 | 均随默认请求出现；"
            "服务端必填性待确认 | `current_page,page_size` | 未取得 | `issue_type,stage`；"
            "页面另有区域、状态、日期、合同/客户筛选尚未映射 | `code:number; data.issue_list:array; "
            "data.total:number; msg:string` | 默认请求200；其他错误未取得 | 当前登录身份；"
            "项目模块权限待确认 | 高 | 草案 | `customer implementation list` | 补搜索/日期/状态参数映射、"
            "列表元素字段、必填性、空结果和权限失败 |"
        )
        new = (
            "| IMPL-LIST-01 | 项目 | 项目工单列表 | 已验证 API | 高 | 敏感查询 | 未取得 | "
            "未取得 | 未取得 | 未取得 | 未取得 | 未取得 | 未取得 | 未取得 | 未取得 | 未取得 | "
            "未取得 | 未知 | 是 | 未取得 | 补权限失败表现与错误码 |"
        )
        self.assertIn(old, text)
        text = text.replace(old, new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("HTTP 方法未验证" in error for error in errors))
        self.assertTrue(any("脱敏路径未取得" in error for error in errors))
        self.assertTrue(any("参数名未取得" in error for error in errors))
        self.assertTrue(any("参数类型未取得" in error for error in errors))
        self.assertTrue(any("是否必填未取得" in error for error in errors))
        self.assertTrue(any("分页字段未取得" in error for error in errors))
        self.assertTrue(any("排序字段未取得" in error for error in errors))
        self.assertTrue(any("筛选字段未取得" in error for error in errors))
        self.assertTrue(any("响应字段轮廓未取得" in error for error in errors))
        self.assertTrue(any("错误码或异常表现未取得" in error for error in errors))
        self.assertTrue(any("权限要求未取得" in error for error in errors))
        self.assertTrue(any("数据敏感级别未取得或不合法" in error for error in errors))
        self.assertTrue(any("CLI 建议命令名未取得" in error for error in errors))
        self.assertTrue(any("仍有补充证据缺口" in error for error in errors))

    def test_cli_fit_must_match_across_tables(self) -> None:
        text = (ROOT / "examples" / "customer-root-cli-ready-resniff.md").read_text(
            encoding="utf-8"
        )
        old = "| IMPL-LIST-01 | 一级导航 | 项目工单列表 | 已验证 API | 高 | 敏感查询 | 草案 | `customer implementation list` |"
        new = "| IMPL-LIST-01 | 一级导航 | 项目工单列表 | 已验证 API | 高 | 敏感查询 | 是 | `customer implementation list` |"
        self.assertIn(old, text)
        text = text.replace(old, new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("CLI 适配值" in error and "不一致" in error for error in errors))

    def test_data_export_cannot_ignore_irreversible_external_effect(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        old = "| FEAT-002 | 导出客户列表 | 数据导出 | 未取得 | 未取得 | 未取得 | 未演练 | 不可逆（文件离开系统） | 未取得 | 不可写 |"
        new = "| FEAT-002 | 导出客户列表 | 数据导出 | 有审计 | 有快照 | 有快照 | 已演练 | 不可逆（文件离开系统） | 未取得 | 可写但需审批 |"
        self.assertIn(old, text)
        text = text.replace(old, new, 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("外部副作用不可逆或未取证" in error for error in errors))

    def test_missing_markdown_separator_fails(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        old = "|---|---|---|---|---|---|---|---|---|---|\n"
        self.assertIn(old, text)
        text = text.replace(old, "\n", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("缺少合法的 Markdown 分隔行" in error for error in errors))

    def test_markdown_separator_column_count_must_match_header(self) -> None:
        text = (ROOT / "examples" / "exploration-report-example.md").read_text(
            encoding="utf-8"
        )
        old = "|---|---|---|---|---|---|---|---|---|---|\n"
        self.assertIn(old, text)
        text = text.replace(old, "|---|\n", 1)
        errors, _warnings = VALIDATOR.validate(text)
        self.assertTrue(any("表头分隔行列数" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
