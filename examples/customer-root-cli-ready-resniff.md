# 客户运营系统根站点 CLI-ready 复嗅探报告

> 示例域名与账号范围已脱敏；路径仅保留结构示例，不对应可访问的真实环境。

## 1. 明确判断

- 目标网页：`https://example.internal/`
- 探测日期：2026-07-20
- 当前是否允许直接封装 CLI：否
- 判断依据：本轮已补齐项目工单、客户列表、咨询工单、通知列表、答案任务、跟单查询、助手和报表的部分真实只读接口契约，但所有候选能力仍至少缺少权限失败表现、字段级响应模式、完整错误语义或参数必填性证据。
- 可进入 CLI 命令树草案：项目工单列表、客户列表、咨询工单列表、通知列表、答案任务列表、跟单查询、智能助手答案视图、系统使用报表。
- 禁用占位：配置列、批量分配、店铺/工单导出、客户黑名单维护、答案任务创建和文件上传、售后信息发送，以及所有新增、编辑、保存、提交、发布、发送、删除、审批、授权和配置修改动作。
- 待验证/无法访问：全局搜索的页面—API映射、店铺列表数据接口、问答/转接/客伴等诊断查询接口、页面访问报表接口、工具使用报表响应、顶部“记咨询”。
- 关键缺失材料：角色与权限失败表现、响应数组元素字段、非空结果模式、参数必填性、业务错误码枚举、稳定性证据和敏感字段最小返回集。

## 2. 范围、口径与安全结果

### 2.1 本轮覆盖口径

| 层级 | 总数 | 本轮触达 | 取得可用页面证据 | 说明 |
|---|---:|---:|---:|---|
| 一级导航模块 | 8 | 8 | 8 | 项目、客户、店铺、工单、通知、助手、工具、报表均至少成功打开一次 |
| 顶部入口 | 1 | 0 | 0 | 根入口连续500，未复核“记咨询” |
| 全局能力 | 1 | 1 | 1 | 搜索框可见；仅观察到页面加载产生的无参数请求，页面动作映射未确认 |
| 二级菜单能力组 | 18 | 18 | 17 | 页面访问报表仅取得页面结构，未取得请求契约 |

一级导航模块固定为8个；顶部入口、全局能力和二级菜单不计入一级模块数量。

### 2.2 探测方式

- 使用现有合法登录态和隔离浏览器任务空间。
- 运行前权限边界确认：已完成；账号性质/只读角色证明：客户提供的只读运营账号，未使用管理员、共享或生产负责人账号。
- 自动允许动作仅包括打开、刷新、导航、展开、只读查询、合成无匹配条件和页面切换。
- 读取响应时只在内存中提取字段名与类型轮廓，没有保存完整响应或业务值。
- 页面实际依赖同组织服务子域时，只记录方法、服务来源、脱敏路径、非凭据字段名和结构；凭据类字段名称和值均省略。
- 证据来源类型：页面与网络结论为 `runtime_observed`；业务命名、权限边界和保留策略为 `user_confirmed` 或 `待确认`。
- 请求来源：页面自身触发；未复制、未重放、未导出 HAR、未保存完整请求/响应。
- 运行时写保护：已启用（BrowserContext 级默认拒绝；`allowReadPostPaths` 与 `allowSessionPostPaths` 均为空；本次阻断 0 次）。
- 数据库直连：否。

### 2.3 安全结果

| 指标 | 结果 |
|---|---|
| 生产副作用 | 0 |
| 探索阶段写操作执行 | 0 |
| 授权改变执行边界 | 否 |
| 可追溯/可回滚评估 | 已覆盖 |
| 导出或下载 | 0 |
| 新增、编辑、保存、提交或删除 | 0 |
| 对外发送 | 0 |
| 权限或配置变更 | 0 |
| Cookie、Token、请求头或完整载荷输出 | 0 |
| 账号、客户、订单、联系方式或行级数据写入报告 | 0 |
| 权限、验证码、风控或反爬绕过 | 0 |

### 2.4 动作审计日志

