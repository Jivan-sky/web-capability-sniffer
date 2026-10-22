# 运行时写保护：把“只读”从口号变成默认拒绝

> Preflight 必读。文字规则只能约束愿意遵守规则的 Agent；**运行时 guard 负责在误触时兜底**。
> 一句话：**能拦就拦；拦不住就换成只读账号 + 人工观察，并在报告里写明补偿控制。**

## 一、为什么需要运行时 guard

探索阶段的事故通常不是“故意写”，而是：

- 以为按钮是查询，点下去触发了保存/初始化；
- 页面自动保存、自动提交、自动创建草稿；
- 在控制台/DevTools 里“复制请求试一下”；
- 误点确认弹窗的“确定”；
- 直接连数据库“看一眼”，执行了带副作用的 SQL。

这些行为在文字规则里都写了“禁止”，但误触发生时规则来不及生效。Guard 的作用是**在请求离开浏览器之前、在弹窗被接受之前**把它拦掉，并留下可审计的阻断记录。

## 二、必须启用的三层控制

| 层 | 控制 | 失败时 |
|---|---|---|
| **网络层** | 默认拒绝非 `GET`/`HEAD`/`OPTIONS` 请求；`POST` 只有显式 allowlist 的只读端点才放行；危险路径词、危险 action 参数（`?action=delete`）和方法覆盖头（`X-HTTP-Method-Override: DELETE`）即使 `GET` 也阻断 | 不能拦截 → 改用只读账号 + 人工观察，并记录补偿控制 |
| **弹窗层** | `confirm`/`alert`/`prompt` 一律 `dismiss`，绝不 `accept`；记录文案 | 不能监听 → 人工盯屏，禁止自动点击 |
| **数据层** | 不直连数据库；确需核对模型时，只用只读副本 + 只读凭证 + `SELECT` + 只读事务 + 语句超时 | 没有只读通道 → 不做数据层核对，记录盲区 |

三层缺一层，报告必须写明缺哪层、为什么、补偿控制是什么、残余风险谁接受。**不能写“已只读”而不写控制证据。**

## 三、浏览器 guard 的接入

参考实现：`scripts/readonly_guard.js`（无第三方依赖，接收 Playwright 风格的 page/context）。

```js
const { installReadOnlyGuard, installDialogGuard } = require('./scripts/readonly_guard');

// 默认拒绝一切非 GET/HEAD/OPTIONS；两个 POST 白名单都为空。
const guard = await installReadOnlyGuard(page, {
  onBlocked: (event) => {
    // 只记录脱敏 origin + pathname，不记录 query/body/header。
    console.error('BLOCKED', event);
  },
});

// 仅在 owner 书面确认“该 POST 是专用只读查询端点”后，才允许逐个加入。
// const guard = await installReadOnlyGuard(page, {
//   allowReadPostPaths: ['/api/query'],
// });

// 登录是独立的会话例外，不得混入只读查询白名单。
// 优先使用客户提供的已认证 storageState；无法复用时才使用专用登录路径。
// const guard = await installReadOnlyGuard(page, {
//   allowSessionPostPaths: ['/api/auth/login'],
// });
```

使用规则：

1. **在第一次导航之前安装**，不要先打开页面再补。
2. **启动浏览器上下文时设置 `serviceWorkers: 'block'`**，否则 Service Worker 发出的请求可能绕过 `page.route`/`context.route`。如果业务页面依赖 Service Worker 才能渲染，停在 Preflight 报告，不要为了“先看看”放开。
3. **优先装在 BrowserContext 上**，这样新标签页/弹窗也在拦截范围内；BrowserContext 不产生 page 级 dialog 事件，需对每个 page 调 `installDialogGuard(page, { onBlocked })`，并在 `context.on('page', ...)` 里给新页面补装。只装 page 时，弹窗由 `installReadOnlyGuard` 一并处理。
4. 两个 POST 白名单都默认空数组，且只接受**精确路径**；通配符、前缀和 query 模板会直接让安装失败。`allowReadPostPaths` 每加一个路径，必须有 owner 确认“该端点只读、无业务副作用”，并在报告里记录路径与确认人。
   - **企业现场优先向 owner 要“只读端点清单”**，而不是运行中自己猜。没有清单就只跑 `GET`/`HEAD`/`OPTIONS`。
   - 如果落地页本身依赖 `POST` 查询才能渲染：停在 Preflight 让 owner 确认，不许为了“先看看”临时放开或关掉 guard。
   - **GraphQL 单端点不能按路径放行写操作**：即使 body 是查询，同一 `/graphql` 也能发送 mutation；guard 会阻断含 `mutation`/`subscription` 的 body，但 owner 仍须证明端点服务端只读。
