#!/usr/bin/env python3
"""Validate CLI-ready sniff report structure, evidence labels, and secret hygiene."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_GROUPS = {
    "明确判断": ("明确判断", "结论"),
    "范围与口径": ("范围", "口径", "页面概况", "页面状态"),
    "证据等级与风险规则": ("证据等级", "风险规则", "风险分类"),
    "能力与命令树分层": ("能力与命令树", "能力清单", "能力地图"),
    "CLI-ready 契约": ("CLI-ready 契约", "CLI ready 契约"),
    "差距清单": ("差距清单",),
    "请求契约": ("请求契约",),
    "风险与未执行动作": ("风险", "未执行动作"),
    "异常与盲区": ("异常", "盲区"),
    "验收结论": ("验收结论", "验收结果"),
}

REQUIRED_CONTRACT_FIELDS = (
    "capability_id",
    "模块",
    "能力名称",
    "状态",
    "证据等级",
    "风险分类",
    "HTTP 方法",
    "脱敏路径",
    "参数名",
    "参数类型",
    "是否必填",
    "分页字段",
    "排序字段",
    "筛选字段",
    "响应字段轮廓",
    "错误码或异常表现",
    "权限要求",
    "数据敏感级别",
    "是否适合封装 CLI",
    "CLI 建议命令名",
    "封装前还需补充的证据",
)

REQUIRED_EVIDENCE_LEVELS = ("高", "中高", "中", "低", "不可用")
REQUIRED_RISK_CLASSES = (
    "只读安全",
    "敏感查询",
    "数据导出",
    "生产写入",
    "对外发送",
    "权限或配置变更",
    "未知风险",
)

ALLOWED_STATUSES = {
    "已验证 API",
    "页面已验证但 API 未确认",
    "仅入口",
    "无法访问",
    "写操作未执行",
}
ALLOWED_CLI_DECISIONS = {"是", "草案", "待验证", "禁用占位", "否"}

FORBIDDEN_PATTERNS = {
    "Authorization 值": re.compile(
        r"(?i)authorization\s*[:=]\s*(?:bearer\s+)?[A-Za-z0-9._~+/-]{12,}"
    ),
    "Bearer Token": re.compile(r"(?i)bearer\s+[A-Za-z0-9._~+/-]{12,}"),
    "Cookie 值": re.compile(r"(?i)(?:^|\s)cookie\s*[:=]\s*[^\n]{12,}"),
    "SSO Token": re.compile(r"(?i)sso[_-]?token\s*=\s*[^\s;]{8,}"),
    "Session 值": re.compile(r"(?i)session(?:_id)?\s*=\s*[^\s;]{8,}"),
    "URL 敏感参数": re.compile(
        r"(?i)https?://[^\s)]+[?&](?:token|session|signature|authorization)=[^&\s)]+"
    ),
    "邮箱地址": re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"),
    "中国大陆手机号": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "疑似长订单号": re.compile(r"(?<![\d/-])\d{13,}(?![\d/-])"),
}


def validate(text: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    headings = [line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")]
    for label, alternatives in REQUIRED_GROUPS.items():
        if not any(any(term in heading for term in alternatives) for heading in headings):
            errors.append(f"缺少必需章节：{label}")

    for field in REQUIRED_CONTRACT_FIELDS:
        if field not in text:
            errors.append(f"CLI-ready 契约缺少字段：{field}")

    for level in REQUIRED_EVIDENCE_LEVELS:
        if not re.search(rf"(?:`|\|\s*){re.escape(level)}(?:`|\s*\|)", text):
            errors.append(f"未定义或使用证据等级：{level}")

    for risk in REQUIRED_RISK_CLASSES:
        if risk not in text:
            errors.append(f"未定义风险分类：{risk}")

    lines = text.splitlines()
    header_index = next(
        (
            index
            for index, line in enumerate(lines)
            if line.startswith("|")
            and "capability_id" in line
            and "HTTP 方法" in line
            and "封装前还需补充的证据" in line
        ),
        None,
    )
    if header_index is None:
        errors.append("未找到 CLI-ready 契约表表头")
    else:
        contract_rows: list[tuple[int, list[str]]] = []
        for index in range(header_index + 2, len(lines)):
            line = lines[index]
            if not line.startswith("|"):
                break
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            contract_rows.append((index + 1, cells))

        if not contract_rows:
            errors.append("CLI-ready 契约表没有能力记录")

        for line_number, cells in contract_rows:
            if len(cells) != len(REQUIRED_CONTRACT_FIELDS):
                errors.append(
                    f"契约表第 {line_number} 行字段数为 {len(cells)}，应为 {len(REQUIRED_CONTRACT_FIELDS)}"
                )
                continue
            if any(not cell for cell in cells):
                errors.append(f"契约表第 {line_number} 行存在空字段；未知值应写未取得/待确认")
            if cells[3] not in ALLOWED_STATUSES:
                errors.append(f"契约表第 {line_number} 行状态不合法：{cells[3]}")
            if cells[4] not in REQUIRED_EVIDENCE_LEVELS:
                errors.append(f"契约表第 {line_number} 行证据等级不合法：{cells[4]}")
            if cells[5] not in REQUIRED_RISK_CLASSES:
                errors.append(f"契约表第 {line_number} 行风险分类不合法：{cells[5]}")
            if cells[18] not in ALLOWED_CLI_DECISIONS:
                errors.append(f"契约表第 {line_number} 行 CLI 适配判断不合法：{cells[18]}")

    if not re.search(r"当前是否允许直接封装\s*CLI\s*[：:]\s*(?:\*\*)?(?:是|否)", text):
        errors.append("未明确回答当前是否允许直接封装 CLI：是/否")

    if "一级导航模块" not in text or "顶部入口" not in text or "全局能力" not in text:
        errors.append("未区分一级导航模块、顶部入口和全局能力")

    for label, pattern in FORBIDDEN_PATTERNS.items():
        if pattern.search(text):
            errors.append(f"发现疑似敏感信息：{label}")

    if "生产副作用" not in text:
        warnings.append("未明确报告生产副作用结果")
    if "未执行" not in text:
        warnings.append("未明确列出未执行动作")
    if "未取得" not in text and "待确认" not in text:
        warnings.append("契约未明确使用‘未取得/待确认’标注未知字段")
    if "不直接生成 CLI" not in text and "不生成" not in text:
        warnings.append("未明确说明报告不直接生成 CLI")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 CLI-ready 网页嗅探报告")
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
    print("OK: CLI-ready 报告结构、口径与敏感信息基础检查通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
