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
    "动作审计日志": ("动作审计日志",),
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
ALLOWED_EVIDENCE_SOURCES = {
    "user_confirmed",
    "runtime_observed",
    "repository_artifact",
    "document_clue",
    "hypothesis",
}

AUDIT_FIELDS = (
    "序号",
    "时间",
    "URL/路径",
    "动作",
    "等级",
    "执行状态",
    "结果",
    "请求来源",
    "副作用判断",
    "证据 ID",
)

ALLOWED_AUDIT_LEVELS = {"A", "B", "C"}
ALLOWED_AUDIT_EFFECTS = {"只读安全", "只识别不执行", "未知风险"}
ALLOWED_STEP_EFFECTS = {"只读安全", "只识别不执行", "未知风险"}
ALLOWED_HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
ALLOWED_DATA_SENSITIVITY = {"高", "中高", "中", "低", "不适用", "未知"}

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
    "动作审计日志": ("动作审计日志",),
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

ALLOWED_CLI_FIT = {"是", "草案", "待验证", "待受控交付", "禁用占位", "否"}

WRITE_RISK_CLASSES = {
    "数据导出",
    "生产写入",
    "对外发送",
    "权限或配置变更",
}

# "未知风险" is not proof of a write, but it must be gated like one until the
# side effect is understood. Keeping it separate preserves the meaning of
# WRITE_RISK_CLASSES while making the safe default enforceable everywhere.
GUARDED_RISK_CLASSES = WRITE_RISK_CLASSES | {"未知风险"}

WRITE_FEATURE_STATUSES = {"未执行", "仅入口", "无法访问", "仅推断"}
WRITE_FLOW_REPLAY_STATUSES = {"不可重放", "未验证"}
UNKNOWN_RISK_FEATURE_STATUSES = {"未执行", "仅入口", "无法访问", "仅推断"}
UNKNOWN_RISK_CLI_FITS = {"禁用占位", "待受控交付", "否"}

PLACEHOLDER_VALUES = {"待填", "TODO", "TBD", "以后补"}

SAFETY_ZERO_METRICS = {
    "生产副作用": ("生产副作用",),
    "探索阶段写操作执行": ("探索阶段写操作执行", "写操作执行"),
    "凭据或载荷输出": ("cookie", "token", "凭据", "载荷", "请求头"),
    "权限、验证码、风控或反爬绕过": ("绕过",),
}

TRACEABILITY_FIELDS = (
    "feature_id",
    "能力/动作",
    "副作用",
    "审计日志",
    "撤销/软删除",
    "快照/备份",
    "恢复演练",
    "外部副作用可逆性",
    "权限回收",
    "可写性结论",
)

CLI_TRACEABILITY_FIELDS = (
    "capability_id",
    "副作用",
    "审计日志",
    "撤销/软删除",
    "快照/备份",
    "恢复演练",
    "外部副作用可逆性",
    "权限回收",
    "可写性结论",
)

ALLOWED_WRITEABILITY = {"只读安全", "可写但需快照", "可写但需审批", "不可写", "未知"}

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
    if header_index + 1 >= len(lines) or not re.fullmatch(
        r"\|(?:\s*:?-{3,}:?\s*\|)+\s*", lines[header_index + 1]
    ):
        errors.append(f"{label}表头后缺少合法的 Markdown 分隔行")
        return []
    separator_cells = [
        cell.strip()
        for cell in lines[header_index + 1].strip().strip("|").split("|")
    ]
    if len(separator_cells) != len(fields):
        errors.append(
            f"{label}表头分隔行列数为 {len(separator_cells)}，应为 {len(fields)}"
        )
    if not rows:
        errors.append(f"{label}没有记录")
        return []
    for line_number, cells in rows:
        if len(cells) != len(fields):
            errors.append(f"{label}第 {line_number} 行字段数为 {len(cells)}，应为 {len(fields)}")
            continue
        if any(not cell for cell in cells):
            errors.append(f"{label}第 {line_number} 行存在空字段；未知值应写未取得/待确认/不适用")
        if any(cell in PLACEHOLDER_VALUES for cell in cells):
            errors.append(
                f"{label}第 {line_number} 行仍有占位值；必须写未取得/待确认/不适用或实际证据"
            )
    return rows


