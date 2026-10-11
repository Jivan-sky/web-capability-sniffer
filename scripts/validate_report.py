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
    "统一社会信用代码": re.compile(r"(?<![0-9A-Z])(?=[0-9A-HJ-NPQRTUWXY]{0,17}[A-HJ-NPQRTUWXY])[0-9A-HJ-NPQRTUWXY]{18}(?![0-9A-Z])"),
    "内网 IP 地址": re.compile(r"\b(?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}|192\.168)\.\d{1,3}\b"),
    "疑似 API 密钥": re.compile(r"(?i)\b(?:sk|ak|api[_-]?key)[-_][A-Za-z0-9]{16,}\b"),
    "URL 内嵌账号密码": re.compile(r"(?i)https?://[^\s/@]+:[^\s/@]+@"),
    "疑似签名参数": re.compile(r"(?i)[?&](?:sign|sig|signature|ciphertext|encrypt)="),
}


# Report format routing. Both report templates share this validator.
FORMAT_FULL = "full_exploration_report"
FORMAT_CLI_READY = "cli_ready_report"

FORMAT_LABELS = {
    FORMAT_FULL: "完整探查报告",
    FORMAT_CLI_READY: "CLI-ready 复嗅探报告",
}

FULL_REPORT_MARKER = "功能地图"
CLI_READY_MARKER = "CLI-ready 契约表"

CLI_READY_SECTIONS = {
    "明确判断": ("明确判断",),
    "范围、口径与安全结果": ("范围", "安全结果"),
    "能力与命令树分层": ("能力与命令树分层",),
    "CLI-ready 契约表": ("CLI-ready 契约表",),
    "请求契约索引": ("请求契约索引",),
    "异常与盲区": ("异常", "盲区"),
    "验收结论": ("验收结论",),
    "结束边界": ("结束边界",),
}

CAPABILITY_ROW_FIELDS = (
    "capability_id",
    "层级",
    "能力",
    "状态",
    "证据等级",
    "风险分类",
    "CLI适配",
    "CLI建议命令名",
)

