---
name: team-reminders
description: 用户要求创建、查看、修改或取消自己的提醒时使用，包括“刚才那条”“第二条”“改明天下午”等连续对话和群内清单私发。读取提醒后若发现它关联 CRM，时间/行动内容修改转入 team-crm 的审批流程；不用提醒只关闭通知，不删除客户计划。
---

# Team reminders

1. Read [the controlled reminder protocol](references/tools.md) completely before
   using reminder tools. It owns arguments, time rules, pagination, fresh versions,
   private destinations and truthful result wording.
2. Resolve the requested reminder from this conversation, then follow the
   protocol's current-turn read and mutation steps. Preserve its real ID across
   reordering and use the version just read.
3. If the selected reminder is CRM-linked and the user changes time/content,
   load the installed `team-crm` skill and its reference before the existing
   linked-reminder update. Follow that protocol's approval/result rules; do not
   independently stage a second customer update.
4. Render the saved result or genuine uncertainty according to the protocol.
   Follow pagination and private-list boundaries for list requests.
5. Remain in the same session. Personal reminders do not require team knowledge;
   a separate knowledge request uses the existing `team-brain` skill.

If this skill or its reference cannot be read, report the missing instructions
and request an operations check. Do not substitute a generic scheduler.