def _validate_audit_log(
    errors: list[str], lines: list[str], text: str
) -> list[tuple[int, list[str]]]:
    """Require a per-action audit log, not just a summary claim of zero writes."""
    rows = _validate_table(errors, lines, "动作审计日志", AUDIT_FIELDS)
    if not rows:
        return rows

    level_counts = {"A": 0, "B": 0, "C": 0}
    for line_number, cells in rows:
        if len(cells) != len(AUDIT_FIELDS):
            continue
        level = cells[4].strip()
        execution = cells[5].strip()
        provenance = cells[7].strip()
        effect = cells[8].strip()
        if level not in ALLOWED_AUDIT_LEVELS:
            errors.append(f"动作审计日志第 {line_number} 行等级不合法：{level}")
            continue
        level_counts[level] += 1
        if effect not in ALLOWED_AUDIT_EFFECTS:
            errors.append(f"动作审计日志第 {line_number} 行副作用判断不合法：{effect}")
        if provenance not in {"页面自身触发", "未触发"}:
            errors.append(
                f"动作审计日志第 {line_number} 行请求来源不合法：{provenance}"
            )
        if level == "A":
            if execution not in {"已执行（只读）", "未执行", "阻断"}:
                errors.append(
                    f"动作审计日志第 {line_number} 行 A 类执行状态不合法：{execution}"
                )
            if execution == "已执行（只读）" and provenance != "页面自身触发":
                errors.append(
                    f"动作审计日志第 {line_number} 行 A 类已执行动作必须来自页面自身触发"
                )
            if execution == "已执行（只读）" and effect != "只读安全":
                errors.append(
                    f"动作审计日志第 {line_number} 行 A 类已执行动作的副作用判断必须是只读安全"
                )
        else:
            if execution not in {"未执行", "阻断"}:
                errors.append(
                    f"动作审计日志第 {line_number} 行 {level} 类动作执行状态只能是 未执行/阻断：{execution}"
                )
            if provenance != "未触发":
                errors.append(
                    f"动作审计日志第 {line_number} 行 {level} 类动作的请求来源必须是未触发"
                )
            if effect == "只读安全":
                errors.append(
                    f"动作审计日志第 {line_number} 行 {level} 类动作不能判为只读安全"
                )

    action_total = re.search(r"动作总数\s*[：:]\s*`?(\d+)", text)
    if action_total is None:
        errors.append("动作审计日志缺少汇总：动作总数")
    elif int(action_total.group(1)) != len(rows):
        errors.append(
            f"动作审计日志汇总 动作总数={action_total.group(1)} 与实际记录数 {len(rows)} 不一致"
        )
    for level, label in (("A", "A 类"), ("B", "B 类"), ("C", "C 类")):
        match = re.search(rf"{label}\s*[：:]\s*`?(\d+)", text)
        if match is None:
            errors.append(f"动作审计日志缺少汇总：{label}")
        elif int(match.group(1)) != level_counts[level]:
            errors.append(
                f"动作审计日志汇总 {label}={match.group(1)} 与实际记录数 {level_counts[level]} 不一致"
            )
    if not re.search(r"写操作执行\s*[：:]\s*`?0`?", text):
        errors.append("动作审计日志必须写明 写操作执行：0")
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


def _check_request_provenance(errors: list[str], text: str) -> None:
    """Require an explicit, machine-checkable read-only request provenance statement."""
    normalized = re.sub(r"\s+", "", text).replace("`", "")
    if not re.search(r"请求来源[：:]页面自身触发", normalized):
        errors.append("缺少请求来源声明：请求来源：页面自身触发")
    if not re.search(
        r"未复制[、,，]未重放[、,，]未导出HAR[、,，]未保存完整请求/响应",
        normalized,
    ):
        errors.append("缺少只读取证声明：未复制、未重放、未导出 HAR、未保存完整请求/响应")


def _check_runtime_controls(errors: list[str], text: str) -> None:
    """Require an explicit runtime guard + database boundary statement."""
    normalized = re.sub(r"\s+", "", text).replace("`", "")
    if "运行时写保护" not in normalized:
        errors.append("缺少运行时写保护声明（已启用/未启用 + 补偿控制）")
    elif "运行时写保护：已启用" not in normalized and not (
        "运行时写保护：未启用" in normalized and "补偿控制" in normalized
    ):
        errors.append("运行时写保护声明不完整：需写 已启用，或 未启用 + 补偿控制")
    elif "运行时写保护：已启用" in normalized and (
        "allowReadPostPaths" not in normalized or "allowSessionPostPaths" not in normalized
    ):
        errors.append(
            "运行时写保护声明缺少 allowReadPostPaths/allowSessionPostPaths 的精确路径状态"
        )
    if not re.search(r"数据库直连[：:](?:否|无)", normalized):
        errors.append("缺少数据库直连声明：应为 否/无")


def _check_global_placeholders(errors: list[str], text: str) -> None:
    for line_number, line in enumerate(text.splitlines(), start=1):
        for placeholder in PLACEHOLDER_VALUES:
            if placeholder in line:
                errors.append(f"第 {line_number} 行出现占位值：{placeholder}")


