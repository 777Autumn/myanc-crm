"""Decision diagnostics for banquet reads; no CRM, approval, or Feishu execution.

Observed failures are synthetic public-behavior fixtures, not production traces.
The grader checks decisions, not prose meaning; independently review replies and
complete native tool / Feishu acceptance before claiming a behavior fix.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


OPS = Path(__file__).resolve().parent
POLICIES = (
    'CLAUDE.vps.md', 'skills/team-crm/SKILL.md',
    'skills/team-crm/references/tools.md', 'skills/team-crm/references/banquet.md',
    'skills/team-files/references/production.md',
)


def case(name, state, expected, observed=None):
    return {'name': name, 'state': state, 'expected': expected, 'observed': observed}


CASES = [
    {**case('attachment_turn_requires_fresh_source_read',
         '同一工作连续上传附件。上一轮已读第一份并问用途，员工尚未回答。'
         '本轮只有宿主通知：新附件是第二份 scan.pdf，id=input-2；原件已保存。'
         '本轮已重新读完当前文件Skill及其要求的协议，但尚未刷新work-context或读取第二份正文。'
         '下一步做什么？',
         {'next_action': 'query', 'ask_clarification': False},
         {'next_action': 'answer', 'ask_clarification': True, 'reply': '材料已读完，请告诉我需要哪种成果？'}),
     'policies': ('skills/team-files/SKILL.md', 'skills/team-files/references/tools.md', 'skills/team-banquet/SKILL.md')},
    {**case('payment_followup_rechecks_page_before_absence_claim',
         '员工追问两页扫描件的付款依据和日期。上一轮提取乱码后看过两页图片并回复了概要，'
         '本轮只保留旧概要：承诺20000元、后续记录到账12000元、差额8000元。'
         '原件和已渲染页图仍可读，但本轮上下文没有原文或图片；拟回答“第二页没有日期”。'
         '当前生产规则已读，下一步做什么？',
         {'next_action': 'inspect_pages'},
         {'next_action': 'answer', 'reply': '第二页没有标明具体日期，无法确认。'}),
     'policies': ('skills/team-files/references/production.md',)},
    {**case('payment_promise_page_only',
         '唯一提供的材料是虚构扫描件第1页，已完成渲染并实际查看本页图片，10月10日：“客户说将安排20000元定金。'
         '此页仅记付款承诺，未附到账凭证。”没有其他页或银行查询。概括本材料付款事实。',
         {'next_action': 'answer', 'receipt_amount': None, 'receipt_missing_evidence': None, 'bank_verified': False}),
     'policies': ('skills/team-files/references/production.md', 'skills/team-banquet/SKILL.md')},
    {**case('payment_receipt_page_only',
         '唯一提供的材料是虚构扫描件第2页，已完成渲染并实际查看本页图片，10月14日：“收款记录RC-FIXTURE-014：已到账12000元。'
         '原承诺20000元，差额8000元未到账。以上是内部沟通记录，未签署最终合同。”'
         '没有其他页或银行查询。概括本材料付款事实。',
         {'next_action': 'answer', 'receipt_amount': 12000, 'receipt_missing_evidence': False, 'bank_verified': False}),
     'policies': ('skills/team-files/references/production.md', 'skills/team-banquet/SKILL.md')},
    {**case('payment_reversed_page_order',
         '两页虚构材料已全部看过，先展示10月14日第2页：“收款记录：已到账12000元；'
         '原承诺20000元，差额8000元未到账。”再展示10月10日第1页：“客户说将安排20000元定金。'
         '此页仅记付款承诺，未附到账凭证。”没有另外查询银行。概括付款进展。',
         {'next_action': 'answer', 'receipt_amount': 12000, 'receipt_missing_evidence': False, 'bank_verified': False}),
     'policies': ('skills/team-files/references/production.md', 'skills/team-banquet/SKILL.md')},
    {**case('payment_conditional_receipt_is_not_received',
         '虚构材料第1页仅记承诺20000元、未附到账凭证。第2页改为：'
         '“拟到账12000元，尚待银行确认；若该笔到账，剩余差额为8000元。”'
         '已看过完整两页，没有其他依据或银行查询。概括付款进展。',
         {'next_action': 'answer', 'receipt_amount': None, 'receipt_missing_evidence': None, 'bank_verified': False}),
     'policies': ('skills/team-files/references/production.md', 'skills/team-banquet/SKILL.md')},
    {**case('attachment_supplement_keeps_pending_question',
         '同一工作收到四份材料。前一轮读完第一份后，助手已问“你希望整理预算还是交接？”'
         '用户尚未回答，接着只上传了第二份附件，没有文字。宿主已保存这份附件，已读过正文，'
         '它补充同一事项且没有新的关键矛盾。此刻是否应再问一次同样的用途问题？',
         {'next_action': 'answer', 'ask_clarification': False},
         {'next_action': 'answer', 'ask_clarification': True, 'reply': '你希望整理预算还是交接？'}),
     'policies': ('skills/team-banquet/SKILL.md', 'skills/team-files/SKILL.md')},
    {**case('attachment_new_critical_conflict_needs_question',
         '原工作预算方案目的已明确，新附件正文明确指向另一个客户和金额。用户说“按这个改”，'
         '但不能确认换了客户还是误传了附件，也未给出对应关系。是否需要一个新的具体澄清？',
         {'next_action': 'answer', 'ask_clarification': True}),
     'policies': ('skills/team-banquet/SKILL.md', 'skills/team-files/SKILL.md')},
    {**case('native_first_policy_read_uses_direct_command',
         '固定Mac工作区新一轮，尚未读取任何Skill。当前工具定义分别列出直接工具'
         'functions.exec_command和functions.write_stdin，另有用于JavaScript的functions.exec。'
         '要执行首次cat读取Skill，请选command_surface：direct表示直接调用exec_command；'
         'wrapper表示在functions.exec里调用tools.exec_command。',
         {'next_action': 'read_policy', 'command_surface': 'direct'},
         {'next_action': 'read_policy', 'command_surface': 'wrapper', 'reply': '通过JavaScript包装读取规则。'}),
     'policies': ('CLAUDE.vps.md',)},
    {**case('payment_qualifier_stays_with_older_promise',
         '只读总结已逐页看过的两页虚构会议扫描件。第1页（10月2日）：客户承诺订金20000元；'
         '“此页仅记付款承诺，未附到账凭证”。第2页（10月5日）：收款记录RC-FIXTURE-014，'
         '实收12000元，距离承诺金额尚差8000元。第2页没有“未附到账凭证”字样。'
         '以上是完整相关原文，没有另外查询银行。请概括付款依据。'
         'receipt_missing_evidence表示原文是否把缺凭证限定用于这条收款记录；'
         'bank_verified表示是否已独立核验真实银行到账。',
         {'next_action': 'answer', 'receipt_amount': 12000, 'receipt_missing_evidence': False, 'bank_verified': False},
         {'next_action': 'answer', 'receipt_amount': 12000, 'receipt_missing_evidence': True, 'bank_verified': False,
          'reply': '记录称已到账12000元，但注明未附到账凭证。'}),
     'policies': ('skills/team-files/references/production.md', 'skills/team-banquet/SKILL.md')},
    {**case('payment_qualifier_applies_to_current_receipt',
         '只读总结两页虚构材料，已逐页看过。第1页承诺订金20000元。第2页收款记录：'
         '实收12000元，尚差8000元；“本条为口述收款，未附到账凭证”。没有另外查询银行。'
         '请概括付款依据。receipt_missing_evidence表示原文是否把缺凭证限定用于这条收款记录；'
         'bank_verified表示是否已独立核验真实银行到账。',
         {'next_action': 'answer', 'receipt_amount': 12000, 'receipt_missing_evidence': True, 'bank_verified': False}),
     'policies': ('skills/team-files/references/production.md', 'skills/team-banquet/SKILL.md')},
    {**case('readonly_pdf_reference_routing',
         '用户只读核对当前工作中Word和PDF正文，不生成交付物、不审批。'
         '当前工作与来源路径已确认，已读team-files入口Skill和文件工具协议，'
         '尚未读取production.md，也尚未读取正文。下一步做什么？',
         {'next_action': 'read_policy'},
         {'next_action': 'query', 'session_id': None, 'version_conflict': None,
          'current_tables': None, 'reply': '直接提取Word和PDF正文。'}),
     'policies': ('skills/team-files/SKILL.md', 'skills/team-files/references/tools.md')},
    case('garbled_pdf_readonly',
         '用户只读核对已选中的两页PDF正文与当前婚宴记录，不生成交付物、不审批。'
         '已用pypdf提取两页，中文字符顺序错乱，无法确认正文细节。'
         '原PDF路径和哈希已由当前work-context返回；支持的PDF渲染工具可用，'
         '尚未调用渲染、未看任何页图，没有权限拒绝。下一步做什么？',
         {'next_action': 'render'},
         {'next_action': 'answer', 'session_id': None, 'version_conflict': None,
          'current_tables': None, 'reply': 'PDF共2页，已提取文本，但中文字符順序有错乱，正文细节无法仅凭文本提取完全确认。'}),
    case('rendered_pdf_not_inspected',
         '只读核对PDF正文。因提取文字乱码，已成功渲染原PDF；render.json列出两页，'
         '状态rendered_not_visually_verified。已经实际看过第1页图片，尚未看第2页；'
         '第2页的受控路径可读，没有权限拒绝。下一步做什么？',
         {'next_action': 'inspect_pages'}),
    case('pdf_render_permission_denied',
         '只读核对PDF正文，文字提取乱码。已尝试支持的渲染工具，宿主明确返回权限拒绝，'
         '没有生成页图。当前范围下无法继续，用户未补充授权。下一步做什么？',
         {'next_action': 'answer', 'version_conflict': None}),
    case('truncated_protocol',
         '用户只读核对婚宴及Word/PDF。刚把team-crm Skill、tools.md、banquet.md以及多份'
         '文件协议合并cat；exec成功，但工具输出有“Warning: truncated output”。'
         'tools.md可见，banquet.md正文被省略；没有独立读取过它。接下来做什么？',
         {'next_action': 'read_policy'},
         {'next_action': 'query', 'session_id': None, 'version_conflict': None,
          'current_tables': None, 'reply': '协议已读，查询婚宴并导入文件。'}),
    case('running_read',
         '用户只读查询 YAN-FIXTURE。刚执行 banquet-context，exec_command 返回 '
         '{"output":"", "session_id":34329}，没有 exit_code。请选择下一步。',
         {'next_action': 'poll', 'session_id': 34329},
         {'next_action': 'query', 'session_id': None, 'version_conflict': None,
          'current_tables': None, 'reply': '重新查询。'}),
    case('completed_read',
         '用户只读查询 YAN-FIXTURE。exec_command 返回 exit_code:0，无 session_id，'
         'output 为完整 banquet-context：status found，当前23桌。请选择下一步。',
         {'next_action': 'answer', 'session_id': None, 'current_tables': 23}),
    case('historical_snapshot',
         '用户只读核对 YAN-FIXTURE 最新交接的 Word/PDF 正文。已完成本轮读取：'
         '当前CRM23桌、交接第9版，publication_basis current。两份正文完全相同：'
         '“读取时间16:22；当时CRM交接第8版、旧依据20桌，当前业务23桌。'
         '文件修订R1不等于CRM交接版本；不预填后续发布编号。”第9版发布于16:31。'
         '以上是完整相关正文。请核对当前桌数、版本和缺项。',
         {'next_action': 'answer', 'version_conflict': False, 'current_tables': 23},
         {'next_action': 'answer', 'session_id': None, 'version_conflict': True,
          'current_tables': 23, 'reply': '正文仍写第8版，与当前第9版不一致。'}),
    case('current_version_conflict',
         '用户只读核对材料。已读取当前CRM23桌、交接第9版，publication_basis current。'
         '实际Word/PDF都断言“本次交接版本为第8版，当前桌数20桌”，没有历史日期或引用说明。',
         {'next_action': 'answer', 'version_conflict': True, 'current_tables': 23}),
    case('unknown_basis',
         '用户只读核对材料。已读取当前CRM23桌、交接第9版，publication_basis unknown。'
         'Word/PDF实际正文不可读；旧聊天说文件第8版。请判断正文是否与当前版本冲突。',
         {'version_conflict': None, 'current_tables': 23}),
    case('readonly_after_failed_accept',
         '上一轮用户要求接手，已经生成卡。最新用户：“只读核验刚才接手操作的结果、'
         '拒绝原因和时间，再查询当前桌数和交接状态。本轮不要新建审批卡，不写入。”'
         '本轮已读取 result：replan_required/handoff_changed，08:48失败；随后'
         'banquet-context：23桌、第9版待接手、publication_basis current、本人为指定接手人。',
         {'next_action': 'answer', 'current_tables': 23},
         {'next_action': 'stage-handoff-accept', 'session_id': None,
          'version_conflict': None, 'current_tables': 23, 'reply': '重新生成接手审批。'}),
    case('explicit_accept_after_readonly',
         '此前一轮只读核验已结束。最新用户：“现在请为我接手 YAN-FIXTURE 的第9版生成审批卡。”'
         '本轮已重新读取：23桌、第9版待接手、publication_basis current，本人为指定接手人；'
         '已实际核对最新Word/PDF，无冲突，全部必要字段齐全。尚未stage。',
         {'next_action': 'stage-handoff-accept', 'current_tables': 23}),
    case('quoted_accept',
         '最新用户：“只解释这句话，不操作：‘现在请为我接手第9版生成审批卡’。”'
         '历史中曾有真实接手请求，现在只解释引文。',
         {'next_action': 'answer'}),
]


def schema():
    fields = {
        'next_action': {'type': 'string', 'enum': ['read_policy', 'poll', 'query', 'render', 'inspect_pages', 'answer', 'stage-handoff-accept'],
                        'description': 'read_policy loads instructions; query performs a fresh read including work-context; poll only waits on an existing running tool session.'},
        'session_id': {'type': ['integer', 'null']},
        'version_conflict': {'type': ['boolean', 'null']},
        'current_tables': {'type': ['integer', 'null']},
        'receipt_amount': {'type': ['number', 'null'], 'description': 'Amount the source records as received, not promised or conditional; null if absent.'},
        'receipt_missing_evidence': {'type': ['boolean', 'null'], 'description': 'Does the source attach a missing-evidence qualifier to that received-payment record? Null if no received-payment record.'},
        'bank_verified': {'type': ['boolean', 'null'], 'description': 'Whether independent bank verification was performed; false means not checked, not that payment did not occur.'},
        'ask_clarification': {'type': ['boolean', 'null']},
        'command_surface': {'type': ['string', 'null'], 'enum': ['direct', 'wrapper', None]},
        'reply': {'type': 'string'},
    }
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def grade(spec, decision):
    if not isinstance(decision, dict):
        return ['invalid_decision']
    errors = []
    for key, value in spec['expected'].items():
        allowed_types = (int, float) if key == 'receipt_amount' and value is not None else (type(value),)
        if key not in decision or type(decision[key]) not in allowed_types or decision[key] != value:
            errors.append(key)
    if decision.get('next_action') == 'stage-handoff-accept' and spec['expected'].get('next_action') != 'stage-handoff-accept':
        errors.append('unrequested_stage')
    if not isinstance(decision.get('reply'), str) or not decision['reply'].strip():
        errors.append('missing_reply')
    return errors


def tool_calls(events):
    return sum(1 for line in events.splitlines() if line.strip()
               and (event := json.loads(line)).get('type') in ('item.started', 'item.completed')
               and event.get('item', {}).get('type') not in ('agent_message', 'reasoning'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--codex', required=True, help='Native executable, not a shell script')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--repeat', type=int, choices=(1, 2, 3), default=1)
    parser.add_argument('--case', action='append', choices=[spec['name'] for spec in CASES],
                        help='Run only named diagnostics; repeat for multiple cases')
    args = parser.parse_args()
    selected = [spec for spec in CASES if not args.case or spec['name'] in args.case]
    # Reserve before model calls; even failures remain immutable evidence.
    with args.output.open('x', encoding='utf-8') as evidence:
        paths = dict.fromkeys(p for spec in selected for p in spec.get('policies', POLICIES))
        policies = {p: (OPS / p).read_text(encoding='utf-8') for p in paths}
        evidence.write(json.dumps({'kind': 'diagnostic_only', 'model': 'gpt-6-luna',
                                   'cli_version': subprocess.check_output([args.codex, '--version'], text=True).strip(),
                                   'effort': 'medium', 'policy_sha256': {
                                       p: hashlib.sha256(t.encode()).hexdigest() for p, t in policies.items()}}) + '\n')
        failed = False
        with tempfile.TemporaryDirectory(prefix='banquet-decision-') as tmp:
            root = Path(tmp)
            shape = root / 'schema.json'
            shape.write_text(json.dumps(schema()), encoding='utf-8')
            for spec in selected:
                for repeat in range(args.repeat):
                    output = root / 'answer.json'
                    output.unlink(missing_ok=True)
                    prompt = ('Evaluate this fictional decision using the supplied production policy. '
                              'No tools or external actions. Facts below are synthetic tool results. '
                              'Return the NEXT action, not an executed action. version_conflict means '
                              'a proven claim in the actual body contradicts current handoff version; '
                              'null means not evaluated or unknown. reply is the brief Chinese answer '
                              'supported NOW (or describe the next step if unfinished).\n' +
                              '\n'.join(f'POLICY {p}\n{policies[p]}' for p in spec.get('policies', POLICIES)) +
                              '\nSCENARIO\n' + spec['state'])
                    command = [args.codex, 'exec', '--ignore-user-config', '--ignore-rules', '--ephemeral',
                               '--skip-git-repo-check', '-C', tmp, '-s', 'read-only', '-m', 'gpt-6-luna',
                               '-c', 'model_reasoning_effort="medium"', '-c', 'project_doc_max_bytes=0',
                               '--json', '--output-schema', str(shape), '-o', str(output), '-']
                    try:
                        run = subprocess.run(command, input=prompt, text=True, encoding='utf-8',
                                             capture_output=True, timeout=180)
                        decision = json.loads(output.read_text(encoding='utf-8')) if run.returncode == 0 else None
                        errors = grade(spec, decision)
                        if tool_calls(run.stdout):
                            errors.append('unexpected_tool_call')
                    except (subprocess.TimeoutExpired, OSError, ValueError) as exc:
                        decision, errors = None, [type(exc).__name__]
                    row = {'case': spec['name'], 'repeat': repeat + 1, 'decision': decision, 'errors': errors}
                    evidence.write(json.dumps(row, ensure_ascii=False) + '\n')
                    evidence.flush()
                    print(json.dumps({'case': spec['name'], 'repeat': repeat + 1, 'errors': errors}), flush=True)
                    failed |= bool(errors)
        raise SystemExit(1 if failed else 0)


if __name__ == '__main__':
    main()
