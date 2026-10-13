---
name: team-crm
description: 使用团队 CRM 查询客户和婚宴商机、婚期与到店安排、销售阶段、建档、记录沟通、修改跟进计划、签单交接与确认接手、查看审批结果时使用。也处理客户筛选、负责人核验、历史查询与工作台入口；纯个人提醒用 team-reminders，团队方法与资料查询用 team-brain。
---

# Team CRM

1. Read [the controlled CRM protocol](references/tools.md) completely before using
   CRM tools. It is the authority for arguments, current-turn reads, pagination,
   approval, shared plans and receipt interpretation.
2. Identify the user's current intent and the real object shown in this conversation.
   Follow the protocol's read/clarify/stage/result steps for that intent.
   For a banquet's current situation, number (such as `YAN-0006`), opportunity, date,
   venue, table count, budget, visit, material validity or handoff, read [the banquet protocol](references/banquet.md)
   before choosing fields or tools.
3. For a write proposal, preserve the confirmed draft and use the existing host
   approval workflow and its exact post-stage reply from the protocol.
4. On the next user turn, follow that turn's intent. Read the matching receipt
   when asked about the operation; do not restage merely to learn its result.
5. For a personal reminder request, load the installed `team-reminders` skill.
   For team methods or knowledge, load the existing `team-brain` skill. Continue
   in this same session; skill switching does not change identity or approval.

If this skill or its reference cannot be read, report the missing instructions
and request an operations check. Never improvise a replacement writer.
