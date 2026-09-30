# Native 文件闭环：测试员工安装记录

记录日期：2026-09-21，北京时间。遵循 CRM `ops/RELEASE.md`；本记录仅含脱敏交付结论。Owner 已授权本轮推进及 Computer Use 测试。候选已安装；既有测试员工在原 Bot 私聊完成了“上传虚构表格、结合公司资料、收到 Excel/Word、回复成果并收到修订版”的真实旅程。操作由 Codex 通过飞书桌面界面完成，不等同独立真人员工批准或多员工推广验收。

## 冻结来源与交付

| 来源 | 准确提交 | PR / 精确 merge-SHA CI |
| --- | --- | --- |
| CRM | `75b7126b9aea39db03544db0df10849cd8afeccb` | [PR #42](https://github.com/77AutumN/myanc-crm/pull/42) / [CI 通过](https://github.com/77AutumN/myanc-crm/actions/runs/35557115561) |
| Gateway | `8732fbb19a0f62c78a64a433910d0f6c6a8986f7` | [PR #20](https://github.com/77AutumN/cc-connect-anc/pull/20) / [CI 通过](https://github.com/77AutumN/cc-connect-anc/actions/runs/35590731595) |
| Knowledge | `88a60ba60a634fe3d6b0f68f91de326b19a39b30` | 既有固定版本，本轮未替换 |

最终候选 SHA-256：`07d6e255380ceaf898d5631fe5bb1ee12b5aa9ac5fa5eada42bfab6ef8029ea0`。通过既有构建入口从上述准确来源导出，实际执行配套 CUJ/Journey，84 个打包文件全部核验。工具链：Go 1.25.6、Node 24.13.0、pnpm 10.28.1、Python 3.13.2。两名独立 AI reviewer 分别完成源码 Spec、Standards 审查；AI 审查不代表 GitHub 真人批准。不将本记录作为新的运行源码版本。

最终客户端 SHA-256：`b0de1d0a3f587f956a8ae291ad055ddb66a84d197fbcb505d1ab8f4f433c2a48`。该候选较上一候选仅客户端不同；网关二进制保持 `3c6430b09c6d0fc878101a3c7e82281010f29b85b8a4e25ababfb4bc106cd2e3`。客户端按需启动，替换时服务 PID、invocation 与状态均未改变，无额外维护重启。

## 本轮安装及核验范围

初次安装候选 SHA-256 为 `ca42d3b9e88100227406fc2b9383a3f3e3bb2090af3b29571d4fe9e1f596d298`，对应 gateway [PR #18](https://github.com/77AutumN/cc-connect-anc/pull/18) merge `52c2e9441eaa87234ad7174f45fd6ca61f3f9a32` 及 [精确 CI](https://github.com/77AutumN/cc-connect-anc/actions/runs/35557090628)。仅为既有 `test-private` 启用 native 文件能力。按候选清单安装 6 个 runtime 文件：网关、受控文件客户端、workspace guard、测试工作区规则、team-files Skill 及 reference。另变更 3 个 controls：测试项目文件配置、sudo token 的 env_keep、既有服务的测试成果组 drop-in；没有新增服务或接收器。固定文档依赖安装到独立环境，新增文件工作目录与文件宿主存储；原 CRM/知识代码、业务规则、凭据及其他员工策略保持不变。

普通身份检查范围为 gateway UID 999 与测试模型 UID/GID 1004：宿主建目录及读取已发布成果；模型账号的普通进程读取不可改写的测试输入、制作和重开两版 DOCX/XLSX、由已安装客户端发布读取权限，保留旧版；所测保护配置、账本及选定的另一员工工作区不可读，受管规则和依赖不可写。该检查不执行模型或发送文件；管理 socket 的实际连接未测试，不能据目录不可进入推定已完成连接验收。

使用冻结候选的维护启动 helper，启动回执与应用健康分别判定。已验证唯一接收器、唯一归属明确的工具监听、六引擎及单一共享连接、普通 gateway 身份、零有效 capability、零自动重启；应用就绪后连续稳定超过 130 秒。9 个安装目标的哈希已与冻结变更逐一对账；六份既有业务库的 schema、行数和逻辑摘要在维护前后保持一致，保护性备份已验证。 原始配置、身份标识、现场状态和日志仅留受保护运维证据。

## 实际发现、修复与旅程证据

- 17:32：原始虚构 XLSX 被入站格式校验拒绝，尚未调用模型。普通 OOXML 的 BOM / Default ContentType 兼容性修复经 [PR #19](https://github.com/77AutumN/cc-connect-anc/pull/19) 合并为 `9aa7b6edab95ab411ff178f013b7f67605abae07`；[精确 merge CI](https://github.com/77AutumN/cc-connect-anc/actions/runs/35586164806) 通过后正常构建、安装。保留原失败证据，没有改造样例规避校验。
- 18:27—18:34：同一原件入站成功，真实 Claude 的文件工具仍返回 `file_transport_disabled`。这期间公司资料的 `knowledge_search`、`knowledge_read` 已有实际成功结果（正文 449 字符、7 块、revision 2），不能因此判定文件旅程完成。原生代理认证修复经 PR #20 合并、精确 CI 和正常组合构建后，仅替换受控客户端。
- 19:09—19:10：回复原任务后，实际 `work-context` 返回原件及哈希，Claude 用已安装的 openpyxl / python-docx 制作两份文件，通过既有 `file-deliver` / FileSender 返回原私聊。Excel 汇总为 175 份、18,300 元；两份文件均在飞书界面实际打开。首版表格长文字未换行，Word 实际两页，记录为首版排版缺口。
- 19:13—19:16：直接回复收到的 Excel，将虚构 TEST-003 改为 50 份、6,000 元，并要求修正上述排版、补足来源信息。新版汇总为 180 份、18,900 元；两份修订成果实际返回并打开，Excel 准备事项已换行，来源页包含实际材料标题、链接和版本，Word 预览页数为 `1/1`。模型端缺少分页渲染工具的限制如实说明；页数由实际飞书预览补证。

四次投递均为 `accepted`，各有非空、已绑定当前工作的消息回执；原件哈希未变，首版与修订版输出及四份宿主快照均逐一匹配回执哈希。回复成果后仍是同一工作、同一受控接收会话。本次完整工具轨迹已按测试账号和固定时间窗核对，没有 CRM 写入、知识发布或旁路发送；不将未判定的复合命令默认为无副作用。

| 宿主成果版本 | 文件 | SHA-256 |
| --- | --- | --- |
| 1 | 虚构需求分析.xlsx | `0bab40f0e9643d79632e9eeb2e2d0efcf45e85e13b71e9ae650c594fb632e16d` |
| 2 | 虚构需求说明.docx | `4e4470e436c049918fffa5dd6c52347941861406f34dbc622ce79d44afd4187e` |
| 3 | 虚构需求分析_v2.xlsx | `e0a011b2646ef2e1c5c2e2cfd7f30458176bcb2f6e68a3e5310718a945e4b01e` |
| 4 | 虚构需求说明_v2.docx | `ef0fd126e3c5f642f05e6cf227960eac0d718a4d19c39c827469f28ff9b421b3` |

原聊天、实际公司资料、成果内容、原始身份与运行记录仅留本地受保护证据，不进入 Git。发布的只是本次范围、哈希和脱敏结论。

## 尚未覆盖与恢复边界

本次覆盖既有测试员工的单次真实模型和飞书文件修订旅程。独立真人员工使用验收、多员工、手机端、跨工作并发以及真实业务模板仍 **incomplete**。PAGE/TOC 等 DOCX 字段限制保留，真实模板兼容性未验证；不静默删除字段。管理 socket 实际连接测试仍未执行，沿用前述范围说明。

发生边界失败或不确定投递时停止并核对结果，不自动重发。恢复仅处理本次代码、规则和配置，关闭文件入口；保留原件、成果、快照及回执，不还原旧业务账本或重放发送。本轮维护脚本只作为一次性历史证据，不可复用。