def _is_missing_evidence(value: str) -> bool:
    """Treat decorative values such as '未取得（待补）' as missing evidence."""
    normalized = value.strip()
    if normalized in {
        "未取得",
        "未知",
        "未演练",
        "未验证",
        "待确认",
        "待补",
        "待授权验证",
        "不适用",
        "无",
    }:
        return True
    if normalized.startswith("无"):
        return True
    return any(
        marker in normalized
        for marker in (
            "未取得",
            "未知",
            "未演练",
            "未验证",
            "未生成",
            "待确认",
            "待补",
            "待授权验证",
            "不适用",
        )
    )


def _check_cli_ready_gate(
    errors: list[str], line_number: int, cells: list[str]
) -> None:
    """For CLI fit 'yes', require evidence for every hard gate, not only status/high."""
    if cells[18] != "是":
        return
    if cells[3] != "已验证 API" or cells[4] != "高":
        errors.append(
            f"CLI-ready 契约表第 {line_number} 行标记可封装 CLI，但状态不是 已验证 API 或证据等级不是 高"
        )
    risk = cells[5]
    if risk in GUARDED_RISK_CLASSES:
        errors.append(
            f"CLI-ready 契约表第 {line_number} 行是写风险/未知风险能力，不能标记可封装 CLI"
        )
    method = cells[6].strip().upper()
    if method not in ALLOWED_HTTP_METHODS:
        errors.append(f"CLI-ready 契约表第 {line_number} 行 HTTP 方法未验证：{cells[6]}")
    for index, label in (
        (7, "脱敏路径"),
        (14, "响应字段轮廓"),
        (15, "错误码或异常表现"),
        (16, "权限要求"),
    ):
        if _is_missing_evidence(cells[index]):
            errors.append(
                f"CLI-ready 契约表第 {line_number} 行标记可封装 CLI，但{label}未取得：{cells[index]}"
            )
    if _is_missing_evidence(cells[8]) and cells[8].strip() not in {"无", "不适用"}:
        errors.append(
            f"CLI-ready 契约表第 {line_number} 行标记可封装 CLI，但参数名未取得：{cells[8]}"
        )
    for index, label in (
        (9, "参数类型"),
        (10, "是否必填"),
        (11, "分页字段"),
        (12, "排序字段"),
        (13, "筛选字段"),
    ):
        if _is_missing_evidence(cells[index]) and cells[index].strip() not in {"无", "不适用"}:
            errors.append(
                f"CLI-ready 契约表第 {line_number} 行标记可封装 CLI，但{label}未取得：{cells[index]}"
            )
    if _is_missing_evidence(cells[19]):
        errors.append(
            f"CLI-ready 契约表第 {line_number} 行标记可封装 CLI，但 CLI 建议命令名未取得"
        )
    if cells[17].strip() not in {"高", "中高", "中", "低"}:
        errors.append(
            f"CLI-ready 契约表第 {line_number} 行数据敏感级别未取得或不合法：{cells[17]}"
        )
    if not _is_missing_evidence(cells[20]):
        errors.append(
            f"CLI-ready 契约表第 {line_number} 行标记可封装 CLI，但仍有补充证据缺口：{cells[20]}"
        )


