# VPS 本地模拟 Wiki 发布

仅 DEMO-WIKI-001／澄禾婚宴团队使用此来源。发布遵守 [RELEASE.md](RELEASE.md)，
不更新 knowledge 源码或正式知识；不需要新依赖、凭据、API 或服务。

| 既有入口 | 普通运行用户 | 默认岗位模板 |
| --- | --- | --- |
| 维护私聊 | claude | skills/team-banquet/roles/maintenance.md |
| 销售测试群入口 | claude-owner-group | skills/team-banquet/roles/sales.md |
| 运营测试群入口 | claude-test-group | skills/team-banquet/roles/operations.md |

维护时先从受保护配置核实入口、用户、cwd、`file_work.runtime = native` 和静默状态；
不匹配则停止对应写入。不要从员工消息决定安装目录或岗位。

正常候选构建从合并提交导出整个 `skills/team-banquet/references/mock-wiki/`，
并生成包含源码提交、知识版本、完整文件列表及哈希的 `SOURCE.json`。
本轮逐文件安装范围：受影响的项目 CLAUDE.md、team-banquet 的 SKILL.md、
references/local-wiki.md、上述 Wiki 目录，以及该入口岗位模板（安装名为
references/workspace-role.md）。旧项目规则有差异时先核对差异，不能顺带覆盖。

三个入口安装同一 Wiki 快照；保留现有 root 所有权、只读保护和 native 沙箱，
草稿仍在该入口允许的工作目录。预先冻结候选、目标文件清单、旧文件及权限；
沿现有静默检查与逐文件原子替换流程安装，保留旧版本用于回退。
不删除旧演练、历史成果，不改用户级配置或重启服务作为默认步骤。

对每个目标目录运行候选中的只读校验：

```sh
python3 ops/mock_wiki.py /verified/workspace/.claude/skills/team-banquet/references/mock-wiki \
  --source-commit FULL_MERGE_SHA --version 1
```

只有三个目录全部通过、岗位映射和普通身份访问检查合格，才记录“已发布”。
部分写入或校验失败应记录准确状态并停止验收；按冻结备份恢复本次范围，不回滚
业务记录。验证时启动新工作以加载项目规则；旧成果修订明确新依据，保留旧版本。

知识更新仍经维护私聊整理草稿、选择性导入、小型内容 PR、两维 AI 审查、CI、
确切 merge CI 和正常候选构建。本入口没有无人值守发布能力。
