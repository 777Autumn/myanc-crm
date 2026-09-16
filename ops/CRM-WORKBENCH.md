# Native CRM mobile workbench

Deployment follows [the release contract](RELEASE.md). Runtime/model navigation
uses the existing [team-crm protocol](skills/team-crm/references/tools.md).
This is display configuration plus a read-only link selector, not a new CRM.

Current delivery: the Owner-approved [September 16 first phase](releases/2026-09-16-crm-mobile-workbench.md)
provides team follow-up and stage views. The second-phase candidate adds personal
views and the team overview; see its release record for actual per-environment
acceptance. An unverified personal mapping stays absent, so `mine` explicitly
falls back to the original Base rather than silently exposing a team view.

## Protected configuration

The optional `workbench_views` object lives in each environment's protected CRM
configuration. Leave it absent until that environment's native views are verified.
It binds to that same configuration's `base_token` and `customer_table_id`:

```json
{
  "workbench_views": {
    "base_token": "SAME_AS_CURRENT_BASE_TOKEN",
    "customer_table_id": "SAME_AS_CURRENT_CUSTOMER_TABLE",
    "owners": {
      "VERIFIED_CRM_USER_ID_OWNER": "vewOwnerExample",
      "VERIFIED_CRM_USER_ID_PARTNER": "vewPartnerExample",
      "VERIFIED_CRM_USER_ID_TEST": "vewTestExample"
    },
    "team": "vewTeamExample",
    "stages": "vewStagesExample",
    "overview": "blkOverviewExample"
  }
}
```

Replace placeholders only in the protected configuration, never in Git. Owner
keys are `allowed_actors[*].feishu_user_id`, not display names or transport IDs.
Copy view IDs from the administrator-verified native view URLs; never guess them.
The Base URL must be the current `/base/<base_token>` entry. The selector builds
only `table` and `view` parameters for views. For `overview`, `table` is the
administrator-verified native dashboard ID (`blk...`), with no `view` parameter.
Both forms drop stale record/filter/fragment values. Verify the dashboard belongs
to this Base before saving its ID; IDs alone do not establish membership.
Absent configuration or an absent target mapping falls back to the existing Base
entry with explicit nonpersonal wording. Malformed/cross-environment configuration
fails closed. No API call, ledger or new gateway route is needed to select a link.

## Native page setup

Inventory the existing views, fields and sharing first. Reuse matching views;
preserve the original total-table view. Use the existing administrator UI, without
granting view-management scopes to the Bot or changing sharing/advanced permissions.
When native owner selection cannot find a verified member, the authorized existing
administrator's user API may save the exact filter. Confirm that this profile's
app matches the CRM writer app before using app-scoped member IDs; never seed
production customers or change their owners to populate a picker.
Start in Sandbox and apply the verified setup to the production Base only afterward.

Create these five views on the customer table:

| View | Filter | Group |
|---|---|---|
| 777秋的跟进 | Exact verified owner 777秋 | 计划时间分组 |
| 王宇遵的跟进 | Exact verified owner 王宇遵 | 计划时间分组 |
| test 的跟进 | Exact verified owner test | 计划时间分组 |
| 全团队跟进 | None, including unassigned | 计划时间分组 |
| 全团队阶段看板 | None | Existing 阶段 field |

Daily views show 客户编号、客户名称、阶段、负责人、下一步行动、下次跟进时间.
Keep contacts, latest communication time and summary available in record details.
Sort within groups by 下次跟进时间 ascending, then 客户编号 ascending. Save view
configuration (temporary personal filter/group/sort changes are not publication).
Preserve all five existing stages, including won/deferred customers with plans.
Native grid-on-mobile cards are used; no separate website or paid widget is needed.

Add only the display formula `计划时间分组`, with the Base/date timezone verified as
Beijing. The end of the future-seven-day range is exclusive at today + 8:

```text
IF(ISBLANK([下次跟进时间]),"未设置时间",IFS([下次跟进时间]<TODAY(),"已过计划日期",[下次跟进时间]<TODAY()+1,"今日安排",[下次跟进时间]<TODAY()+8,"未来七天",TRUE(),"更晚安排"))
```

This formula does not modify source dates or create/complete plans or reminders.
Before switching links, verify the actual native formula around Beijing midnight,
blank dates, today 00:00/23:59, tomorrow, day +7 23:59 and day +8 00:00. Native
execution evidence is required; a Python equivalent is not a substitute. Use
fictional Sandbox data only, never production acceptance customers.

Verify each personal view against its exact owner, team inclusion of unassigned
customers, five stage groups and record counts without treating partial loading
as totals. Reload saved URLs to verify persistence, not just the current UI state.
Check that CRM schema/query/approval/plan-reminder regression tests still pass.

## Team today overview

Create one native dashboard in each Base, reusing a matching existing one. Three
statistics cards count all customer records, filtered only by `计划时间分组`:
`今日安排`, `已过计划日期`, `未设置时间`. Include unassigned and all stages. These
are full-source counts, not loaded-page counts; their sum excludes future plans.
Enable native record drill-down and provide links to the existing team and stage
views. Keep sharing restricted to existing collaborators; no subscriptions,
automations, public links, helper tables or business fields are needed.

Use the existing formula, not hard-coded dates. Observe actual Beijing midnight
refresh against complete record exports; the platform may briefly retain earlier
formula/chart results. Record observed delay instead of promising instant refresh.
Verify empty dates, yesterday, both ends of today, tomorrow, and won/deferred rows
with Sandbox fixtures. Check personal membership again after reassigning a fixture.
Remove only newly created fixture records after verification, retaining evidence.
The dashboard shows recorded plans, not completion or reminder delivery status.

## Cutover, acceptance and rollback

Record native object IDs and before/after settings in protected operational
evidence; commit only a sanitized release summary. Inspect installed runtime and
skill versions before selecting the candidate; preserve unrelated knowledge code.
After review/CI/merge and candidate validation, back up only the runtime, client,
skill and protected configuration being changed. Configure each environment's own
view map; never copy Sandbox IDs into production. Existing user and Bot scopes,
allowlists, credentials and business ledgers remain untouched.

Validate links for all three identities in private/group contexts; verify fallback
and rejection of model identity/URL overrides. Owner and test then check phone
opening, readable cards, record details and returning to Bot. Wang's existing
human-test exemption remains; no result is inferred for him. Report page setup,
GitHub delivery and phone acceptance separately, with unexecuted items explicit.

On a view/configuration failure, remove only `workbench_views` from the affected
protected configuration to restore the original total-table entrance. Disable or
remove only the newly introduced views/formula after recording their IDs and
dependencies. Restore code/skill together if necessary. Preserve all customers,
communications, plans and reminder/approval journals; never roll back a business
database to restore display settings.
