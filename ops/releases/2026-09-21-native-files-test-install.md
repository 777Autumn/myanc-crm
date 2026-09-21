# Native 文件闭环：测试员工安装记录

记录日期：2026-09-21，北京时间。遵循 CRM `ops/RELEASE.md`；本记录仅含脱敏交付结论。Owner 已授权本轮冻结候选安装与既有服务维护。候选已安装，稳定健康检查通过；真实文件旅程验收 **incomplete**。

## 冻结来源与交付

| 来源 | 准确提交 | PR / 精确 merge-SHA CI |
| --- | --- | --- |
| CRM | `75b7126b9aea39db03544db0df10849cd8afeccb` | [PR #42](https://github.com/77AutumN/myanc-crm/pull/42) / [CI 通过](https://github.com/77AutumN/myanc-crm/actions/runs/35557115561) |
| Gateway | `52c2e9441eaa87234ad7174f45fd6ca61f3f9a32` | [PR #18](https://github.com/77AutumN/cc-connect-anc/pull/18) / [CI 通过](https://github.com/77AutumN/cc-connect-anc/actions/runs/35557090628) |
| Knowledge | `88a60ba60a634fe3d6b0f68f91de326b19a39b30` | 既有固定版本，本轮未替换 |

候选 SHA-256：`ca42d3b9e88100227406fc2b9383a3f3e3bb2090af3b29571d4fe9e1f596d298`。通过既有构建入口从准确来源导出、构建并逐文件核验；本地实现及 GitHub 源码交付已完成。两名独立 AI reviewer 分别完成 Spec、Standards 审查；AI 审查不代表 GitHub 真人批准。来源及合并映射沿用本轮 HANDOFF，不将本记录作为新的运行源码版本。

## 本轮安装及核验范围

仅为既有 `test-private` 启用 native 文件能力。按候选清单安装 6 个 runtime 文件：网关、受控文件客户端、workspace guard、测试工作区规则、team-files Skill 及 reference。另变更 3 个 controls：测试项目文件配置、sudo token 的 env_keep、既有服务的测试成果组 drop-in；没有新增服务或接收器。固定文档依赖安装到独立环境，新增文件工作目录与文件宿主存储；原 CRM/知识代码、业务规则、凭据及其他员工策略保持不变。

普通身份检查范围为 gateway UID 999 与测试模型 UID/GID 1004：宿主建目录及读取已发布成果；模型账号的普通进程读取不可改写的测试输入、制作和重开两版 DOCX/XLSX、由已安装客户端发布读取权限，保留旧版；所测保护配置、账本及选定的另一员工工作区不可读，受管规则和依赖不可写。该检查不执行模型或发送文件；管理 socket 的实际连接未测试，不能据目录不可进入推定已完成连接验收。

使用冻结候选的维护启动 helper，启动回执与应用健康分别判定。已验证唯一接收器、唯一归属明确的工具监听、六引擎及单一共享连接、普通 gateway 身份、零有效 capability、零自动重启；应用就绪后连续稳定超过 130 秒。9 个安装目标的哈希已与冻结变更逐一对账；六份既有业务库的 schema、行数和逻辑摘要在维护前后保持一致，保护性备份已验证。 原始配置、身份标识、现场状态和日志仅留受保护运维证据。

## 尚未完成与恢复边界

真实 Claude 旅程及其中的公司资料读取、原会话 XLSX/DOCX 投递、员工打开确认及回复修订均未执行，全部 **incomplete**；此前宿主只读资料预检、离线普通身份检查与 CI 不替代这些验收。不得表述为文件闭环已验收上线。

PAGE/TOC 等 DOCX 字段限制保留，真实模板兼容性未验证。

发生边界失败或不确定投递时停止并核对结果，不自动重发。恢复仅处理本次代码、规则和配置，关闭文件入口；保留原件、成果、快照及回执，不还原旧业务账本或重放发送。本轮维护脚本只作为一次性历史证据，不可复用。
