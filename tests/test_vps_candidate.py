import importlib.util
import io
import json
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

OPS = Path(__file__).parents[1] / "ops"
sys.path.insert(0, str(OPS))
SPEC = importlib.util.spec_from_file_location("build_vps_candidate", OPS / "build_vps_candidate.py")
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class CandidateTests(unittest.TestCase):
    def test_skipped_or_missing_cross_repo_tests_reject_success_exit(self):
        for output in ("", json.dumps({"Action": "skip", "Test": "TestCUJ_CRMIPC1_CustomerApprovalAndContinuedDiscussion"})):
            with patch.object(builder.subprocess, "check_output", return_value=output):
                with self.assertRaises(ValueError):
                    builder.paired_tests(Path("gateway"), {})

    def test_persistent_go_flags_and_external_overlay_are_disabled(self):
        with patch.dict(builder.os.environ, {"GOFLAGS": "-overlay=external.json -tags=no_web",
                                             "GOENV": "external-config", "GOWORK": "external.work"}):
            env = builder.build_environment("fixed-crm")
        self.assertEqual("off", env["GOENV"])
        self.assertEqual("off", env["GOWORK"])
        self.assertEqual("", env["GOFLAGS"])

    def fake_run(self, args, cwd):
        if args[1] == "archive":
            archive_path = next(arg.split("=", 1)[1] for arg in args if arg.startswith("--output="))
            with tarfile.open(archive_path, "w") as archive:
                member = tarfile.TarInfo(self.member)
                content = b"committed content\n"
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))

    def test_export_uses_only_fetched_sha_not_worktree_or_old_assets(self):
        self.member = "source.py"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "old-dist.js").write_text("ignored stale output", encoding="utf-8")
            with patch.object(builder, "run", side_effect=self.fake_run) as commands, \
                 patch.object(builder.gate, "command", return_value="a" * 40):
                builder.export("77AutumN/myanc-crm", "a" * 40, root / "export")
            self.assertEqual(["source.py"], [path.name for path in (root / "export").iterdir()])
            self.assertTrue(any(call.args[0][-1] == "a" * 40 for call in commands.call_args_list))

    def test_traversal_archive_rejected(self):
        self.member = "../escape.py"
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(builder, "run", side_effect=self.fake_run), \
             patch.object(builder.gate, "command", return_value="a" * 40):
            with self.assertRaises(ValueError):
                builder.export("77AutumN/myanc-crm", "a" * 40, Path(temp) / "export")

    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "candidate.tgz"
            output.write_bytes(b"original")
            with self.assertRaises(ValueError):
                builder.build("a" * 40, "b" * 40, output)
            self.assertEqual(b"original", output.read_bytes())

    def test_missing_shared_state_blocks_before_fetch(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(builder.gate, "STATE", Path(temp) / "absent.json"), \
             patch.object(builder, "export") as export:
            with self.assertRaises(FileNotFoundError):
                builder.build("a" * 40, "b" * 40, Path(temp) / "candidate.tgz")
            export.assert_not_called()