| 序号 | 时间 | URL/路径 | 动作 | 等级 | 执行状态 | 结果 | 请求来源 | 副作用判断 | 证据 ID |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-07-30 09:00 Asia/Shanghai | `/app` | 打开根入口 | A | 已执行（只读） | 成功 | 页面自身触发 | 只读安全 | EVID-001 |
| 2 | 2026-07-30 09:05 Asia/Shanghai | `/app` | 打开一级导航模块 | A | 已执行（只读） | 成功 | 页面自身触发 | 只读安全 | EVID-002 |
| 3 | 2026-07-30 09:20 Asia/Shanghai | `/app` | 打开二级菜单 | A | 已执行（只读） | 成功 | 页面自身触发 | 只读安全 | EVID-003 |
| 4 | 2026-07-30 09:30 Asia/Shanghai | `/app` | 合成无匹配条件查询 | A | 已执行（只读） | 成功 | 页面自身触发 | 只读安全 | EVID-004 |
| 5 | 2026-07-30 09:40 Asia/Shanghai | `/app` | 识别配置维护入口 | B | 未执行 | 入口可见 | 未触发 | 只识别不执行 | EVID-005 |
| 6 | 2026-07-30 09:45 Asia/Shanghai | `/app` | 识别批量分配入口 | B | 未执行 | 入口可见 | 未触发 | 只识别不执行 | EVID-005 |
| 7 | 2026-07-30 09:50 Asia/Shanghai | `/app` | 识别导出入口 | B | 未执行 | 入口可见 | 未触发 | 只识别不执行 | EVID-005 |
| 8 | 2026-07-30 09:55 Asia/Shanghai | `/app` | 识别售后发送入口 | B | 未执行 | 入口可见 | 未触发 | 只识别不执行 | EVID-005 |
| 9 | 2026-07-30 10:00 Asia/Shanghai | `/app` | 识别答案任务创建入口 | B | 未执行 | 入口可见 | 未触发 | 只识别不执行 | EVID-005 |
| 10 | 2026-07-30 10:05 Asia/Shanghai | `/app` | 根入口连续 500，停止 | C | 未执行 | 阻断 | 未触发 | 未知风险 | EVID-006 |

汇总：`动作总数：10`、`A 类：4`、`B 类：5`、`C 类：1`、`写操作执行：0`。

### 2.5 可追溯与可回滚评估

| capability_id | 副作用 | 审计日志 | 撤销/软删除 | 快照/备份 | 恢复演练 | 外部副作用可逆性 | 权限回收 | 可写性结论 |
|---|---|---|---|---|---|---|---|---|
| WRITE-CONFIG-01 | 权限或配置变更 | 未取得 | 未取得 | 未取得 | 未演练 | 不适用 | 未取得 | 未知 |
| WRITE-ASSIGN-01 | 生产写入 | 未取得 | 未取得 | 未取得 | 未演练 | 不适用 | 未取得 | 未知 |
| EXPORT-01 | 数据导出 | 未取得 | 未取得 | 未取得 | 未演练 | 不可逆（已下载文件无法收回） | 未取得 | 不可写 |
| ANSWER-CREATE-01 | 生产写入 | 未取得 | 未取得 | 未取得 | 未演练 | 不适用 | 未取得 | 未知 |
| AFTERSALES-SEND-01 | 对外发送 | 未取得 | 未取得 | 未取得 | 未演练 | 不可逆（消息已发出） | 未取得 | 不可写 |
| TOOLS-ROOT-01 | 未知风险 | 未取得 | 未取得 | 未取得 | 未演练 | 不适用 | 未取得 | 未知 |
| TOP-CONSULT-01 | 未知风险 | 未取得 | 未取得 | 未取得 | 未演练 | 不适用 | 未取得 | 未知 |

## 3. 证据等级与风险规则

### 3.1 证据等级

| 等级 | 定义 |
|---|---|
| `高` | 页面交互与对应网络请求均验证，业务语义可复核 |
| `中高` | 网络请求出现，但业务语义、参数或响应仍需确认 |
| `中` | 页面交互验证，但接口契约不足 |
| `低` | 仅菜单、入口、静态代码或路由存在 |
| `不可用` | 访问异常、无权限或被安全边界阻断 |

### 3.2 风险分类

| 分类 | 定义 |
|---|---|
| `只读安全` | 无业务状态变化，输出已最小化 |
| `敏感查询` | 输入或输出可能涉及客户、店铺、工单、组织、人员或业务内容 |
| `数据导出` | 下载或批量导出业务数据 |
| `生产写入` | 新增、编辑、保存、提交、删除或分配 |
| `对外发送` | 发送消息、通知或售后信息 |
| `权限或配置变更` | 授权、黑名单、版本、显示列或系统配置修改 |
| `未知风险` | 当前证据不足，无法确认副作用 |

