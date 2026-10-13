import unittest

from ops.banquet_behavior_eval import CASES, grade, schema, tool_calls


class BanquetBehaviorEvalTests(unittest.TestCase):
    def test_observed_failures_are_rejected(self):
        observed = [case for case in CASES if case['observed']]
        self.assertEqual(3, len(observed))
        for case in observed:
            with self.subTest(case=case['name']):
                self.assertTrue(grade(case, case['observed']))

    def test_expected_decisions_and_each_counterpart(self):
        for case in CASES:
            with self.subTest(case=case['name']):
                decision = {'next_action': 'answer', 'session_id': None,
                            'version_conflict': None, 'current_tables': None, 'reply': '虚构决策说明。',
                            **case['expected']}
                self.assertEqual([], grade(case, decision))
                for field in case['expected']:
                    wrong = dict(decision)
                    del wrong[field]
                    self.assertIn(field, grade(case, wrong))
                self.assertTrue(grade(case, {**decision, 'reply': ''}))
                self.assertTrue(grade(case, None))

    def test_schema_does_not_supply_a_case_answer(self):
        shape = schema()
        self.assertEqual(set(shape['properties']), set(shape['required']))
        self.assertFalse(shape['additionalProperties'])
        self.assertNotIn('const', str(shape))

    def test_unknown_body_does_not_authorize_a_stage(self):
        case = next(case for case in CASES if case['name'] == 'unknown_basis')
        decision = {'next_action': 'query', 'version_conflict': None, 'current_tables': 23, 'reply': '正文尚未核对。'}
        self.assertEqual([], grade(case, decision))
        self.assertIn('unrequested_stage', grade(case, {**decision, 'next_action': 'stage-handoff-accept'}))

    def test_diagnostic_rejects_tools_even_without_start_event(self):
        self.assertEqual(0, tool_calls('{"type":"item.completed","item":{"type":"agent_message"}}'))
        for phase in ('started', 'completed'):
            for kind in ('command_execution', 'mcp_tool_call', 'web_search'):
                self.assertEqual(1, tool_calls('{"type":"item.' + phase + '","item":{"type":"' + kind + '"}}'))


if __name__ == '__main__':
    unittest.main()
