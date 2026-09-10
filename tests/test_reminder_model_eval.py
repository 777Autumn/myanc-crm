import unittest

from ops.reminder_model_eval import CASES, RECEIPTS, completion_claimed, grade, output_schema


class ReminderEvalTests(unittest.TestCase):
    def case(self, name):
        return next(case for case in CASES if case[0] == name)

    def result(self, name, reply):
        _, _, action, at = self.case(name)
        return {"action": action, "at": at,
                "destination": "self_private" if action in {"create", "private_list"} else None,
                "reply": reply}

    def test_observed_premature_success_is_not_a_pass(self):
        for name, reply in (
            ("next_monday", "已为你创建提醒。持久化成功后会回传具体ID。"),
            ("group_all", '我已用 {"all":true} 发起请求，主机会把提醒排队到私聊。'),
            ("timeout", "已设置提醒，请放心等待。"),
        ):
            with self.subTest(name=name):
                self.assertIn("ungrounded_completion", grade(self.case(name), self.result(name, reply)))

    def test_pre_call_and_unavailable_are_explicit(self):
        for name in ("next_monday", "group_all", "storage_failure", "timeout"):
            with self.subTest(name=name):
                self.assertEqual([], grade(self.case(name), self.result(name, "目前尚未确认执行结果，需要先查询清单核对。")))
                self.assertTrue(grade(self.case(name), self.result(name, "好的。")))

    def test_negated_and_conditional_claims_are_not_false_positives(self):
        for reply in ("无法确定提醒是否已创建。", "还不能确认已排队或已送达。",
                      "只有收到回执后，才代表已排队。"):
            self.assertFalse(completion_claimed(reply))
        self.assertTrue(completion_claimed("无法确认，但提醒已创建。"))
        self.assertIn("ungrounded_progress", grade(self.case("next_monday"),
                      self.result("next_monday", "正在发送创建请求，目前尚未确认。")))

    def test_unavailable_is_unknown_and_needs_reconciliation(self):
        self.assertEqual({"status": "unavailable", "code": "tool_or_delivery_failed"}, RECEIPTS["storage_failure"])
        self.assertEqual({"status": "unavailable", "code": "transport_unavailable"}, RECEIPTS["timeout"])
        for reply in ("目前没有生成提醒，稍后重新发起。", "无法确定是否已创建，请稍后重试。"):
            self.assertTrue(grade(self.case("timeout"), self.result("timeout", reply)))
        reply = "无法确定提醒是否已创建；需要先查询清单核对，有疑问请运维检查，暂不再次创建。"
        self.assertEqual([], grade(self.case("timeout"), self.result("timeout", reply)))

    def test_schema_enforces_format_without_supplying_case_answer(self):
        branches = output_schema()["oneOf"]
        self.assertEqual({"create", "private_list", "clarify", "none", "unsupported"},
                         {action for branch in branches for action in branch["properties"]["action"]["enum"]})
        for branch in branches:
            self.assertEqual(["action", "at", "destination", "reply"], branch["required"])
            self.assertFalse(branch["additionalProperties"])

    def test_null_fields_and_reply_are_required(self):
        result = self.result("quote", "仅总结，没有设置提醒。")
        self.assertEqual([], grade(self.case("quote"), result))
        for field, value in (("destination", "self_private"), ("at", "2026-09-14T09:00:00+08:00"),
                             ("reply", ""), ("reply", None)):
            self.assertTrue(grade(self.case("quote"), {**result, field: value}))
        for invalid in (None, [], "text"):
            self.assertTrue(grade(self.case("quote"), invalid))

    def test_persisted_receipt_is_complete_and_queue_is_not_delivery(self):
        reply = "已设置：2026年9月14日（周一）09:00，北京时间，私聊提醒你联系虚构客户丁总。编号 rem_eval_created。"
        self.assertEqual([], grade(self.case("created_receipt"), self.result("created_receipt", reply)))
        self.assertTrue(grade(self.case("created_receipt"), self.result("created_receipt", reply.replace("rem_eval_created", "rem_invented"))))
        self.assertEqual([], grade(self.case("list_queued"), self.result("list_queued", "完整清单已排队，将私聊发送，尚未确认送达。")))
        self.assertTrue(grade(self.case("list_queued"), self.result("list_queued", "完整清单已排队并已发送到私聊。")))


if __name__ == "__main__":
    unittest.main()
