import unittest

from ops.reminder_model_eval import CASES, grade


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
                self.assertEqual([], grade(self.case(name), self.result(name, "目前尚未确认执行结果。")))
                self.assertTrue(grade(self.case(name), self.result(name, "好的。")))

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
