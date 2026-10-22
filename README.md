# web-capability-sniffer

只读嗅探已授权网页的页面能力、交互路径和网络请求契约，输出结构化、可追溯、已脱敏的能力报告及 CLI-ready 前置契约。

本项目只负责嗅探、证据分级、风险判断、可追溯/回滚预判和交接材料；**永不执行写操作**，**不做主动安全测试/扫描/越权探测**，不直接生成或发布 CLI，也不执行生产写操作。授权只扩大“可记录范围”，不扩大“可执行范围”。

## 当前能力

- 盘点页面、一级导航、顶部入口、全局能力和二级菜单。
- 关联只读页面操作与网络请求。
- 记录方法、脱敏路径、参数Schema、分页/排序/筛选字段和响应轮廓。
- 区分页面证据、请求证据、已验证契约和无法访问项。
- 判断能力可进入命令树草案、待验证、禁用占位或不适合CLI。
- 校验报告结构、ID 追踪、写风险可追溯覆盖、请求来源声明和常见敏感信息泄露风险。

## 安全边界

- 不执行新增、编辑、保存、提交、发布、发送、删除、导出、下载、审批、分配、支付或配置修改。
- 不执行 UI 最终确认、接口写调用、SQL、任何请求重放；写请求只记录入口。
- 不复制页面请求做手工探测，不导出 HAR，不保存完整请求/响应或含 PII 截图。
- 不做端口扫描、目录/路由/账号枚举、爆破、注入探测、IDOR/越权验证、参数篡改、fuzz。
- DDL/DML、清空/重置/初始化、批量导入、权限变更一律禁止。
- 运行时默认拒绝：第一次导航前安装请求 guard，非 `GET`/`HEAD`/`OPTIONS` 一律阻断；`POST` 只有 owner 确认的专用只读端点才放行，登录 POST 走独立 `allowSessionPostPaths`；两个白名单都只接受精确路径；危险路径词/危险 action 参数即使 `GET` 也阻断；percent-encoded 路径先解码；弹窗只 dismiss；审计路径脱敏。
- 不直连数据库、不执行 SQL；确需核对表结构时另立只读任务，使用只读副本/只读凭证/只读事务/超时。
- 不输出Cookie、Token、凭据值、账号、客户、订单、联系方式、完整请求/响应或行级业务数据。
- 不绕过权限、验证码、风控或反爬。
- 页面、菜单和路由存在不等于API已经验证。
- 不把发现的业务能力继续封装为CLI、Skill或Plugin。

详细规则见 [references/read-only-enforcement.md](references/read-only-enforcement.md)、[references/boundaries.md](references/boundaries.md) 和 [references/cli-readiness.md](references/cli-readiness.md)。

## 目录

```text
.
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── boundaries.md
│   ├── cli-readiness.md
│   ├── data-model.md
│   ├── distributed-exploration.md
│   ├── exploration-workflow.md
│   ├── publish-templates.md
│   ├── read-only-enforcement.md
│   ├── runtime-guard.md
│   ├── report-template.md
│   ├── report-template-cli-ready.md
│   └── review-rules.md
├── scripts/validate_report.py
├── scripts/readonly_guard.js
├── tests/test_validate_report.py
├── tests/readonly_guard.test.js
└── examples/
    ├── exploration-report-example.md
    └── customer-root-cli-ready-resniff.md
```

## 使用

安装到 Codex 常用 Skill 目录（`~/.agents/skills` 或 `~/.codex/skills`；Claude Code 常用 `~/.claude/skills`）：

```bash
git clone https://github.com/Jivan-sky/web-capability-sniffer.git
cp -R web-capability-sniffer ~/.agents/skills/web-capability-sniffer
```

在任务中调用：

```text
Use $web-capability-sniffer 对这个URL进行只读嗅探，并生成CLI-ready前置契约和差距报告。
```

## 校验

```bash
python3 scripts/validate_report.py examples/customer-root-cli-ready-resniff.md
python3 scripts/validate_report.py examples/exploration-report-example.md
python3 -m unittest discover -s tests -v
node --test tests/readonly_guard.test.js
```

## 当前成熟度

当前版本可以生成能力盘点、CLI命令树草案和可追溯/回滚预判，并提供浏览器层默认拒绝 guard。校验器会拒绝写风险或 `未知风险` 状态升级、两张 CLI 表风险/状态/CLI 适配不一致、Flow/Step 只读误标、缺失逐动作审计、缺失可追溯行、缺失请求来源声明和占位值；标记 `是` 时还会逐项核对方法、路径、参数类型/必填性、分页/排序/筛选、响应、错误、权限、敏感级别、命令名和剩余证据。单项能力只有在这些证据全部满足时，才允许标记为可直接交给其他Agent封装。写操作能力永远只能标“禁用占位/待受控交付”，`未知风险` 只能标“禁用占位/待受控交付/否”，均不在本 skill 内执行。
