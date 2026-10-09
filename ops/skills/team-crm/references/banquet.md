# 婚宴销售：同一客户可以有多场宴会

客户保存联系人和联系方式；婚宴业务保存一次宴会。已有确切婚宴编号时，直接
用 `banquet` 读取该场宴会。从客户查找其宴会时，先读取客户，重名时让用户
选客户编号。当前工具没有按客户关系筛选宴会的入口；说明“已找到客户，暂时无法
确认其关联宴会”，请用户提供婚宴编号，或在获准的飞书表中核对关联。
`banquets.keyword` 只匹配宴会名称、编号、场地和来源；客户姓名或编号的关键词
搜索为空不证明没有关联宴会。对某一场宴会的修改使用查询返回的 `record_id`。
旧客户阶段和婚宴销售阶段分别保存。

`banquet_id` 可用查询返回的 `record_id` 或确切业务编号（如 `YAN-0006`）；
宿主只在当前获准婚宴表内精确核对编号，审批仍绑定真实记录。同名宴会先查询选择。
普通 `unavailable` 只说明本次调用未完成，不能推断个人连接失效或要求重新授权；
仅按明确的连接错误提示重连，其他失败先核对输入和已有回执。

继续使用 `/usr/local/bin/crm-tool`，一个命令和一个 stdin JSON 对象。
个人读取由宿主选本人连接，群聊读取只在宿主批准的共享资源内。
工具不接受账号、profile、Base、表 ID 或批准参数。

| 命令 | 参数与用途 |
|---|---|
| `banquets` | `owner: me/all`（默认 me），可选 `keyword`、`stages`、`date_from/date_to`（YYYY-MM-DD）、`offset`。all 仍受当前身份权限约束，每页 20 条，继续按 `next_offset` 翻页 |
| `banquet` | `banquet_id`，读取最新业务和最近 10 条真实沟通，`history_has_more` 为 true 时不得称已读全部历史 |
| `stage-banquet-create` | 必填 `customer_query/name/owner_ref/stage`，可选下列业务字段，先用 `assignee` 核验负责人 |
| `stage-banquet-update` | `banquet_id` 和仅包含实际变更的 `changes` |
| `stage-banquet-followup` | `banquet_id/occurred_at/content`，可选 `channel`，记录实际发生的沟通；content 最多 2000 字符，超过时拆分并分别审批 |

可写业务字段：`name`、`source`、`owner_ref`、`banquet_date`、`date_note`、
`date_status`、`session`、`venue`、`estimated_tables`、`budget`、`visit_at`、
`visited_at`、`stage`、`next_action`、`next_followup_at`、`followup_status`。
客户关系由创建时选定的客户决定；需要换客户时先说明原因，请人工核对。

阶段仅有：新线索、跟进中、已约到店、已到店、已签单、已流失。
日期确认状态为待确认、预计、已确认。跟进状态为待跟进、已完成、已取消。
阶段不自动证明到店事实、跟进完成、签约材料齐全或同事已接手。

`banquet_date` 接受确切 YYYY-MM-DD；只有“明年五月”时保存在 `date_note`，
日期留空，不能补成五月一日。“周六来看场”等相对日期，先按当前日期和
Asia/Shanghai 核对所指日期；有歧义时追问。到店安排、实际到店和跟进时间
使用带时区的 ISO 时间。预计日期保留“预计”，不能写“已确认”。
桌数和预算为非负数字；先确认预算单位和含义，不能猜总价或每桌价。

用户说“考虑 20 桌”时保留考虑/预计措辞；真实沟通写进跟进记录。
改下一步或到店安排本身不算已经发生的沟通。需要两项写入时分别预览、批准、
回读；取消第二项不会撤销已完成的第一项。每次获批后读取 `result` 确认状态。
`verification_unknown` 必须人工核对，不重新提交来掩盖未知结果。

婚宴跟进字段与旧客户个人提醒互不代建。只有部署验收确认原生自动化已启用，
才可以承诺婚宴提醒会送达；不能为同一计划再创建一条个人提醒。
场地和日期目前是销售记录，不代表已锁档或已排除重复预订。

## 签单材料与指定接手

先用 `banquet` 读取已签单业务，并读取获准的客户及沟通事实。通过现有文件
流程生成 Word 交接清单，分开写客户需求、已确认事项、待补项；不得复制私人
对话或未经授权的资料。先完成文件交付，用 `work-context` 核对 accepted
状态和确切版本。文件送达不代表同事已确认接手。

| 命令 | 参数与用途 |
|---|---|
| `handoff` | `banquet_id`，读取当前交接；获准材料导入当前工作后，用 `work-context` 获取文件路径并实际阅读 |
| `stage-handoff-submit` | `banquet_id/recipient_ref/delivery_ids/missing`；先用 `assignee` 核验指定同事，材料为当前工作中已送达的 1–4 个版本，至少一个 Word。无缺项也明确填写“无” |
| `stage-handoff-accept` | `banquet_id/version`，指定同事在自己的会话预览并确认当前版本 |
| `stage-handoff-return` | `banquet_id/version/reason`，指定同事说明缺项，预览并退回 |

读取结果顶层 `is_recipient` 是宿主对当前用户的接手人核验。
为 true 时说明“指定你接手”，为 false 时说明当前记录中的指定人。
消息来源与 CRM 应用的用户 ID 可不同，以此核验结果判断，不按姓名或跨应用 ID 猜测。

提交、接手和退回均须宿主审批卡确认。材料、接手人或待补项改变后，重新提交
产生新版；旧版本及旧卡不能代确认新版。不要把直接改表的“已接手”当作已核验
确认。读取失败时不声称材料已送达，不使用作者的会话接手。每次 `result`
回读成功后提供飞书记录链接，以及宴会编号和交接版本供对方查找。

`open` 可选 `target`：`banquet-mine` 我的待跟进、`banquet-visits` 到店安排、
`banquet-stages` 销售阶段、`handoff-pending` 待交接、`handoff-mine` 我的待接手。
未配置返回拒绝；视图仅方便操作，不能据此断言具有行列隔离权限。
