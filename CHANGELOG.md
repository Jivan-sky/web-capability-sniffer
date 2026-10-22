# CHANGELOG

记录每个版本**要解决什么问题、怎么改、达成什么效果**。效果只写实际验证过的；未验证的一律标注。

---

## v1.2 — 深审后的 guard 收口(2026-10-22)

### 这一版修了什么

- **登录与会话不再被只读 POST 规则卡死**：新增 `allowSessionPostPaths`，只接受精确的专用登录/会话创建路径；优先复用客户提供的已认证 `storageState`。
- **写路径识别补齐**：`save/create/update/edit/add/submit/execute/run/trigger/sync/generate/export/download/assign/transfer/publish` 等按路径段阻断；支持 camelCase（如 `deleteAll`）和 percent-encoded（如 `%64elete`）路径归一化。
- **白名单不再可放大**：`allowReadPostPaths` 与 `allowSessionPostPaths` 只接受精确路径，通配符/前缀/query 模板在安装时直接报错，避免一个 `/api/*` 放大成全部 POST。
- **GraphQL body 拦截**：即使路径被加入只读白名单，body 出现 `mutation`/`subscription` 也阻断。
- **审计脱敏**：阻断事件只记录 `origin + pathname`，UUID、长数字、邮箱、凭据参数掩码；弹窗文案截断并脱敏。
- **回调 fail-closed**：`onBlocked` 抛错或弹窗 dismiss 抛错不再阻断后续 abort/dismiss，阻断事件仍可追溯。

### 验证状态

- 已验证：`node --check scripts/readonly_guard.js`；`node --test tests/readonly_guard.test.js`（23 tests OK）；Python 60 tests OK；两份样例校验 OK。
- 未验证：真实浏览器/真实客户页面的 guard 接入、生产级误触拦截；不能声称“已在客户生产环境验证”。

---

## v1.1 — 运行时默认拒绝与只读数据边界(2026-10-22)

### 这版修了什么

初版把“只读”写在规则里，但规则挡不住误触：按钮误点、页面自动保存、控制台重放、确认弹窗、直连数据库，都可能在实际探查中发生。深审后补三层运行时控制，并把“可写结论”的假控制收紧。

### 改动

- `scripts/readonly_guard.js`（新增）：无第三方依赖的浏览器 guard。默认拒绝非 `GET`/`HEAD`/`OPTIONS`；`POST` 只有显式 allowlist 才放行；危险路径词即使 `GET` 也阻断；弹窗只 dismiss；guard 异常 fail-closed；阻断事件只记录 `origin + pathname`，不记录 query/body/header。
- `tests/readonly_guard.test.js`（新增）：15 项 Node 测试，覆盖方法、allowlist、危险路径、危险 action 参数、方法覆盖头、query 误判、fail-closed、弹窗 dismiss、卸载。
- `references/runtime-guard.md`（新增）：网络层、弹窗层、数据层三层控制；工具不支持拦截时的补偿控制；guard 不能解决什么。
- `references/read-only-enforcement.md`：新增运行时写保护与数据库/SQL 边界；自检增加 guard、临时放开、只读事务项。
- `references/boundaries.md`、`references/exploration-workflow.md`、`SKILL.md`：Preflight 必须先装 guard；阻断事件按 `C / 阻断 / 未触发 / 未知风险` 进审计；报告必须声明运行时写保护与数据库直连。
- `references/report-template.md`、`references/report-template-cli-ready.md`、两份样例：补“运行时写保护”“数据库直连”声明。
- `.gitlab-ci.yml`、`.github/workflows/validate.yml`：Python 报告校验 + Node guard 测试。
- `README.md`、`agents/openai.yaml`：同步运行时只读边界与验证命令。

### 验证状态

- 已验证：`python -m unittest discover -s tests -v`（59 tests OK）；两份样例 `validate_report.py` OK；`node --test tests/readonly_guard.test.js`（15 tests OK）。
- 未验证：真实浏览器/真实客户页面的 guard 接入、只读数据库事务、生产级误触拦截；不能声称“已在客户生产环境验证”。