## 4. 能力与命令树分层

| capability_id | 层级 | 能力 | 状态 | 证据等级 | 风险分类 | CLI适配 | CLI建议命令名 |
|---|---|---|---|---|---|---|---|
| GLOBAL-SEARCH-01 | 全局能力 | 客户/店铺/主账号搜索 | 页面已验证但 API 未确认 | 中高 | 敏感查询 | 草案 | `customer search` |
| IMPL-LIST-01 | 一级导航 | 项目工单列表 | 已验证 API | 高 | 敏感查询 | 草案 | `customer implementation list` |
| CUSTOMER-LIST-01 | 一级导航 | 客户列表与分层筛选 | 已验证 API | 高 | 敏感查询 | 草案 | `customer customer list` |
| SHOP-LIST-01 | 一级导航 | 店铺列表与分布筛选 | 页面已验证但 API 未确认 | 中 | 敏感查询 | 待验证 | `customer shop list` |
| TICKET-LIST-01 | 一级导航 | 客户咨询工单列表 | 已验证 API | 高 | 敏感查询 | 草案 | `customer ticket advisory list` |
| NOTICE-LIST-01 | 一级导航 | 通知列表 | 已验证 API | 高 | 敏感查询 | 草案 | `customer notice list` |
| ASSISTANT-ANSWER-VIEW-01 | 一级导航 | 智能助手答案分析视图 | 已验证 API | 高 | 敏感查询 | 草案 | `customer assistant answer-view` |
| TOOLS-ROOT-01 | 一级导航 | 工具集合 | 页面已验证但 API 未确认 | 中 | 未知风险 | 禁用占位 | `customer tool`（禁用） |
| REPORT-USAGE-01 | 一级导航 | 系统使用报表 | 已验证 API | 高 | 敏感查询 | 草案 | `customer report usage-summary` |
| ANSWER-LIST-01 | 二级菜单 | 店铺答案生成任务列表 | 已验证 API | 高 | 敏感查询 | 草案 | `customer answer-task list` |
| DIAG-FOLLOWUP-01 | 二级菜单 | 跟单诊断查询 | 已验证 API | 高 | 敏感查询 | 草案 | `customer diagnose follow-up` |
| DIAG-OTHERS-01 | 二级菜单 | 问答/转接/客伴诊断页面 | 页面已验证但 API 未确认 | 中 | 敏感查询 | 待验证 | `customer diagnose <type>` |
| REPORT-PAGE-01 | 二级菜单 | 页面访问报表 | 页面已验证但 API 未确认 | 中 | 敏感查询 | 待验证 | `customer report page-visits` |
| REPORT-TOOL-01 | 二级菜单 | 工具使用报表 | 页面已验证但 API 未确认 | 中高 | 敏感查询 | 待验证 | `customer report tool-usage` |
| TOP-CONSULT-01 | 顶部入口 | 记咨询 | 无法访问 | 不可用 | 未知风险 | 否 | `customer consult`（禁用） |
| WRITE-CONFIG-01 | 二级菜单 | 配置列与黑名单维护 | 写操作未执行 | 低 | 权限或配置变更 | 禁用占位 | `customer config`（禁用） |
| WRITE-ASSIGN-01 | 二级菜单 | 客户批量分配 | 写操作未执行 | 低 | 生产写入 | 禁用占位 | `customer customer assign`（禁用） |
| EXPORT-01 | 二级菜单 | 店铺与工单导出 | 写操作未执行 | 低 | 数据导出 | 禁用占位 | `customer export`（禁用） |
| ANSWER-CREATE-01 | 二级菜单 | 答案任务创建与文件上传 | 写操作未执行 | 中 | 生产写入 | 禁用占位 | `customer answer-task create`（禁用） |
| AFTERSALES-SEND-01 | 二级菜单 | 售后补发信息发送 | 写操作未执行 | 低 | 对外发送 | 禁用占位 | `customer aftersales send`（禁用） |

## 5. CLI-ready 契约表

> “草案”只允许进入命令树设计，不允许进入实现。未知信息统一保留为“未取得/待确认”。