CLI_CONTRACT_FIELDS = (
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

REQUEST_INDEX_FIELDS = (
    "方法",
    "脱敏路径",
    "触发动作",
    "参数轮廓",
    "响应轮廓",
    "异常表现",
    "证据等级",
)

ALLOWED_CAPABILITY_STATUSES = {
    "已验证 API",
    "页面已验证但 API 未确认",
    "仅入口",
    "无法访问",
    "写操作未执行",
}

ALLOWED_CLI_FIT = {"是", "草案", "待验证", "待授权验证", "禁用占位", "否"}

SAFETY_ZERO_METRICS = {
    "生产副作用": ("生产副作用",),
    "凭据或载荷输出": ("cookie", "token", "凭据", "载荷", "请求头"),
    "权限、验证码、风控或反爬绕过": ("绕过",),
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


def _check_referenced_ids(
    errors: list[str],
    label: str,
    column_label: str,
    rows: list[tuple[int, list[str]]],
    field_count: int,
    index: int,
    known: set[str],
    prefix: str,
) -> None:
    for line_number, cells in rows:
        if len(cells) != field_count:
            continue
        for identifier in re.findall(rf"{prefix}-\d+", cells[index]):
            if identifier not in known:
                errors.append(f"{label}第 {line_number} 行 {column_label} 引用了不存在的 {identifier}")


def detect_format(text: str) -> str | None:
    if CLI_READY_MARKER in text:
        return FORMAT_CLI_READY
    if FULL_REPORT_MARKER in text:
        return FORMAT_FULL
    return None


def _safety_metrics(lines: list[str]) -> dict[str, str]:
    header_index, rows = _find_table(lines, ("指标", "结果"))
    if header_index is None:
        return {}
    return {cells[0]: cells[1] for _, cells in rows if len(cells) == 2}


def _validate_cli_ready_report(text: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    headings = _headings(text)
    for label, alternatives in CLI_READY_SECTIONS.items():
        if not any(any(term in heading for term in alternatives) for heading in headings):
            errors.append(f"缺少必需章节：{label}")

    lines = text.splitlines()
    capability_rows = _validate_table(errors, lines, "能力与命令树分层", CAPABILITY_ROW_FIELDS)
    contract_rows = _validate_table(errors, lines, "CLI-ready 契约表", CLI_CONTRACT_FIELDS)
    request_rows = _validate_table(errors, lines, "请求契约索引", REQUEST_INDEX_FIELDS)

    for line_number, cells in capability_rows:
        if len(cells) != len(CAPABILITY_ROW_FIELDS):
            continue
        if cells[3] not in ALLOWED_CAPABILITY_STATUSES:
            errors.append(f"能力与命令树分层第 {line_number} 行状态不合法：{cells[3]}")
        if cells[4] not in ALLOWED_EVIDENCE_LEVELS:
            errors.append(f"能力与命令树分层第 {line_number} 行证据等级不合法：{cells[4]}")
        if cells[5] not in ALLOWED_RISK_CLASSES:
            errors.append(f"能力与命令树分层第 {line_number} 行风险分类不合法：{cells[5]}")
        if cells[6] not in ALLOWED_CLI_FIT:
            errors.append(f"能力与命令树分层第 {line_number} 行 CLI适配 不合法：{cells[6]}")

    for line_number, cells in contract_rows:
        if len(cells) != len(CLI_CONTRACT_FIELDS):
            continue
        if cells[3] not in ALLOWED_CAPABILITY_STATUSES:
            errors.append(f"CLI-ready 契约表第 {line_number} 行状态不合法：{cells[3]}")
        if cells[4] not in ALLOWED_EVIDENCE_LEVELS:
            errors.append(f"CLI-ready 契约表第 {line_number} 行证据等级不合法：{cells[4]}")
        if cells[5] not in ALLOWED_RISK_CLASSES:
            errors.append(f"CLI-ready 契约表第 {line_number} 行风险分类不合法：{cells[5]}")
        if cells[18] not in ALLOWED_CLI_FIT:
            errors.append(f"CLI-ready 契约表第 {line_number} 行是否适合封装 CLI 不合法：{cells[18]}")
        if cells[18] == "是" and (cells[3] != "已验证 API" or cells[4] != "高"):
            errors.append(
                f"CLI-ready 契约表第 {line_number} 行标记可封装 CLI，但状态不是 已验证 API 或证据等级不是 高"
            )

    for line_number, cells in request_rows:
        if len(cells) != len(REQUEST_INDEX_FIELDS):
            continue
        if cells[6] not in ALLOWED_EVIDENCE_LEVELS:
            errors.append(f"请求契约索引第 {line_number} 行证据等级不合法：{cells[6]}")

    capability_ids = {
        cells[0] for _, cells in capability_rows if len(cells) == len(CAPABILITY_ROW_FIELDS)
    }
    contract_ids = {
        cells[0] for _, cells in contract_rows if len(cells) == len(CLI_CONTRACT_FIELDS)
    }
    for identifier in sorted(capability_ids - contract_ids):
        errors.append(f"能力与命令树分层中的 {identifier} 未出现在 CLI-ready 契约表")
    for identifier in sorted(contract_ids - capability_ids):
        errors.append(f"CLI-ready 契约表中的 {identifier} 未出现在能力与命令树分层")

    metrics = _safety_metrics(lines)
    if not metrics:
        errors.append("未找到安全结果表（指标 | 结果）")
    for label, keywords in SAFETY_ZERO_METRICS.items():
        hit = next(
            (
                value
                for name, value in metrics.items()
                if any(keyword in name.lower() for keyword in keywords)
            ),
            None,
        )
        if hit is None:
            errors.append(f"安全结果表缺少指标：{label}")
        elif hit.strip().strip("`") != "0":
            errors.append(f"安全结果表 {label} 不为 0：{hit}")

    if not re.search(r"当前是否允许直接封装\s*CLI\s*[：:]\s*`?(?:是|否|未评估)", text):
        errors.append("未明确回答当前是否允许直接封装 CLI：是/否/未评估")

    for label, pattern in FORBIDDEN_PATTERNS.items():
        if pattern.search(text):
            errors.append(f"发现疑似敏感信息：{label}")

    if "user_confirmed" not in text and "runtime_observed" not in text:
        warnings.append("未显式标注证据来源类型")
    if "不直接生成" not in text:
        warnings.append("未明确说明不直接生成 CLI、Skill 或 Plugin")

    return errors, warnings


def validate(text: str) -> tuple[list[str], list[str]]:
    detected = detect_format(text)
    if detected is None:
        return (["无法识别的报告格式：既不是完整探查报告，也不是 CLI-ready 复嗅探报告"], [])
    if detected == FORMAT_CLI_READY:
        return _validate_cli_ready_report(text)
    return _validate_full_report(text)


def _validate_full_report(text: str) -> tuple[list[str], list[str]]:
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

    feature_ids = {cells[0] for _, cells in feature_rows if len(cells) == len(FEATURE_FIELDS)}
    flow_ids = {cells[0] for _, cells in flow_rows if len(cells) == len(FLOW_FIELDS)}
    step_ids = {cells[0] for _, cells in step_rows if len(cells) == len(STEP_FIELDS)}
    evidence_ids = {cells[0] for _, cells in evidence_rows if len(cells) == len(EVIDENCE_FIELDS)}

    for line_number, cells in feature_rows:
        if len(cells) != len(FEATURE_FIELDS):
            continue
        if not re.fullmatch(r"FEAT-\d{3,}", cells[0]):
            errors.append(f"功能地图第 {line_number} 行 feature_id 格式不合法：{cells[0]}")

    for line_number, cells in flow_rows:
        if len(cells) != len(FLOW_FIELDS):
            continue
        if not re.fullmatch(r"FLOW-\d{3,}", cells[0]):
            errors.append(f"Flow 清单第 {line_number} 行 flow_id 格式不合法：{cells[0]}")

    _check_referenced_ids(errors, "功能地图", "关联 flow_id", feature_rows, len(FEATURE_FIELDS), 8, flow_ids, "FLOW")
    _check_referenced_ids(errors, "功能地图", "关联 evidence_id", feature_rows, len(FEATURE_FIELDS), 9, evidence_ids, "EVID")
    _check_referenced_ids(errors, "Flow 清单", "所属 feature_id", flow_rows, len(FLOW_FIELDS), 2, feature_ids, "FEAT")
    _check_referenced_ids(errors, "Flow 清单", "Step 列表", flow_rows, len(FLOW_FIELDS), 5, step_ids, "STEP")
    _check_referenced_ids(errors, "Step 证据", "flow_id", step_rows, len(STEP_FIELDS), 1, flow_ids, "FLOW")
    _check_referenced_ids(errors, "Step 证据", "网络证据", step_rows, len(STEP_FIELDS), 6, evidence_ids, "EVID")

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
    detected = detect_format(text)
    if detected is not None:
        print(f"FORMAT: {FORMAT_LABELS[detected]}")
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
