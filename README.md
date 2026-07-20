# web-capability-sniffer

只读嗅探已授权网页的页面能力、交互路径和网络请求契约，输出结构化、可追溯、已脱敏的能力报告及 CLI-ready 前置契约。

本项目只负责嗅探、证据分级、风险判断和交接材料，不直接生成或发布 CLI，也不执行生产写操作。

## 当前能力

- 盘点页面、一级导航、顶部入口、全局能力和二级菜单。
- 关联只读页面操作与网络请求。
- 记录方法、脱敏路径、参数Schema、分页/排序/筛选字段和响应轮廓。
- 区分页面证据、请求证据、已验证契约和无法访问项。
- 判断能力可进入命令树草案、待验证、禁用占位或不适合CLI。
- 校验报告结构与常见敏感信息泄露风险。

## 安全边界

- 不执行新增、编辑、保存、提交、发布、发送、删除、导出、下载、审批、分配、支付或配置修改。
- 不输出Cookie、Token、凭据值、账号、客户、订单、联系方式、完整请求/响应或行级业务数据。
- 不绕过权限、验证码、风控或反爬。
- 页面、菜单和路由存在不等于API已经验证。
- 不把发现的业务能力继续封装为CLI、Skill或Plugin。

详细规则见 [references/boundaries.md](references/boundaries.md) 和 [references/cli-readiness.md](references/cli-readiness.md)。

## 目录

```text
.
├── SKILL.md
├── agents/openai.yaml
├── references/
│   ├── boundaries.md
│   ├── cli-readiness.md
│   └── report-template.md
├── scripts/validate_report.py
├── tests/test_validate_report.py
└── examples/customer-root-cli-ready-resniff.md
```

## 使用

安装到Codex默认Skill目录：

```bash
git clone https://gitlab.xiaoduoai.com/ai-pe/web-capability-sniffer.git
cp -R web-capability-sniffer ~/.codex/skills/web-capability-sniffer
```

在任务中调用：

```text
Use $web-capability-sniffer 对这个URL进行只读嗅探，并生成CLI-ready前置契约和差距报告。
```

## 校验

```bash
python3 scripts/validate_report.py examples/customer-root-cli-ready-resniff.md
python3 -m unittest discover -s tests -v
```

## 当前成熟度

当前版本可以生成能力盘点和CLI命令树草案。单项能力只有在参数、响应、错误、权限、敏感字段策略和稳定性证据全部满足时，才允许标记为可直接交给其他Agent封装。