| capability_id | 模块 | 能力名称 | 状态 | 证据等级 | 风险分类 | HTTP 方法 | 脱敏路径 | 参数名 | 参数类型 | 是否必填 | 分页字段 | 排序字段 | 筛选字段 | 响应字段轮廓 | 错误码或异常表现 | 权限要求 | 数据敏感级别 | 是否适合封装 CLI | CLI 建议命令名 | 封装前还需补充的证据 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| GLOBAL-SEARCH-01 | 全局 | 客户/店铺/主账号搜索 | 页面已验证但 API 未确认 | 中高 | 敏感查询 | GET | `/api/v1/search/customers` | 未取得 | 待确认 | 无参数请求可返回200；查询参数待确认 | 未取得 | 未取得 | 未取得 | `code:number; data.total:number; data.list:array` | 无参数请求200；空结果和业务错误未确认 | 当前登录身份；角色范围待确认 | 高 | 草案 | `customer search` | 关联页面搜索动作与请求；补查询参数、列表元素字段和权限失败表现 |
| IMPL-LIST-01 | 项目 | 项目工单列表 | 已验证 API | 高 | 敏感查询 | GET | `[业务服务]/api/projects/list` | `issue_type,current_page,page_size,stage`；凭据字段已省略 | `current_page/page_size:number`，其余待确认 | 均随默认请求出现；服务端必填性待确认 | `current_page,page_size` | 未取得 | `issue_type,stage`；页面另有区域、状态、日期、合同/客户筛选尚未映射 | `code:number; data.issue_list:array; data.total:number; msg:string` | 默认请求200；其他错误未取得 | 当前登录身份；项目模块权限待确认 | 高 | 草案 | `customer implementation list` | 补搜索/日期/状态参数映射、列表元素字段、必填性、空结果和权限失败 |
| CUSTOMER-LIST-01 | 客户 | 客户列表与分层筛选 | 已验证 API | 高 | 敏感查询 | GET | `[客户服务]/api/customers/list` | `search_key,current_page,page_size,label,label_key,time_tag,type,customer_stage,maintain_area,sort_key,sort_order,max_last_follow_time,tags,start_service_time,end_service_time,current_level,sign_level,has_competitor,maintain_supporters,delivery_manager,maintainer,pre_sales,team_obj,prediction_zh,industry_level1`；凭据字段已省略 | `current_page/page_size:number`；其他字段多为字符串或待确认 | 默认请求全部携带；服务端必填性未确认 | `current_page,page_size` | `sort_key,sort_order` | 其余参数均为筛选候选 | `code:number; data.customer_list:array; data.total:number; message:string; timestamp:number` | 默认请求200；合成搜索未触发新请求；错误未取得 | 当前登录身份；客户范围与角色权限待确认 | 高 | 草案 | `customer customer list` | 补参数枚举/类型、数组元素字段、空结果、错误码和权限失败 |
| SHOP-LIST-01 | 店铺 | 店铺列表与产品/平台分布 | 页面已验证但 API 未确认 | 中 | 敏感查询 | 未取得 | 列表路径未取得；已确认 `/api/v1/shop/menu` 与 `/api/v1/shop/category_search` 仅为菜单/条件接口 | 条件接口见 `search_key,path_end` | 字符串 | 待确认 | 未取得 | 未取得 | 店铺状态、产品、平台、到期条件和关键词尚未映射 | 菜单接口返回计数/分类数组；店铺列表响应未取得 | 页面首次成功，随后连续两次500 | 当前登录身份；店铺范围权限待确认 | 高 | 待验证 | `customer shop list` | 待页面稳定后捕获真实列表请求、参数、响应、错误和权限 |
| TICKET-LIST-01 | 工单 | 客户咨询工单列表 | 已验证 API | 高 | 敏感查询 | POST | `[工单服务]/api/tickets/search` | `page_size,page,sort_key,sort_order,search_args.issue_state,search_args.product_module,search_args.create_time` | `page_size/page:number; sort_key/sort_order:string; search_args:object` | 默认请求全部出现；服务端必填性待确认 | `page_size,page` | `sort_key,sort_order` | `issue_state,product_module,create_time`；客户筛选参数未捕获 | `code:number; data.advisory_list:array; data.current_page:number; data.page_total:number; data.total:number; msg:string` | 默认请求200；筛选输入未触发新请求；其他错误未取得 | 当前登录身份；工单范围权限待确认 | 高 | 草案 | `customer ticket advisory list` | 补客户筛选映射、数组元素字段、必填性、空结果和权限失败 |
| NOTICE-LIST-01 | 通知 | 通知列表 | 已验证 API | 高 | 敏感查询 | GET | `/api/v1/notifications/list` | `page_size,current_page,sort_order,sort_key` | 页码/页大小为数字；排序字段为字符串 | 无参数请求也返回200，均非HTTP层必填 | `page_size,current_page` | `sort_order,sort_key` | 页面可见渠道、产品线、类型、日期、关键词；接口字段未捕获 | `code:number; data.total:number; data.list:array` | 无参数请求200；数组元素、空结果和业务错误未取得 | 当前登录身份；通知范围权限待确认 | 中高 | 草案 | `customer notice list` | 补全部筛选参数、列表元素字段、错误码和权限失败 |
| ASSISTANT-ANSWER-VIEW-01 | 智能助手 | 智能助手答案分析视图 | 已验证 API | 高 | 敏感查询 | POST及GET | `/api/v1/assistant/.../answers/view`；相关配置和店铺列表路径已脱敏归组 | 主视图含 `show_related.limit,show_related.skip` 及关联条件对象；店铺列表含 `keyword` | 分页数字；关联条件对象；其他待确认 | 默认请求出现；服务端必填性待确认 | `show_related.limit,show_related.skip` | 未取得 | 店铺、分类、关联条件 | `code:number; data.question_with_conds:null或object; data.hist_answer_total:number; data.question_total:number; data.new_semantics_count:number; data.stat_key:string; message:string` | 本轮页面200；凭据相关请求已整体省略；其他错误未取得 | 当前登录身份且需要店铺上下文；角色范围待确认 | 高 | 草案 | `customer assistant answer-view` | 补脱敏店铺选择约束、非空响应元素、权限失败和错误语义；不得执行分析或导出 |
| TOOLS-ROOT-01 | 工具 | 工具集合入口 | 页面已验证但 API 未确认 | 中 | 未知风险 | 不适用 | 不适用 | 不适用 | 不适用 | 不适用 | 不适用 | 不适用 | 不适用 | 页面识别内容工具、店铺工具、诊断工具箱、售后工具 | 未取得 | 各工具独立权限待确认 | 未知 | 禁用占位 | `customer tool`（禁用） | 逐工具确认只读性；写入、上传、发送类保持禁用 |
| REPORT-USAGE-01 | 报表 | 系统使用汇总 | 已验证 API | 高 | 敏感查询 | GET | `/api/v1/reports/summary`; `/api/v1/reports/dimensions`; `/api/v1/reports/departments` | `summary.date`; `basic.start_date,basic.end_date`; 部门树无查询字段 | 日期字符串；部门树无参数 | 页面请求无参数时可部分返回200；带日期请求由页面触发 | 不适用 | 未取得 | 日期、组织维度 | `summary.data.basic/task/alert/advisory/date`; `basic.data.items:array`; `dept.data.depts:array` | summary首次超时后200；部门树曾超时/500，页面加载时又200 | 当前登录身份；组织范围权限待确认 | 中高 | 草案 | `customer report usage-summary` | 明确接口职责、日期格式、字段级响应、稳定性、错误和权限失败 |
| ANSWER-LIST-01 | 内容工具 | 店铺答案生成任务列表 | 已验证 API | 高 | 敏感查询 | GET | `/api/v1/tasks/list` | `source,keyword,skip,limit,user,shop_type` | `skip/limit:number`；其他为字符串或待确认 | 默认请求全部出现；服务端必填性待确认 | `skip,limit` | 未取得 | `source,keyword,user,shop_type` | `error_code:number; info:string; data.list:array; data.total:number` | 合成无匹配条件刷新返回200及空列表 | 当前登录身份；任务范围权限待确认 | 高 | 草案 | `customer answer-task list` | 补数组元素字段、参数枚举、权限失败及非零业务错误 |
| DIAG-FOLLOWUP-01 | 诊断工具箱 | 跟单诊断查询 | 已验证 API | 高 | 敏感查询 | GET | `/api/v1/diagnostics/follow-up/search` | `order_id,buyer_id,platform,plat_user_id,task_name,date` | HTTP传输为字符串；日期格式待确认 | 页面要求至少一个条件；各字段是否可独立使用待确认 | 不适用 | 不适用 | 订单号、买家标识、平台、店铺主账号、任务名、日期 | `code:number; message:string; data:object`；无匹配时为空对象 | 合成无匹配条件返回HTTP 200；业务错误未取得 | 当前登录身份；诊断权限待确认 | 高 | 草案 | `customer diagnose follow-up` | 补非空data字段、参数独立性、日期格式、权限失败和错误码；页面未确认买家昵称输入映射 |
| DIAG-OTHERS-01 | 诊断工具箱 | 问答/转接/客伴诊断 | 页面已验证但 API 未确认 | 中 | 敏感查询 | 未取得 | 未取得 | 页面可见日期、平台、店铺/子账号、买家、消息内容等输入 | 待确认 | 待确认 | 未取得 | 未取得 | 页面字段已识别，接口字段未取得 | 表格字段已识别，响应契约未取得 | 未取得 | 当前登录身份；各诊断权限待确认 | 高 | 待验证 | `customer diagnose <type>` | 在页面用合成条件逐项触发只读查询，捕获接口、参数、响应、空结果和权限 |
| REPORT-PAGE-01 | 报表 | 页面访问报表 | 页面已验证但 API 未确认 | 中 | 敏感查询 | 未取得 | 页面路由脱敏为 `/reports/:id` | 页面可见开始/结束日期 | 日期字符串待确认 | 待确认 | 未取得 | 未取得 | 日期 | 页面表头包括日期、UV、PV、标题、路径；API响应未取得 | 未取得 | 当前登录身份；报表权限待确认 | 中 | 待验证 | `customer report page-visits` | 捕获页面请求、日期参数、响应和权限失败；动态路由ID不得进入输出 |
| REPORT-TOOL-01 | 报表 | 工具使用报表 | 页面已验证但 API 未确认 | 中高 | 敏感查询 | GET | `/api/v1/reports/tools`; `/api/v1/reports/tool-usage` | `date[0],date[1],page,start_date,end_date,type` | 页码数字；日期/类型待确认 | 待确认 | `page` | 未取得 | 日期、类型、姓名页面输入 | 页面表格含工具、UV/PV、有效使用、组织及使用率；API响应未取得 | 页面触发请求，但两个接口连续两次超时 | 当前登录身份；组织/人员范围权限待确认 | 高 | 待验证 | `customer report tool-usage` | 服务稳定后补响应模式、分页、姓名筛选、错误和权限失败 |
| TOP-CONSULT-01 | 顶部入口 | 记咨询 | 无法访问 | 不可用 | 未知风险 | 未取得 | 未取得 | 未取得 | 未取得 | 未取得 | 不适用 | 不适用 | 未取得 | 未取得 | 根入口连续500，顶部入口未复核 | 未取得 | 未知 | 否 | `customer consult`（禁用） | 根入口恢复后仅确认入口与副作用；不得提交 |
| WRITE-CONFIG-01 | 客户/项目/通知 | 配置列与黑名单维护 | 写操作未执行 | 低 | 权限或配置变更 | 未取得 | 未取得 | 配置项待确认 | 待确认 | 待确认 | 不适用 | 不适用 | 未取得 | 未取得 | 未取得 | 配置权限待确认 | 高 | 禁用占位 | `customer config`（禁用） | 即使发现接口也不执行保存、新增或移除 |
| WRITE-ASSIGN-01 | 客户 | 客户批量分配 | 写操作未执行 | 低 | 生产写入 | 未取得 | 未取得 | 记录集合和分配目标 | 待确认 | 待确认 | 不适用 | 不适用 | 未取得 | 未取得 | 未取得 | 分配权限待确认 | 高 | 禁用占位 | `customer customer assign`（禁用） | 即使发现接口也不执行 |
| EXPORT-01 | 店铺/工单/助手 | 导出 | 写操作未执行 | 低 | 数据导出 | 未取得 | 未取得 | 当前筛选条件 | 待确认 | 待确认 | 待确认 | 待确认 | 待确认 | 下载结构未取得 | 未取得 | 导出权限待确认 | 高 | 禁用占位 | `customer export`（禁用） | 即使发现接口也不执行或下载 |
| ANSWER-CREATE-01 | 内容工具 | 答案任务创建与文件上传 | 写操作未执行 | 中 | 生产写入 | 未取得 | 未取得 | 页面可见平台、账号、数据来源、任务类型、开始语、结束语和文件 | 待确认 | 待确认 | 不适用 | 不适用 | 未取得 | 创建结果未取得 | 未取得 | 创建权限待确认 | 高 | 禁用占位 | `customer answer-task create`（禁用） | 不上传、不提交；移交独立测试环境的受控验证，不在本 skill 内执行 |
| AFTERSALES-SEND-01 | 售后工具 | 售后补发信息发送 | 写操作未执行 | 低 | 对外发送 | 未取得 | 未取得 | 未取得 | 未取得 | 未取得 | 不适用 | 不适用 | 未取得 | 发送结果未取得 | 未取得 | 发送权限待确认 | 高 | 禁用占位 | `customer aftersales send`（禁用） | 即使发现接口也不执行发送 |

