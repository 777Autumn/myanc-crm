# Bot 优化：GitHub 交付与待上线范围

记录日期：2026-09-11，北京时间。此记录不是线上部署回执。
完成口径遵循 [发布约定](../RELEASE.md)。

## 版本映射

| 仓库 | 已合并 PR | 审阅 head | squash main SHA |
| --- | --- | --- | --- |
| CRM | [#17](https://github.com/77AutumN/myanc-crm/pull/17) | `2eeeac9e051ad83523cc76313c6c0afc793a7858` | `d3ece89561dad81adcaf8c01930292f4c2316114` |
| 网关 | [#8](https://github.com/77AutumN/cc-connect-anc/pull/8) | `c93102822b5cc1615729285f295887d9832ac43c` | `148a2fe51ec3553d52aed4277d5b14518739c7ea` |

两仓通过现有 head 匹配门禁合并；base 未变化，合并树与审阅 head 的树一致。
CRM 运行策略与受测 `d5c67095` 相同，最后一笔仅整理验收和遗留文档。
网关 `2a798f53` 至最终 head 仅追加三份知识查询测试文件，运行代码没有改变。
现有知识仓库 `0d75a2d4dcfc0fb45717e308ca6e6edfea8d240b` 未改动。

独立 Spec/Standards 源码审阅通过，证据绑定 head/base，保存在候选提交外：
[CRM 审阅摘要](https://github.com/77AutumN/myanc-crm/pull/17#issuecomment-5622962874)、
[网关审阅摘要](https://github.com/77AutumN/cc-connect-anc/pull/8#issuecomment-5622963323)。
这些审阅不是 GitHub 人工批准。

## 精确 CI 与验证

- CRM PR CI [34510132845](https://github.com/77AutumN/myanc-crm/actions/runs/34510132845) 和
  main push CI [34510311969](https://github.com/77AutumN/myanc-crm/actions/runs/34510311969)：`test` 通过。
- 网关 PR CI [34508306388](https://github.com/77AutumN/cc-connect-anc/actions/runs/34508306388)：五项必需 job 通过。
- 网关 main push CI [34510184228](https://github.com/77AutumN/cc-connect-anc/actions/runs/34510184228)：`lint`、`unit-test`、`smoke-test`、`regression-test`、`performance-test` 五项全部通过。

代表性原生模型流程已按用户调整后的实用口径完成；不同冻结版本的计数、
已修复的当前记录未重读问题、环境阻断、非阻断措辞及旧候选失败均保留在
[验收记录](../acceptance/2026-09-10-bot-ux-candidate.md)。实际平台消息及工具
结果均已复核，没有用程序绿灯代替语义检查，也没有把虚构数据测试冒充真人试用。
本地完整 Go/CUJ/构建、Linux Python 及显式跨仓组合测试已通过；本地未跑 race，
由 GitHub 的完整测试覆盖。门禁/候选包追加复核 16 项通过。

真实模型使用既有订阅隔离环境，没有新增账号、登录或付费 API。达到代表性
范围后已停止额外调用。一次隔离工具传输失败根因未知，后续未复现；不将
“后来成功”记成根因修复。知识夹具安装权限失配只在私有测试环境修复。

## 候选包与线上边界

GitHub 交付与线上完成分开：候选包仍须通过 `ops/build_vps_candidate.py`
从精确 main SHA 导出、重建 Web 和显式运行跨仓测试。构建完成后的最终输入
SHA、产物摘要及文件哈希清单在对应 PR 的提交外记录中绑定；不为文档自引用
反复改提交。本文不声称某个未构建文件就是候选包。

本次未部署、重启生产服务、修改业务数据或启用新告警库。所有隔离测试已
退出，临时令牌已清除、测试端口已释放；选定生产服务/配置/订阅设置核对未变。
没有读取并比较生产账本的全部内容，不能宣称全量业务快照相同。

下一阶段必须另行确认一次维护窗口，依 [告警运维说明](../OPS-ALERTS.md)
核对现场版本、备份和队列；初始化独立受保护告警库、检查六个模型用户真实
读取拒绝及六环境显示配置，保留 CRM/提醒账本、身份边界和知识库当前启用状态。
回滚先暂停相关调度，保留待发项与回执，再恢复审核代码配置，不覆盖业务账本。

Owner/test 在新候选上的无固定话术独立试用仍未执行。王宇遵真人验收仍为
豁免，不用 test 结果替代。轻微措辞、CI 运行时升级、登录修复后续证据核对、
原工作区整理继续由 [遗留清单](../FOLLOWUPS.md) 跟踪。
