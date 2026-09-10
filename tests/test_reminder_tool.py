import json
import unittest

from test_crm_tool import CrmToolClientTests, ProxyPeer


class ReminderToolTests(unittest.TestCase):
    invoke = CrmToolClientTests.invoke
    def test_reminder_business_commands_share_authenticated_transport(self):
        cases = {
            "reminder-create": {"content": "联系虚构客户", "at": "2026-09-14T09:00:00+08:00"},
            "reminder-list": {"all": True},
            "reminder-update": {"id": "rem_fixture", "version": 1, "content": "测试"},
            "reminder-cancel": {"id": "rem_fixture", "version": 2},
        }
        for command, body in cases.items():
            with self.subTest(command=command):
                peer = ProxyPeer({"status": "ok"})
                code, result, factory = self.invoke([command], json.dumps(body).encode(), peer)
                self.assertEqual(0, code)
                self.assertEqual("ok", result["status"])
                factory.assert_called_once()

    def test_reminder_never_accepts_identity_destination_or_shell(self):
        for command in ("reminder-create", "reminder-list", "reminder-update", "reminder-cancel"):
            for field in ("user", "user_id", "recipient", "chat_id", "project", "path", "exec", "cron"):
                with self.subTest(command=command, field=field):
                    code, result, factory = self.invoke([command], json.dumps({field: "forged"}).encode(), ProxyPeer({"status": "ok"}))
                    self.assertEqual(2, code)
                    self.assertEqual("invalid_input", result["code"])
                    factory.assert_not_called()


if __name__ == "__main__":
    unittest.main()