## 6. 当前报告差距清单

| 差距 | 受影响能力 | 阻断级别 | 最小补证方式 |
|---|---|---|---|
| 角色和权限失败表现缺失 | 全部候选CLI能力 | 阻断 CLI-ready | 使用合法低权限测试身份只读访问；无身份则保持未取得，不绕过权限 |
| 列表元素字段未提取 | 实施、客户、工单、通知、任务 | 阻断 CLI-ready | 仅提取数组元素字段名/类型，不记录业务值 |
| 参数必填性与枚举不完整 | 全部候选CLI能力 | 阻断 CLI-ready | 在页面用合成条件逐字段触发只读查询，记录接受/拒绝状态 |
| 业务错误码与非法参数表现缺失 | 全部候选CLI能力 | 阻断 CLI-ready | 仅使用安全、无副作用的格式错误或空条件；不得制造生产异常 |
| 店铺列表接口未捕获 | 店铺模块 | 阻断能力实现 | 页面稳定后重新进入并关联列表请求 |
| 跟单诊断买家字段页面映射未确认 | 跟单诊断 | 阻断买家昵称命令设计 | 页面增加或确认买家字段后，用合成值验证 `buyer_id` 映射 |
| 工具使用接口连续超时 | 工具使用报表 | 阻断契约完成 | 服务恢复后只读重试一次完整页面加载 |
| 根入口连续500 | 顶部入口和根级导航 | 阻断顶部入口复核 | 服务恢复后重新打开根页，不重复高频刷新 |
| 敏感数据最小返回集未定义 | 全部敏感查询 | 阻断生产CLI | 由业务与安全负责人定义允许输出字段、默认脱敏和审计要求 |