5. 危险路径按**路径段**和 camelCase 归一化后匹配；`save`/`create`/`update`/`edit`/`submit`/`execute`/`run`/`trigger`/`sync`/`generate`/`export`/`download`/`assign`/`publish` 等即使 `GET` 也阻断；percent-encoded 路径先解码再匹配，解码失败 fail-closed。危险 action 参数和方法覆盖头同样阻断。
6. Guard 自身异常必须 fail-closed（参考实现会 `abort`），不能让请求漏过去。
7. 每次阻断都进动作审计日志：等级 `C`、执行状态 `阻断`、请求来源 `未触发`、副作用判断 `未知风险`，并写阻断原因。事件只记录脱敏后的 `origin + pathname`；UUID、长数字、邮箱和凭据参数必须掩码，弹窗文案截断并脱敏。
8. 阻断后**停止该路径**并报告，不要反复重试或换方法绕过。

## 四、数据层规则

本 skill **不连接数据库、不执行 SQL**。如果探查确实需要核对表结构/字段/状态机：

1. 另立“只读数据核对”任务，不在网页嗅探任务里顺手做；
2. 使用客户提供的**只读副本/只读账号**，禁止生产写账号、管理员账号、共享账号；
3. 会话级强制只读：PostgreSQL `SET default_transaction_read_only = on`；MySQL `SET SESSION TRANSACTION READ ONLY`；其他库用等价只读事务；
4. 只允许 `SELECT`/`SHOW`/`DESCRIBE`/`EXPLAIN` 等只读语句；禁止 `INSERT`/`UPDATE`/`DELETE`/`MERGE`/DDL/`GRANT`/`REVOKE`；
5. 设置 `statement_timeout`/查询超时与行数上限，避免拖垮生产；
6. 结果只保留字段名、类型、枚举、状态机轮廓；不导出业务行数据；
7. 没有只读通道 → 不做，记录为盲区，不用“我就看一眼”替代授权。

## 五、工具不支持拦截时怎么办

有些浏览器工具不支持请求拦截。此时必须同时满足：

1. 使用**真实只读账号/客户正式只读角色**；管理员、共享、生产负责人账号不用于生产探查；
2. 关闭自动保存/自动提交/自动确认；人工盯屏，一次只做一个 A 类动作；
3. 禁止打开 DevTools 的“Copy as cURL”、禁止控制台、禁止请求重放；
4. 每个动作前后记录页面状态与审计日志；
5. 报告写明“运行时网络 guard：未启用；原因：工具不支持；补偿控制：只读账号 + 人工观察 + 禁止控制台”；缺这句 → 验收不通过。

## 六、Guard 不能解决什么

- 不能判断 `GET` 是否在服务端产生业务副作用；仍需按业务语义判断，并在发现自动副作用时立即停止。
- 不能拦截 Service Worker（除非启动时 `serviceWorkers: 'block'`）、WebSocket/SSE 帧内容、浏览器扩展或页面外的原生客户端；探查中禁止通过 WebSocket 发送业务指令，发现即停。
- 不能替代只读账号：账号权限仍是最后一道边界。
- 不能替代审计日志：guard 只记录“被阻断”，不记录“为什么这个入口存在”。
- 不能替代 FDE 的写入门卡：写操作仍必须移交受控流程。

## 七、自检

- 第一次导航前装好 guard 了吗？装在 context 还是 page？
- `allowReadPostPaths` / `allowSessionPostPaths` 是否为空？每个例外是否有 owner 确认与报告记录？是否误用了通配符或前缀？
- 阻断事件是否按 `C / 阻断 / 未触发 / 未知风险` 进了逐动作审计？
- 审计事件是否只含脱敏路径，没有 query/body/header/邮箱/长 ID？
- 弹窗是否只 dismiss、从未 accept？
- 是否直连了数据库？是否用了只读副本、只读凭证、只读事务和超时？
- 工具不支持拦截时，是否写了补偿控制与残余风险？
- Guard 自身报错时，是否 fail-closed 并停止，而不是继续？