def _check_traceability_semantics(
    errors: list[str],
    label: str,
    rows: list[tuple[int, list[str]]],
    field_count: int,
    risk_by_id: dict[str, str],
    required_ids: set[str],
    snapshot_index: int,
    rehearsal_index: int,
    audit_index: int,
    external_index: int,
) -> None:
    seen: set[str] = set()
    row_ids: set[str] = set()
    for line_number, cells in rows:
        if len(cells) != field_count:
            continue
        identifier = cells[0]
        row_ids.add(identifier)
        if identifier in seen:
            errors.append(f"{label}第 {line_number} 行重复记录：{identifier}")
        seen.add(identifier)
        if identifier not in risk_by_id:
            errors.append(f"{label}第 {line_number} 行引用了不存在的对象：{identifier}")
            continue
        conclusion = cells[-1]
        if conclusion not in ALLOWED_WRITEABILITY:
            errors.append(f"{label}第 {line_number} 行可写性结论不合法：{conclusion}")
        risk = risk_by_id[identifier]
        if risk in GUARDED_RISK_CLASSES and conclusion == "只读安全":
            errors.append(
                f"{label}第 {line_number} 行是写风险/未知风险对象，不能得出 只读安全 结论"
            )
        if risk == "未知风险" and conclusion in {"可写但需快照", "可写但需审批"}:
            errors.append(
                f"{label}第 {line_number} 行是未知风险对象，补证前不能得出任何可写结论"
            )
        if conclusion in {"可写但需快照", "可写但需审批"} and _is_missing_evidence(
            cells[audit_index]
        ):
            errors.append(
                f"{label}第 {line_number} 行得出 {conclusion}，但没有审计日志证据"
            )
        # Any "snapshot required" conclusion must carry an actual snapshot and
        # a rehearsed recovery path, regardless of the risk category.  For
        # approval-only conclusions, retain the stricter requirement on data
        # and configuration changes.
        needs_snapshot_evidence = conclusion == "可写但需快照" or (
            conclusion == "可写但需审批"
            and risk in {"生产写入", "权限或配置变更"}
        )
        if needs_snapshot_evidence:
            if _is_missing_evidence(cells[snapshot_index]):
                errors.append(
                    f"{label}第 {line_number} 行是 {risk} 且得出 {conclusion}，但没有快照/备份证据"
                )
            if _is_missing_evidence(cells[rehearsal_index]):
                errors.append(
                    f"{label}第 {line_number} 行是 {risk} 且得出 {conclusion}，但没有恢复演练证据"
                )
        if conclusion in {"可写但需快照", "可写但需审批"} and risk in {
            "对外发送",
            "数据导出",
        }:
            external = cells[external_index]
            if _is_missing_evidence(external) or "不可逆" in external:
                errors.append(
                    f"{label}第 {line_number} 行是对外发送且得出 {conclusion}，但外部副作用不可逆或未取证"
                )
    for identifier in sorted(required_ids - row_ids):
        errors.append(f"{label}缺少写风险对象：{identifier}")


def detect_format(text: str) -> str | None:
    headings = _headings(text)
    if any(CLI_READY_MARKER in heading for heading in headings):
        return FORMAT_CLI_READY
    if any(FULL_REPORT_MARKER in heading for heading in headings):
        return FORMAT_FULL
    return None


def _safety_metrics(lines: list[str]) -> tuple[dict[str, str], set[str]]:
    header_index, rows = _find_table(lines, ("指标", "结果"))
    if header_index is None:
        return {}, set()
    metrics: dict[str, str] = {}
    duplicates: set[str] = set()
    for _, cells in rows:
        if len(cells) != 2:
            continue
        if cells[0] in metrics:
            duplicates.add(cells[0])
        metrics[cells[0]] = cells[1]
    return metrics, duplicates