## 7. 请求契约索引

| 方法 | 脱敏路径 | 触发动作 | 参数轮廓 | 响应轮廓 | 异常表现 | 证据等级 |
|---|---|---|---|---|---|---|
| GET | `[业务服务]/api/projects/list` | 打开正式项目工单 | `issue_type,current_page,page_size,stage` | `issue_list,total` | 默认200 | 高 |
| GET | `[客户服务]/api/customers/list` | 打开客户管理 | 分页、排序及多维筛选字段 | `customer_list,total` | 默认200 | 高 |
| POST | `[工单服务]/api/tickets/search` | 打开咨询工单 | 分页、排序、状态/模块/时间筛选 | `advisory_list,current_page,page_total,total` | 默认200 | 高 |
| GET | `/api/v1/notifications/list` | 打开通知列表（页面自身请求） | 分页、排序；其他筛选待确认 | `total,list` | 无参数200 | 高 |
| GET | `/api/v1/tasks/list` | 打开任务列表、合成空结果刷新 | `source,keyword,skip,limit,user,shop_type` | `list,total` | 无匹配200空列表 | 高 |
| GET | `/api/v1/diagnostics/follow-up/search` | 跟单诊断合成查询 | 订单、买家、平台、店铺账号、任务、日期 | `code,message,data` | 无匹配200空对象 | 高 |
| POST | `/api/v1/assistant/.../answers/view` | 智能助手页面默认加载 | 分页及关联条件对象 | 答案统计与列表上下文 | 默认200 | 高 |
| GET | `/api/v1/reports/summary` | 系统使用报表 | `date` | 汇总对象 | 首次超时后200 | 高 |
| GET | `/api/v1/reports/dimensions` | 系统使用报表 | `start_date,end_date` | `items` | 200 | 高 |
| GET | `/api/v1/reports/departments` | 系统使用与工具报表 | 无 | `depts` | 曾超时/500，页面加载时200 | 中高 |
| GET | `/api/v1/reports/tool-usage` | 工具使用报表 | 日期、页码、类型 | 未取得 | 连续两次超时 | 中高 |
| GET | `/api/v1/reports/tools` | 工具使用报表 | 无 | 未取得 | 连续两次超时 | 中高 |
| GET | `/api/v1/search/customers` | 页面加载触发；页面动作未关联 | 参数未取得 | `total,list` | 无参数200 | 中高 |

