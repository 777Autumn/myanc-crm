import json
import os
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


TEMPLATE = Path(__file__).resolve().parents[1] / "ops" / "lark-crm-writer-customer-trial.sh"


class CustomerWriterTemplateTests(unittest.TestCase):
    def validate(self, args):
        source = TEMPLATE.read_text(encoding="utf-8")
        # Execute the exact embedded argv validator, not a second implementation.
        validator = source.split("<<'PY' || usage\n", 1)[1].split("\nPY\n", 1)[0]
        with patch.object(sys, "argv", ["-", *args]):
            with self.assertRaises(SystemExit) as raised:
                exec(compile(validator, str(TEMPLATE), "exec"), {})
        return raised.exception.code

    def request(self, **data):
        return ["api", "POST", "/open-apis/contact/v3/users/batch_get_id", "--params",
                '{"user_id_type":"open_id"}', "--data", json.dumps(data)]

    def test_accepts_one_exact_user_email_mobile_and_known_id(self):
        for data in ({"emails": ["colleague@example.com"], "include_resigned": False},
                     {"mobiles": ["13800000000"], "include_resigned": False},
                     {"mobiles": ["+15555555555"], "include_resigned": False}):
            self.assertEqual(0, self.validate(self.request(**data)))
        self.assertEqual(0, self.validate(["contact", "+get-user", "--user-id", "ou_member",
                                         "--user-id-type", "open_id", "--format", "json"]))

    def test_rejects_broad_raw_api_identity_overrides_and_file_input(self):
        good = self.request(emails=["colleague@example.com"], include_resigned=False)
        bad = [good + ["--as", "user"], good + ["--profile", "other"],
               [*good[:2], "/open-apis/im/v1/messages", *good[3:]],
               ["api", "GET", *good[2:]], [*good[:4], '{"user_id_type":"user_id"}', *good[5:]],
               [*good[:-1], "@private-file.json"],
               ["contact", "+search-user", "--query", "同事"]]
        for args in bad:
            with self.subTest(args=args):
                self.assertEqual(64, self.validate(args))

    def test_rejects_multiple_people_enterprise_email_and_ambiguous_json(self):
        for data in ({"emails": ["a@example.com", "b@example.com"], "include_resigned": False},
                     {"enterprise_email": ["a@example.com"], "include_resigned": False},
                     {"emails": ["a@example.com"], "include_resigned": True},
                     {"emails": ["a@example.com"]},
                     {"emails": ["a@example.com"], "mobiles": ["13800000000"], "include_resigned": False},
                     {"mobiles": ["张三"], "include_resigned": False}):
            with self.subTest(data=data):
                self.assertEqual(64, self.validate(self.request(**data)))
        args = self.request(emails=["a@example.com"], include_resigned=False)
        args[-1] = '{"emails":["a@example.com"],"emails":["b@example.com"],"include_resigned":false}'
        self.assertEqual(64, self.validate(args))

    def test_fixed_bot_profile_and_native_boundaries_remain_literal(self):
        source = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn("profile=crm-writer", source)
        self.assertIn("expected_version=1.0.90", source)
        self.assertIn('exec "$cli" "$@" --profile "$profile" --as bot', source)
        self.assertIn("unset MYANC_CRM_HOST_SECRET MYANC_CRM_HOST_SECRET_FILE", source)
        self.assertNotIn("auth login", source)

    def test_bash_syntax_when_available_without_running_template(self):
        bash = Path("C:/Program Files/Git/bin/bash.exe")
        binary = str(bash) if bash.is_file() else shutil.which("bash")
        if not binary:
            self.skipTest("bash is unavailable for offline syntax check")
        completed = subprocess.run([binary, "-n", str(TEMPLATE)], capture_output=True,
                                   text=True, timeout=10, check=False)
        self.assertEqual(0, completed.returncode, completed.stderr)

    def test_whole_wrapper_with_fake_cli_enforces_argv_before_execution(self):
        bash = Path("C:/Program Files/Git/bin/bash.exe")
        binary = str(bash) if bash.is_file() else shutil.which("bash")
        if not binary:
            self.skipTest("bash is unavailable for offline execution")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Pin this test's Python (Windows may expose a python3 app-store stub)
            # and replace the CLI with an offline recorder. The argv logic is unchanged.
            fake = root / "fake-cli"
            fake.write_text('#!/usr/bin/env bash\nif [[ ${1-} == --version ]]; then\n'
                            '  printf "lark-cli version 1.0.90\\n"\nelse\n'
                            '  printf "%s\\n" "$@"\nfi\n', encoding="utf-8", newline="\n")
            fake.chmod(0o700)
            source = TEMPLATE.read_text(encoding="utf-8")
            wrapper = root / "wrapper.sh"
            source = source.replace("cli=/usr/local/libexec/lark-cli-1.0.90", "cli=./fake-cli")
            source = source.replace("python3 - ", f'"{Path(sys.executable).as_posix()}" - ')
            wrapper.write_text(source, encoding="utf-8", newline="\n")
            valid = self.request(emails=["colleague@example.com"], include_resigned=False)
            environment = {**os.environ, "MSYS2_ARG_CONV_EXCL": "*"}
            result = subprocess.run([binary, "-c", shlex.join(["./wrapper.sh", *valid])], cwd=root,
                                    capture_output=True, text=True, timeout=10, check=False, env=environment)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual([*valid, "--profile", "crm-writer", "--as", "bot"], result.stdout.splitlines())
            for invalid in (valid + ["--as", "user"], valid + ["--profile=other"],
                            [*valid[:2], "/open-apis/im/v1/messages", *valid[3:]],
                            ["contact", "+search-user", "--query", "Colleague"],
                            ["base", "+record-list", "--base-token", "fixture", "--as", "user"]):
                with self.subTest(invalid=invalid):
                    result = subprocess.run([binary, "-c", shlex.join(["./wrapper.sh", *invalid])], cwd=root,
                                            capture_output=True, text=True, timeout=10, check=False, env=environment)
                    self.assertEqual(64, result.returncode, result.stderr)
                    self.assertEqual("", result.stdout)


if __name__ == "__main__":
    unittest.main()
