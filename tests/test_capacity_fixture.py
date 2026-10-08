"""The capacity fixture must preserve real route and personal-read denials."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from myanc_crm.connections import ConnectionBlocked, Connections, access

spec = importlib.util.spec_from_file_location("capacity_fixture", Path(__file__).resolve().parents[1]/"spikes/host_tool_fixture.py")
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


class CapacityFixtureTests(unittest.TestCase):
    def test_source_startup_keeps_app_and_cli_version_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = fixture.capacity_config(Path(tmp))
            run = mock.Mock(return_value=subprocess.CompletedProcess([], 0, '1.0.90\n', ''))
            connection = Connections(config, run=run)
            self.assertEqual('enabled', connection.validate_source('capacity-app')['status'])
            self.assertEqual([config['personal_connections']['cli_path'], '--version'], run.call_args.args[0])
            with self.assertRaises(ConnectionBlocked):
                connection.validate_source('wrong-app')
            run.return_value.stdout = '1.0.91\n'
            with self.assertRaises(ConnectionBlocked):
                connection.validate_source('capacity-app')

    def test_real_cli_envelope_shared_read_and_private_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = fixture.capacity_config(Path(tmp))
            env = dict(os.environ, MYANC_SPIKE_DIR=tmp, MYANC_SPIKE_SEED="capacity",
                       MYANC_CRM_HOST_SECRET="offline-gateway-host-secret-00000000000001",
                       MYANC_CRM_ACTION_TOKEN="offline-session-action-token-000000001")
            for index, allowed in ((1, True), (0, False)):
                principal = {k:v for k,v in config["personal_connections"]["routes"][index].items() if k != "audience"}
                principal.update(session_key="fixture-session", message_id="fixture-message")
                result = subprocess.run([sys.executable, "-B", fixture.__file__, "host-tool"],
                    input=json.dumps(dict(command="customer", request=dict(customer_query="C-002"), principal=principal)),
                    env=env, capture_output=True, text=True, encoding="utf-8", timeout=10)
                payload = json.loads(result.stdout)
                self.assertEqual(allowed, payload.get("status") == "found", payload)
            result = subprocess.run([sys.executable, "-B", fixture.__file__, "host-tool"],
                input=json.dumps(dict(command="stage", request={}, principal=principal)), env=env,
                capture_output=True, text=True, encoding="utf-8", timeout=10)
            self.assertNotEqual(0, result.returncode)

    def test_shared_read_and_file_work_keep_route_and_personal_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = fixture.capacity_config(Path(tmp))
            connection = Connections(config)
            for route in config["personal_connections"]["routes"]:
                principal = {k:v for k,v in route.items() if k != "audience"}
                principal.update(session_key="test-session", message_id="test-message")
                self.assertEqual("allowed", connection.guard("file-status", principal, "", "work")["status"])
                if route["audience"] == "shared":
                    self.assertIsNone(access(config, "customer", principal))
                    self.assertEqual("allowed", connection.guard("customer", principal, "", "work")["status"])
                else:
                    with self.assertRaises(ConnectionBlocked):
                        connection.guard("customer", principal, "", "work")
                with self.assertRaises(ConnectionBlocked):
                    connection.guard("file-status", dict(principal, user_id="unmapped"), "", "work")


if __name__ == "__main__":
    unittest.main()