## 8. 风险与未执行动作

### 8.1 本轮识别但未执行

探索阶段写操作执行：`0`。写操作执行清单：`无`。以下均为只识别入口、未执行：

- 配置列、客户黑名单、供应商授权、客户端版本和其他配置修改。
- 客户批量分配、新增、编辑、保存、提交、删除和批量处理。
- 店铺、工单、助手及其他数据导出或下载。
- 答案生成文件上传和任务提交。
- 售后补发、通知发布及其他对外发送。
- 助手“分析”等可能产生显著资源消耗或未知副作用的动作。

### 8.2 即使发现接口也不能执行

- 所有导出、下载、上传和导入接口。
- 所有生产写入、分配、删除、审批、支付和退款接口。
- 所有通知、消息、邮件、短信和售后发送接口。
- 所有授权、黑名单、版本和配置保存接口。

## 9. 异常与盲区

1. 根 URL 连续两次返回500，停止重复刷新。
2. 店铺页首次成功进入并取得页面/菜单证据，随后连续两次返回500，真实列表接口未捕获。
3. 智能助手系统本轮已经恢复并成功进入；页面自动带入已有店铺上下文，报告已移除全部相关值和动态查询串。
4. 助手加载期间观察到一个凭据相关请求，路径、字段名和值均未纳入报告。
5. 工具使用报表两个查询接口连续两次超时，未取得响应轮廓。
6. 页面访问报表使用动态路由，报告统一脱敏为 `/reports/:id`，没有记录动态ID。
7. 问答、转接和客伴诊断仅打开页面，没有提交查询，因此API契约未确认。
8. 没有合法低权限测试身份，无法验证角色边界和无权限错误。
9. 本轮没有人工参考功能清单，无法计算完整功能覆盖率和误报率。