def _validate_cli_ready_report(text: str) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    headings = _headings(text)
    for label, alternatives in CLI_READY_SECTIONS.items():
        if not any(any(term in heading for term in alternatives) for heading in headings):
            errors.append(f"缺少必需章节：{label}")

    lines = text.splitlines()
    audit_rows = _validate_audit_log(errors, lines, text)
    capability_rows = _validate_table(errors, lines, "能力与命令树分层", CAPABILITY_ROW_FIELDS)
    contract_rows = _validate_table(errors, lines, "CLI-ready 契约表", CLI_CONTRACT_FIELDS)
    request_rows = _validate_table(errors, lines, "请求契约索引", REQUEST_INDEX_FIELDS)
    traceability_header, traceability_rows = _find_table(lines, CLI_TRACEABILITY_FIELDS)
    if traceability_header is not None and traceability_rows:
        traceability_rows = _validate_table(
            errors, lines, "可追溯与可回滚评估", CLI_TRACEABILITY_FIELDS
        )

    capability_ids = {
        cells[0] for _, cells in capability_rows if len(cells) == len(CAPABILITY_ROW_FIELDS)
    }
    contract_ids = {
        cells[0] for _, cells in contract_rows if len(cells) == len(CLI_CONTRACT_FIELDS)
    }
    capability_risk = {
        cells[0]: cells[5]
        for _, cells in capability_rows
        if len(cells) == len(CAPABILITY_ROW_FIELDS)
    }
    contract_risk = {
        cells[0]: cells[5]
        for _, cells in contract_rows
        if len(cells) == len(CLI_CONTRACT_FIELDS)
    }
    capability_status = {
        cells[0]: cells[3]
        for _, cells in capability_rows
        if len(cells) == len(CAPABILITY_ROW_FIELDS)
    }
    contract_status = {
        cells[0]: cells[3]
        for _, cells in contract_rows
        if len(cells) == len(CLI_CONTRACT_FIELDS)
    }
    capability_cli_fit = {
        cells[0]: cells[6]
        for _, cells in capability_rows
        if len(cells) == len(CAPABILITY_ROW_FIELDS)
    }
    contract_cli_fit = {
        cells[0]: cells[18]
        for _, cells in contract_rows
        if len(cells) == len(CLI_CONTRACT_FIELDS)
    }
    effective_risk: dict[str, str] = {}
    for identifier in capability_ids | contract_ids:
        risks = [
            risk
            for risk in (capability_risk.get(identifier), contract_risk.get(identifier))
            if risk
        ]
        effective_risk[identifier] = next(
            (risk for risk in risks if risk in GUARDED_RISK_CLASSES),
            risks[0] if risks else "",
        )
    write_capability_ids = {
        identifier
        for identifier, risk in effective_risk.items()
        if risk in GUARDED_RISK_CLASSES
    }
    if write_capability_ids and not any(
        len(cells) == len(AUDIT_FIELDS) and cells[4] in {"B", "C"}
        for _, cells in audit_rows
    ):
        errors.append("存在写风险能力，但动作审计日志没有 B/C 类入口识别记录")

    for label, rows, field_count in (
        ("能力与命令树分层", capability_rows, len(CAPABILITY_ROW_FIELDS)),
        ("CLI-ready 契约表", contract_rows, len(CLI_CONTRACT_FIELDS)),
    ):
        seen_ids: set[str] = set()
        for line_number, cells in rows:
            if len(cells) != field_count:
                continue
            if cells[0] in seen_ids:
                errors.append(f"{label}第 {line_number} 行重复 capability_id：{cells[0]}")
            seen_ids.add(cells[0])

    for line_number, cells in capability_rows:
        if len(cells) != len(CAPABILITY_ROW_FIELDS):
            continue
        identifier = cells[0]
        if identifier in contract_risk and cells[5] != contract_risk[identifier]:
            errors.append(
                f"{identifier} 的风险分类在能力与命令树分层和 CLI-ready 契约表中不一致："
                f"{cells[5]} / {contract_risk[identifier]}"
            )
        if identifier in contract_status and cells[3] != contract_status[identifier]:
            errors.append(
                f"{identifier} 的状态在能力与命令树分层和 CLI-ready 契约表中不一致："
                f"{cells[3]} / {contract_status[identifier]}"
            )
        if identifier in contract_cli_fit and cells[6] != contract_cli_fit[identifier]:
            errors.append(
                f"{identifier} 的 CLI 适配值在能力与命令树分层和 CLI-ready 契约表中不一致："
                f"{cells[6]} / {contract_cli_fit[identifier]}"
            )

    for line_number, cells in capability_rows:
        if len(cells) != len(CAPABILITY_ROW_FIELDS):
            continue
        effective = effective_risk.get(cells[0], cells[5])
        if cells[3] not in ALLOWED_CAPABILITY_STATUSES:
            errors.append(f"能力与命令树分层第 {line_number} 行状态不合法：{cells[3]}")
        if cells[4] not in ALLOWED_EVIDENCE_LEVELS:
            errors.append(f"能力与命令树分层第 {line_number} 行证据等级不合法：{cells[4]}")
        if cells[5] not in ALLOWED_RISK_CLASSES:
            errors.append(f"能力与命令树分层第 {line_number} 行风险分类不合法：{cells[5]}")
        if cells[6] not in ALLOWED_CLI_FIT:
            errors.append(f"能力与命令树分层第 {line_number} 行 CLI适配 不合法：{cells[6]}")
        if cells[5] in WRITE_RISK_CLASSES and cells[6] not in {"禁用占位", "待受控交付"}:
            errors.append(
                f"能力与命令树分层第 {line_number} 行是写风险能力，CLI适配只能是 禁用占位/待受控交付：{cells[6]}"
            )
        if effective == "未知风险" and cells[6] not in UNKNOWN_RISK_CLI_FITS:
            errors.append(
                f"能力与命令树分层第 {line_number} 行是未知风险能力，CLI适配只能是 禁用占位/待受控交付/否：{cells[6]}"
            )
        if effective in WRITE_RISK_CLASSES:
            if cells[3] != "写操作未执行":
                errors.append(
                    f"能力与命令树分层第 {line_number} 行是写风险能力，状态只能是 写操作未执行：{cells[3]}"
                )
        elif effective == "未知风险" and cells[3] == "已验证 API":
            errors.append(
                f"能力与命令树分层第 {line_number} 行是未知风险能力，状态不能是 已验证 API：{cells[3]}"
            )

    for line_number, cells in contract_rows:
        if len(cells) != len(CLI_CONTRACT_FIELDS):
            continue
        effective = effective_risk.get(cells[0], cells[5])
        if cells[3] not in ALLOWED_CAPABILITY_STATUSES:
            errors.append(f"CLI-ready 契约表第 {line_number} 行状态不合法：{cells[3]}")
        if cells[4] not in ALLOWED_EVIDENCE_LEVELS:
            errors.append(f"CLI-ready 契约表第 {line_number} 行证据等级不合法：{cells[4]}")
        if cells[5] not in ALLOWED_RISK_CLASSES:
            errors.append(f"CLI-ready 契约表第 {line_number} 行风险分类不合法：{cells[5]}")
        if cells[18] not in ALLOWED_CLI_FIT:
            errors.append(f"CLI-ready 契约表第 {line_number} 行是否适合封装 CLI 不合法：{cells[18]}")
        if cells[5] in WRITE_RISK_CLASSES and cells[18] not in {"禁用占位", "待受控交付"}:
            errors.append(
                f"CLI-ready 契约表第 {line_number} 行是写风险能力，是否适合封装 CLI 只能是 禁用占位/待受控交付：{cells[18]}"
            )
        if effective == "未知风险" and cells[18] not in UNKNOWN_RISK_CLI_FITS:
            errors.append(
                f"CLI-ready 契约表第 {line_number} 行是未知风险能力，是否适合封装 CLI 只能是 禁用占位/待受控交付/否：{cells[18]}"
            )
        if effective in WRITE_RISK_CLASSES and cells[3] != "写操作未执行":
            errors.append(
                f"CLI-ready 契约表第 {line_number} 行是写风险能力，状态只能是 写操作未执行：{cells[3]}"
            )
        elif effective == "未知风险" and cells[3] == "已验证 API":
            errors.append(
                f"CLI-ready 契约表第 {line_number} 行是未知风险能力，状态不能是 已验证 API：{cells[3]}"
            )
        _check_cli_ready_gate(errors, line_number, cells)

    for line_number, cells in request_rows:
        if len(cells) != len(REQUEST_INDEX_FIELDS):
            continue
        if cells[6] not in ALLOWED_EVIDENCE_LEVELS:
            errors.append(f"请求契约索引第 {line_number} 行证据等级不合法：{cells[6]}")

    for identifier in sorted(capability_ids - contract_ids):
        errors.append(f"能力与命令树分层中的 {identifier} 未出现在 CLI-ready 契约表")
    for identifier in sorted(contract_ids - capability_ids):
        errors.append(f"CLI-ready 契约表中的 {identifier} 未出现在能力与命令树分层")

    if write_capability_ids and traceability_header is None:
        errors.append("存在写风险能力，但缺少可追溯与可回滚评估表")
    else:
        _check_traceability_semantics(
            errors,
            "可追溯与可回滚评估",
            traceability_rows,
            len(CLI_TRACEABILITY_FIELDS),
            effective_risk,
            write_capability_ids,
            snapshot_index=4,
            rehearsal_index=5,
            audit_index=2,
            external_index=6,
        )

    metrics, duplicate_metrics = _safety_metrics(lines)
    if not metrics:
        errors.append("未找到安全结果表（指标 | 结果）")
    for name in sorted(duplicate_metrics):
        errors.append(f"安全结果表存在重复指标：{name}")
    for label, keywords in SAFETY_ZERO_METRICS.items():
        hits = [
            (name, value)
            for name, value in metrics.items()
            if any(keyword in name.lower() for keyword in keywords)
        ]
        if not hits:
            errors.append(f"安全结果表缺少指标：{label}")
        else:
            bad = [
                (name, value)
                for name, value in hits
                if value.strip().strip("`") != "0"
            ]
            if bad:
                details = "；".join(f"{name}={value}" for name, value in bad)
                errors.append(f"安全结果表 {label} 不为 0：{details}")

    boundary_values = [
        (name, value)
        for name, value in metrics.items()
        if "授权改变执行边界" in name
    ]
    if not boundary_values:
        errors.append("安全结果表缺少指标：授权改变执行边界")
    else:
        bad_boundaries = [
            (name, value)
            for name, value in boundary_values
            if value.strip().strip("`") != "否"
        ]
        if bad_boundaries:
            details = "；".join(f"{name}={value}" for name, value in bad_boundaries)
            errors.append(f"安全结果表 授权改变执行边界 不为 否：{details}")

    if "可追溯" not in text or "可回滚" not in text:
        errors.append("未提供可追溯/可回滚评估")

    if "运行前权限边界确认" not in text:
        errors.append("未明确报告运行前权限边界确认")
    if "账号性质" not in text and "只读角色" not in text:
        errors.append("未记录账号性质或只读角色证明")

    if "待授权验证" in text:
        errors.append("出现已废弃的待授权验证状态；写能力只能用 待受控交付/禁用占位")

    if not re.search(r"当前是否允许直接封装\s*CLI\s*[：:]\s*`?(?:是|否|未评估)", text):
        errors.append("未明确回答当前是否允许直接封装 CLI：是/否/未评估")
    elif write_capability_ids:
        cli_answer = re.search(
            r"当前是否允许直接封装\s*CLI\s*[：:]\s*`?(是|否|未评估)", text
        )
        if cli_answer is not None and cli_answer.group(1) == "是":
            errors.append("存在写风险能力时，当前是否允许直接封装 CLI 必须为 否")

    if not re.search(r"写操作执行清单\s*[：:]\s*`?(?:无|0)", text):
        errors.append("未明确报告写操作执行清单：无/0")

    _check_request_provenance(errors, text)
    _check_runtime_controls(errors, text)
    _check_global_placeholders(errors, text)

    for label, pattern in FORBIDDEN_PATTERNS.items():
        if pattern.search(text):
            errors.append(f"发现疑似敏感信息：{label}")

    if "user_confirmed" not in text and "runtime_observed" not in text:
        errors.append("未显式标注证据来源类型（user_confirmed/runtime_observed）")
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
    audit_rows = _validate_audit_log(errors, lines, text)
    feature_rows = _validate_table(errors, lines, "功能地图", FEATURE_FIELDS)
    flow_rows = _validate_table(errors, lines, "Flow 清单", FLOW_FIELDS)
    step_rows = _validate_table(errors, lines, "Step 证据", STEP_FIELDS)
    evidence_rows = _validate_table(errors, lines, "Evidence 索引", EVIDENCE_FIELDS)
    traceability_header, traceability_rows = _find_table(lines, TRACEABILITY_FIELDS)
    if traceability_header is not None and traceability_rows:
        traceability_rows = _validate_table(
            errors, lines, "可追溯与可回滚评估", TRACEABILITY_FIELDS
        )

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
        if not re.search(r"FEAT-\d+", cells[2]):
            errors.append(f"Flow 清单第 {line_number} 行未关联 feature_id")
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
        if not re.search(r"FLOW-\d+", cells[1]):
            errors.append(f"Step 证据第 {line_number} 行未关联 flow_id")
        if cells[7] not in ALLOWED_STEP_EFFECTS:
            errors.append(f"Step 证据第 {line_number} 行副作用判断不合法：{cells[7]}")

    for line_number, cells in evidence_rows:
        if len(cells) != len(EVIDENCE_FIELDS):
            continue
        if not cells[0].startswith("EVID-"):
            errors.append(f"Evidence 索引第 {line_number} 行 evidence_id 格式不合法：{cells[0]}")
        if cells[1] not in ALLOWED_EVIDENCE_SOURCES:
            errors.append(f"Evidence 索引第 {line_number} 行来源类型不合法：{cells[1]}")
        if cells[7] not in ALLOWED_EVIDENCE_LEVELS:
            errors.append(f"Evidence 索引第 {line_number} 行置信度不合法：{cells[7]}")

    feature_ids = {cells[0] for _, cells in feature_rows if len(cells) == len(FEATURE_FIELDS)}
    flow_ids = {cells[0] for _, cells in flow_rows if len(cells) == len(FLOW_FIELDS)}
    step_ids = {cells[0] for _, cells in step_rows if len(cells) == len(STEP_FIELDS)}
    evidence_ids = {cells[0] for _, cells in evidence_rows if len(cells) == len(EVIDENCE_FIELDS)}
    feature_meta = {
        cells[0]: {"name": cells[3], "status": cells[5], "risk": cells[6]}
        for _, cells in feature_rows
        if len(cells) == len(FEATURE_FIELDS)
    }
    flow_meta = {
        cells[0]: {"features": re.findall(r"FEAT-\d+", cells[2])}
        for _, cells in flow_rows
        if len(cells) == len(FLOW_FIELDS)
    }
    evidence_meta = {
        cells[0]: cells[1]
        for _, cells in evidence_rows
        if len(cells) == len(EVIDENCE_FIELDS)
    }

    if any(meta["risk"] in GUARDED_RISK_CLASSES for meta in feature_meta.values()) and not any(
        len(cells) == len(AUDIT_FIELDS) and cells[4] in {"B", "C"}
        for _, cells in audit_rows
    ):
        errors.append("存在写风险能力，但动作审计日志没有 B/C 类入口识别记录")

    _check_traceability_semantics(
        errors,
        "可追溯与可回滚评估",
        traceability_rows,
        len(TRACEABILITY_FIELDS),
        {identifier: meta["risk"] for identifier, meta in feature_meta.items()},
        {
            identifier
            for identifier, meta in feature_meta.items()
            if meta["risk"] in GUARDED_RISK_CLASSES
        },
        snapshot_index=5,
        rehearsal_index=6,
        audit_index=3,
        external_index=7,
    )

    for line_number, cells in feature_rows:
        if len(cells) != len(FEATURE_FIELDS):
            continue
        if cells[6] in WRITE_RISK_CLASSES and cells[5] not in WRITE_FEATURE_STATUSES:
            errors.append(
                f"功能地图第 {line_number} 行是写风险能力，状态只能是 未执行/仅入口/无法访问/仅推断：{cells[5]}"
            )
        if cells[6] == "未知风险" and cells[5] not in UNKNOWN_RISK_FEATURE_STATUSES:
            errors.append(
                f"功能地图第 {line_number} 行是未知风险能力，状态只能是 未执行/仅入口/无法访问/仅推断：{cells[5]}"
            )
        if cells[5] in {"已验证", "页面已验证"}:
            referenced = re.findall(r"EVID-\d+", cells[9])
            if not referenced:
                errors.append(f"功能地图第 {line_number} 行状态为已验证，但没有关联 EVID")
            for evidence_id in referenced:
                if evidence_meta.get(evidence_id) not in {"runtime_observed", "user_confirmed"}:
                    errors.append(
                        f"功能地图第 {line_number} 行状态为已验证，但 {evidence_id} 不是 runtime_observed/user_confirmed"
                    )

    for line_number, cells in flow_rows:
        if len(cells) != len(FLOW_FIELDS):
            continue
        linked = flow_meta[cells[0]]["features"]
        if any(
            feature_meta.get(feature_id, {}).get("risk") in GUARDED_RISK_CLASSES
            for feature_id in linked
        ) and cells[6] not in WRITE_FLOW_REPLAY_STATUSES:
            errors.append(
                f"Flow 清单第 {line_number} 行涉及写风险能力，可重放状态只能是 不可重放/未验证：{cells[6]}"
            )

    write_flow_ids = {
        flow_id
        for flow_id, meta in flow_meta.items()
        if any(
            feature_meta.get(feature_id, {}).get("risk") in GUARDED_RISK_CLASSES
            for feature_id in meta["features"]
        )
    }
    for line_number, cells in step_rows:
        if len(cells) != len(STEP_FIELDS):
            continue
        if cells[1] in write_flow_ids and cells[7] not in {"只识别不执行", "未知风险"}:
            errors.append(
                f"Step 证据第 {line_number} 行属于写风险 Flow，副作用判断只能是 只识别不执行/未知风险：{cells[7]}"
            )

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

    for metric in ("生产副作用", "探索阶段写操作执行", "凭据泄露", "权限绕过"):
        matches = re.findall(rf"{metric}\s*[：:]\s*`?\s*(\d+)", text)
        if not matches:
            errors.append(f"未明确报告{metric}：0")
        elif any(value != "0" for value in matches):
            errors.append(f"{metric}不为 0：{', '.join(matches)}")
    if not re.search(r"授权(?:是否)?改变执行边界\s*[：:]\s*`?否`?", text):
        errors.append("未明确报告授权是否改变执行边界：否")
    if "可追溯" not in text or "可回滚" not in text:
        errors.append("未提供可追溯/可回滚评估")
    if not re.search(r"写操作执行清单\s*[：:]\s*`?(?:无|0)", text):
        errors.append("未明确报告写操作执行清单：无")

    _check_request_provenance(errors, text)
    _check_runtime_controls(errors, text)
    _check_global_placeholders(errors, text)
    if not re.search(r"当前是否允许直接封装\s*CLI\s*[：:]\s*(?:`)?(?:是|否|未评估)(?:`)?", text):
        errors.append("未明确回答当前是否允许直接封装 CLI：是/否/未评估")

    required_terms = ("一级导航模块", "顶部入口", "全局能力", "二级菜单能力")
    for term in required_terms:
        if term not in text:
            errors.append(f"未区分统计项：{term}")
    if "副作用授权范围" not in text and "副作用记录范围" not in text:
        errors.append("未明确报告副作用授权范围")
    if "待授权验证" in text:
        errors.append("出现已废弃的待授权验证状态；写能力只能用 待受控交付/禁用占位")
    if "运行前权限边界确认" not in text:
        errors.append("未明确报告运行前权限边界确认")

    for label, pattern in FORBIDDEN_PATTERNS.items():
        if pattern.search(text):
            errors.append(f"发现疑似敏感信息：{label}")

    if "user_confirmed" not in text and "runtime_observed" not in text:
        errors.append("未显式标注可核验的证据来源类型（user_confirmed/runtime_observed）")
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
