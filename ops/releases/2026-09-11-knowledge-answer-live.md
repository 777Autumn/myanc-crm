# 知识问答策略与 Skill：授权上线记录

实际记录日期：2026-09-11，北京时间。Owner 对本候选的备份、安装及一次维护窗口回复
“可以”后实施。遵循 [发布约定](../RELEASE.md)；前一阶段的未上线结论保留在
[定向回归记录](2026-09-11-knowledge-answer-completion.md)，不倒改历史。

当前结论：代码实现、源码 GitHub 交付和本次维护核验完成；**Owner/test 新版本无提示
首问、自然追问及来源打开仍未完成**。本记录不表示整个历史优化或资料整理计划完成。

## 冻结来源与候选

| 仓库 | 候选精确 main SHA | 成功 push CI |
| --- | --- | --- |
| CRM | `077629890e46e3c5b26a0015dd80de2cd1fcd723` | [34611499964](https://github.com/77AutumN/myanc-crm/actions/runs/34611499964) |
| 网关 | `c0db79e13c061f94c408fe152c8769154f07f22a` | [34597903568](https://github.com/77AutumN/cc-connect-anc/actions/runs/34597903568) |
| 知识 | `c8b9f771d69f797a00f4436de7a43a82b5557a34` | [34610996634](https://github.com/77AutumN/myanc-team-brain/actions/runs/34610996634) |

来源分别经 CRM [#24](https://github.com/77AutumN/myanc-crm/pull/24)、网关
[#10](https://github.com/77AutumN/cc-connect-anc/pull/10)、知识
[#14](https://github.com/77AutumN/myanc-team-brain/pull/14) 合并。独立 Spec、Standards
证据绑定候选 head/base；agent 审阅不称为 GitHub 人工批准。维护前重新通过三 SHA 发布门禁。

支持入口 `ops/build_vps_candidate.py` 从三源全新导出，按锁文件重建 Web；57 份包内
文件集合和哈希核验一致。工具链为 Python 3.13.2、Go 1.25.6、Node 24.13.0、pnpm 10.28.1，
目标 Linux/amd64、CGO=0。CRM 246 项/6 跳过、spikes 17 项、知识 62 项/2 跳过，适用项
通过；显式配对 CRMIPC1、CRMIPC2、KNOWLEDGEIPC2 及 core CUJ 实际通过，不以单仓绿灯替代。

产物 `knowledge-answer-candidate-20260911.tar.gz`，30,485,494 bytes，SHA256：
`4ebaad44ac2dcd7152336365aef9f28872e26af5de81b0ba2008d90daf7d7bde`。

## 实际变更与保全

只原子替换六个已固定模型工作区内的 `CLAUDE.md` 和
`.claude/skills/team-brain/SKILL.md`，共 12 份既有文件，保留 root:root/0444。
覆盖 Owner、partner、test 各自私聊及群聊，身份映射仍为三人六环境。

| 六环境相同文件 | 原 SHA256 | 安装后 SHA256 |
| --- | --- | --- |
| `CLAUDE.md` | `a0f7d809fc04ce2098ce00ce401dbdb93ba9f46be9c9ea9bf4098a2dfb91ba9f` | `627ae09417642bddf5221d2824daa27cd0932a0408179dbc18776622ee76cd70` |
| `team-brain/SKILL.md` | `36f3fa8b8cfde7ab84653f778ef3f07efc87e805f373d9dc1831f02958c482b3` | `5f72a9ac23dfaf12fe463aab62037414ec16ea48fab8b50e5907a7c40114228b` |

网关二进制与候选逐字节一致，SHA256
`8195dab0e729fe82ef19ad9245257904abf136c981e8fa71e83a39785783342a`，未替换。
现有知识运行目录仍为 `/opt/team-brain/releases/9e44acc73bc6916f3c785b460bb4d75e1f806d89`；
七份 Python 运行文件与新候选逐字节一致，目录名不冒充新的安装源码证明。
协议、受控客户端、宿主入口、配置、凭据及权限均未改；未重建或初始化知识库。

维护保留原 71 项控制文件基线，检查仅上述 12 份改变。12 份原文件、冻结 payload、六库
SQLite backup 和网关状态归档留在 VPS root-only 的
`/root/knowledge-answer-maintenance-20260911/`。未下载业务备份、聊天或身份配置。
六库包括真实/Sandbox CRM、知识状态及发布日志、提醒、告警；停止前、备份时、离线安装后
与初次健康核验的逻辑内容一致。没有 CRM/知识写入、提醒创建或自动会话重置。

## 维护核验

- 23:01:58 冻结维护计划及 12 份备份；23:02:13 完成停服态业务快照；23:02:14 完成安装；
  23:02:25 由既有 systemd 启动一次。没有重复启动、重装或恢复旧业务账本。
- 独立脚本审阅发现历史 `/new` 对账豁免还需绑定接收时间，修正并保留原 FAIL。
  最终脚本 SHA256 `03c92352de3f98429480568d0e0f05a331ae8e5cb798ab5fa3b8ddd4461fef2e`
  经双轴复审通过；13 项维护合成测试在 Windows 和 VPS Linux 均通过。
- 仅对账一笔有确切时间、同会话清理及后续已完成问答证据的旧宿主 `/new`；单独计数，
  未伪造模型完成记录。同 ID 不同时间的未完成重放仍会阻止切换。
- 初次健康检查未通过“唯一 HTTPS”条件：启动短暂有两条 HTTPS；保留该失败结果，
  未重启或改门槛。23:03:44 再核验为一个接收进程、一条 HTTPS、一个 18743 工具监听器，
  六个 engine、五个连接复用者，启动 ERROR=0、自动重启=0。
- 实际配置语义核对三人六环境映射一致；逐个模型用户权限检查均不能读取指定宿主配置、
  状态目录、提醒库或执行知识宿主。六环境 final-only、隐藏模型页脚配置保持生效。

这是现场宿主/文件权限核验，不冒充模型工具边界的全套真人回归。本次未再调用 Claude、
未在生产制造库损坏，也未重复执行 CRM 审批、提醒管理、识图、`/stop` 或工作区写入探针。
前序隔离模型三轮及其局限仍以原记录为准；未执行项目继续单列。

## 验收与回滚

Owner/test 各自以新会话自然提出不带标题的拜访准备问题，再自然追问并打开来源；只给
任务目标，不给提问答案模板。验收用 `/new` 建立本版本干净上下文，不把它当成旧触发
缺陷的修复。两账号结果尚待提供；王宇遵真人验收按此前决定豁免，不用他人结果替代。

发生需要回滚的故障时先暂停调度并保留当前提醒、告警及全部业务状态。经核对的本次
`answer_cutover.py rollback` 只恢复 12 份原控制文件及权限，先备份当前队列，留下服务
停止状态；需人工核对在途结果后再显式启动旧版本。不得覆盖账本、删除未发送提醒或
复用历史安装脚本。该一次性脚本只适用于本次冻结基线，后续版本必须重新对账。

证据集中在仓库外 `D:/MYANC/.knowledge-answer-evidence/maintenance-20260911/`：
`PLAN.md`、`release-gate.json`、两轴最终审阅、`linux-tests.txt`、`probe-reconciled.json`、
`receipt-redacted.json`、`health-1.txt`、`health-2.txt`、`inventory-after.json`。
本 PR 只补脱敏记录和遗留状态；其合并 SHA/CI 保存在 PR 评论及外部交接中，不再次部署。