## 10. 验收结论

### 10.1 嗅探报告验收

- 是否通过：通过。
- 原因：8个一级模块均取得新鲜页面证据；能力状态、请求契约、证据等级、风险、异常、未执行动作和数据最小化结果均已记录。
- 安全硬门槛：生产副作用、敏感信息输出和权限绕过均为0。

### 10.2 CLI-ready 验收

- 是否通过：不通过。
- 不能通过的具体原因：没有任何能力同时满足完整字段模式、必填性、错误语义、权限失败、敏感最小返回集和稳定性要求。
- 当前是否允许直接封装 CLI：否

### 10.3 下一步最小补探清单

1. 服务稳定后补获店铺列表真实请求。
2. 补取实施、客户、工单、通知和任务列表的数组元素字段名/类型。
3. 在页面用合成条件逐项触发只读查询，验证筛选参数、必填性和空结果。
4. 确认跟单诊断的买家昵称页面输入与 `buyer_id` 参数映射。
5. 服务恢复后补取工具使用报表响应。
6. 使用合法低权限测试身份验证403/无权限表现；没有测试身份则保持未取得。
7. 由业务与安全负责人确认敏感查询的最小输出字段和审计规则。

### 10.4 需要继续只读验证的接口

- 店铺真实列表接口：路径未取得。
- `/api/v1/notifications/list`：渠道、产品线、类型、日期和关键词参数。
- `/api/v1/diagnostics/follow-up/search`：买家字段映射、日期格式和非空响应。
- `/api/v1/reports/tool-usage`、`/api/v1/reports/tools`：响应轮廓和稳定性。
- 问答、转接、客伴诊断接口：路径、参数和响应均待确认。
- 页面访问报表接口：未捕获。

### 10.5 即使发现也不能执行的接口/动作

- 导出、下载、上传、导入。
- 新增、编辑、保存、提交、删除、批量分配。
- 发布、通知、补发及其他对外发送。
- 授权、黑名单、版本、配置保存。
- 审批、支付、退款及其他生产副作用动作。

## 11. 结束边界

本报告只输出后续 CLI 设计所需的前置契约与差距，不直接生成 CLI，也不修改、测试、安装或发布任何从目标站点发现的 CLI、Skill 或 Plugin。
