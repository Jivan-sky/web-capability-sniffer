#!/usr/bin/env python3
"""Validate web exploration reports for structure, traceability, and secret hygiene."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_GROUPS = {
    "明确判断": ("明确判断",),
    "范围、口径与安全结果": ("范围", "安全结果"),
    "功能地图": ("功能地图",),
    "Flow 清单": ("Flow 清单", "流程清单"),
    "Step 证据": ("Step 证据", "步骤证据"),
    "Evidence 索引": ("Evidence 索引", "证据索引"),
    "网络请求索引": ("网络请求索引", "请求索引"),
    "人工审核清单": ("人工审核", "审核清单"),
    "发布物草稿": ("发布物", "操作手册", "培训材料"),
    "风险、未执行动作与盲区": ("风险", "未执行", "盲区"),
    "验收结论": ("验收结论",),
}

FEATURE_FIELDS = (
    "feature_id",
    "模块",
    "页面/入口",
    "功能名称",
    "角色线索",
    "状态",
    "风险分类",
    "证据等级",
    "关联 flow_id",
    "关联 evidence_id",
    "人工审核建议",
)

FLOW_FIELDS = (
    "flow_id",
    "流程名称",
    "所属 feature_id",
    "角色/前置条件",
    "触发入口",
    "Step 列表",
    "可重放状态",
    "验证状态",
    "输出用途",
)

STEP_FIELDS = (
    "step_id",
    "flow_id",
    "动作类型",
    "目标/选择器线索",
    "输入数据策略",
    "页面结果",
    "网络证据",
    "副作用判断",
    "可重放线索",
)

EVIDENCE_FIELDS = (
    "evidence_id",
    "来源类型",
    "采集方式",
    "触发 step_id",
    "脱敏 URL/路径",
    "请求轮廓",
    "页面轮廓",
    "置信度",
    "限制/盲区",
)

ALLOWED_FEATURE_STATUSES = {
    "已验证",
    "页面已验证",
    "仅入口",
    "无法访问",
    "未执行",
    "仅推断",
}

ALLOWED_RISK_CLASSES = {
    "只读安全",
    "敏感查询",
    "数据导出",
    "生产写入",
    "对外发送",
    "权限或配置变更",
    "未知风险",
}

ALLOWED_EVIDENCE_LEVELS = {"高", "中高", "中", "低", "不可用"}
ALLOWED_REVIEW_ACTIONS = {"确认", "合并", "排除", "补探", "需 owner 定义"}
ALLOWED_REPLAY_STATUSES = {"可重放", "部分可重放", "不可重放", "未验证"}
ALLOWED_VALIDATION_STATUSES = {"已验证", "按需验证通过", "待验证", "阻断"}

FORBIDDEN_PATTERNS = {
    "Authorization 值": re.compile(
        r"(?i)authorization\s*[:=]\s*(?:bearer\s+)?[A-Za-z0-9._~+/-]{12,}"
    ),
    "Bearer Token": re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/-]{12,}"),
    "Cookie 值": re.compile(r"(?i)(?:^|\s)cookie\s*[:=]\s*[^\n]{12,}"),
    "SSO Token": re.compile(r"(?i)sso[_-]?token\s*=\s*[^\s;]{8,}"),
    "Session 值": re.compile(r"(?i)session(?:_id)?\s*=\s*[^\s;]{8,}"),
    "URL 敏感参数": re.compile(
        r"(?i)https?://[^\s)]+[?&](?:token|session|signature|authorization)=[^&\s)]*"
    ),
    "邮箱地址": re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    "中国大陆手机号": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "疑似长订单号": re.compile(r"(?<![\d/-])\d{13,}(?![\d/-])"),
}


def _headings(text: str) -> list[str]:
    return [line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")]


def _find_table(lines: list[str], required_fields: tuple[str, ...]) -> tuple[int | None, list[tuple[int, list[str]]]]:
    header_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.startswith("|") and all(field in line for field in required_fields)
        ),
        None,
    )
    if header_index is None:
        return None, []

    rows: list[tuple[int, list[str]]] = []
    for index in range(header_index + 2, len(lines)):
        line = lines[index]
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        rows.append((index + 1, cells))
    return header_index, rows


def _validate_table(
    errors: list[str],
    lines: list[str],
    label: str,
    fields: tuple[str, ...],
) -> list[tuple[int, list[str]]]:
    header_index, rows = _find_table(lines, fields)
    if header_index is None:
        errors.append(f"未找到{label}表头")
        return []
    if not rows:
        errors.append(f"{label}没有记录")
        return []
    for line_number, cells in rows:
        if len(cells) != len(fields):
            errors.append(f"{label}第 {line_number} 行字段数为 {len(cells)}，应为 {len(fields)}")
            continue
        if any(not cell for cell in cells):
            errors.append(f"{label}第 {line_number} 行存在空字段；未知值应写未取得/待确认/不适用")
    return rows


def validate(text: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    headings = _headings(text)
    for label, alternatives in REQUIRED_GROUPS.items():
        if not any(any(term in heading for term in alternatives) for heading in headings):
            errors.append(f"缺少必需章节：{label}")

    for field_group in (FEATURE_FIELDS, FLOW_FIELDS, STEP_FIELDS, EVIDENCE_FIELDS):
        for field in field_group:
            if field not in text:
                errors.append(f"缺少必需字段：{field}")

    lines = text.splitlines()
    feature_rows = _validate_table(errors, lines, "功能地图", FEATURE_FIELDS)
    flow_rows = _validate_table(errors, lines, "Flow 清单", FLOW_FIELDS)
    step_rows = _validate_table(errors, lines, "Step 证据", STEP_FIELDS)
    evidence_rows = _validate_table(errors, lines, "Evidence 索引", EVIDENCE_FIELDS)

    for line_number, cells in feature_rows:
        if len(cells) != len(FEATURE_FIELDS):
            continue
        if cells[5] not in ALLOWED_FEATURE_STATUSES:
            errors.append(f"功能地图第 {line_number} 行状态不合法：{cells[5]}")
        if cells[6] not in ALLOWED_RISK_CLASSES:
            errors.append(f"功能地图第 {line_number} 行风险分类不合法：{cells[6]}")
        if cells[7] not in ALLOWED_EVIDENCE_LEVELS:
            errors.append(f"功能地图第 {line_number} 行证据等级不合法：{cells[7]}")
        if cells[10] not in ALLOWED_REVIEW_ACTIONS:
            errors.append(f"功能地图第 {line_number} 行人工审核建议不合法：{cells[10]}")

    for line_number, cells in flow_rows:
        if len(cells) != len(FLOW_FIELDS):
            continue
        if not re.search(r"STEP-\d{3}", cells[5]):
            errors.append(f"Flow 清单第 {line_number} 行未引用 step_id")
        if cells[6] not in ALLOWED_REPLAY_STATUSES:
            errors.append(f"Flow 清单第 {line_number} 行可重放状态不合法：{cells[6]}")
        if cells[7] not in ALLOWED_VALIDATION_STATUSES:
            errors.append(f"Flow 清单第 {line_number} 行验证状态不合法：{cells[7]}")

    for line_number, cells in step_rows:
        if len(cells) != len(STEP_FIELDS):
            continue
        if not cells[0].startswith("STEP-"):
            errors.append(f"Step 证据第 {line_number} 行 step_id 格式不合法：{cells[0]}")
        if "只读" not in cells[7] and "只识别" not in cells[7] and "未知风险" not in cells[7]:
            errors.append(f"Step 证据第 {line_number} 行副作用判断不清：{cells[7]}")

    for line_number, cells in evidence_rows:
        if len(cells) != len(EVIDENCE_FIELDS):
            continue
        if not cells[0].startswith("EVID-"):
            errors.append(f"Evidence 索引第 {line_number} 行 evidence_id 格式不合法：{cells[0]}")
        if cells[7] not in ALLOWED_EVIDENCE_LEVELS:
            errors.append(f"Evidence 索引第 {line_number} 行置信度不合法：{cells[7]}")

    if not re.search(r"生产副作用\s*[：:]\s*`?0`?", text):
        errors.append("未明确报告生产副作用：0")
    if not re.search(r"凭据泄露\s*[：:]\s*`?0`?", text):
        errors.append("未明确报告凭据泄露：0")
    if not re.search(r"权限绕过\s*[：:]\s*`?0`?", text):
        errors.append("未明确报告权限绕过：0")
    if not re.search(r"当前是否允许直接封装\s*CLI\s*[：:]\s*(?:`)?(?:是|否|未评估)(?:`)?", text):
        errors.append("未明确回答当前是否允许直接封装 CLI：是/否/未评估")

    required_terms = ("一级导航模块", "顶部入口", "全局能力", "二级菜单能力")
    for term in required_terms:
        if term not in text:
            errors.append(f"未区分统计项：{term}")
    if "副作用授权范围" not in text:
        errors.append("未明确报告副作用授权范围")
    if "运行前权限边界确认" not in text:
        errors.append("未明确报告运行前权限边界确认")

    for label, pattern in FORBIDDEN_PATTERNS.items():
        if pattern.search(text):
            errors.append(f"发现疑似敏感信息：{label}")

    if "user_confirmed" not in text and "runtime_observed" not in text:
        warnings.append("未显式标注证据来源类型")
    if "未取得" not in text and "待确认" not in text and "不适用" not in text:
        warnings.append("未知字段未使用未取得/待确认/不适用标注")
    if "不生成" not in text and "不直接生成" not in text:
        warnings.append("未明确说明不直接生成 CLI、Skill 或 Plugin")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="校验网页系统功能探查报告")
    parser.add_argument("report", type=Path)
    args = parser.parse_args()

    text = args.report.read_text(encoding="utf-8")
    errors, warnings = validate(text)

    for item in warnings:
        print(f"WARNING: {item}")
    for item in errors:
        print(f"ERROR: {item}")

    if errors:
        return 1
    print("OK: 探查报告结构、证据追踪与敏感信息基础检查通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
