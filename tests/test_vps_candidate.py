import importlib.util
import hashlib
import io
import json
import subprocess
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
    def test_old_gateway_has_no_file_runtime_and_partial_runtime_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gateway, bundle = root / "gateway", root / "bundle"
            (gateway / "ops").mkdir(parents=True)
            bundle.mkdir()
            builder.copy_file_runtime_templates(gateway, bundle)
            self.assertFalse((bundle / "gateway-ops").exists())
            (gateway / "ops/file_tool.py").write_text("synthetic", encoding="utf-8")
            with self.assertRaises(ValueError):
                builder.copy_file_runtime_templates(gateway, bundle)

    def test_build_packages_only_explicit_fresh_sources_with_all_hashes(self):
        for knowledge_sha in (None, "c" * 40):
            with self.subTest(knowledge=knowledge_sha), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                state = root / "state.json"
                state.write_text(json.dumps(dict(version=1, reconciliation="fixture", incidents=[])), encoding="utf-8")
                exported, commands = [], []
                def export(repo, commit, destination):
                    exported.append((repo, commit, destination))
                    files = {"77AutumN/myanc-crm": ["myanc_crm/cli.py", "ops/runtime.py",
                                 "ops/CLAUDE.vps.md", "ops/skills/team-crm/SKILL.md",
                                 "ops/skills/team-crm/references/tools.md",
                                 "ops/skills/team-reminders/SKILL.md",
                                 "ops/skills/team-reminders/references/tools.md",
                                 "ops/skills/team-files/SKILL.md",
                                 "ops/skills/team-files/references/tools.md"],
                             "77AutumN/cc-connect-anc": ["web/pnpm-lock.yaml", "ops/file_tool.py",
                                 "ops/work_sandbox.py", "ops/config.local.json", "ops/private.sqlite"],
                             "77AutumN/myanc-team-brain": ["team_brain/tool.py", "team_brain/host.py",
                                 "skills/team-brain/SKILL.md", "skills/team-brain/references/tools.md",
                                 "ops/team-brain-host.example", "ops/host.example.json",
                                 "ops/install.py", "ops/bootstrap.py", "team_brain/__pycache__/old.pyc"]}
                    for name in files[repo]:
                        path = destination / name
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_text(commit, encoding="utf-8")
                    if repo == '77AutumN/myanc-crm' and knowledge_sha:
                        wiki = destination / 'ops' / builder.mock_wiki.RELATIVE_ROOT
                        wiki.mkdir(parents=True)
                        (wiki / 'index.md').write_text('fictional source', encoding='utf-8')
                        (wiki / 'metadata.json').write_text(json.dumps(dict(
                            company_id='DEMO-WIKI-001', data_scope='虚构演练', version=1)), encoding='utf-8')
                def run(args, cwd, env=None):
                    commands.append((args, cwd, env))
                    if args[:2] == ["go", "build"]:
                        Path(args[args.index("-o") + 1]).write_bytes(b"fresh-binary")
                def version(*args):
                    return "10.0.0" if args[0].startswith("pnpm") else "fixture-toolchain"
                output = root / "candidate.tgz"
                with patch.object(builder.gate, "STATE", state), \
                     patch.object(builder.gate, "released", return_value={}) as released, \
                     patch.object(builder.gate, "command", side_effect=version), \
                     patch.object(builder, "export", side_effect=export), patch.object(builder, "run", side_effect=run), \
                     patch.object(builder, "paired_tests", return_value=["fixture-journey"]):
                    result = builder.build("a" * 40, "b" * 40, output, knowledge_sha)
                self.assertEqual(result["sources"], {repo: commit for repo, commit, _ in exported})
                self.assertEqual(len(exported), 3 if knowledge_sha else 2)
                self.assertEqual(released.call_count, 2 * len(exported))
                self.assertIn(["pnpm", "install", "--frozen-lockfile"], [args for args, _, _ in commands])
                with tarfile.open(output) as archive:
                    names = archive.getnames()
                    self.assertFalse(any("__pycache__" in name for name in names))
                    self.assertNotIn("candidate/knowledge/ops/install.py", names)
                    self.assertNotIn("candidate/knowledge/ops/bootstrap.py", names)
                    for name, digest in result["files"].items():
                        self.assertEqual(hashlib.sha256(archive.extractfile("candidate/" + name).read()).hexdigest(), digest)
                    self.assertEqual("candidate/knowledge/team_brain/tool.py" in names, bool(knowledge_sha))
                    wiki_source = 'ops/' + builder.mock_wiki.RELATIVE_ROOT.as_posix() + '/SOURCE.json'
                    self.assertEqual(wiki_source in result['files'], bool(knowledge_sha))
                    if knowledge_sha:
                        source = json.load(archive.extractfile('candidate/' + wiki_source))
                        self.assertEqual(source['source_commit'], 'a' * 40)
                        self.assertEqual(source['knowledge_version'], 1)
                        self.assertEqual(source['files']['index.md'], hashlib.sha256(b'fictional source').hexdigest())
                    for skill in ("team-crm", "team-reminders", "team-files"):
                        for name in ("SKILL.md", "references/tools.md"):
                            path = f"ops/skills/{skill}/{name}"
                            self.assertIn(path, result["files"])
                            self.assertEqual(archive.extractfile("candidate/" + path).read(), b"a" * 40)
                    for name in ("file_tool.py", "work_sandbox.py"):
                        path = f"gateway-ops/{name}"
                        self.assertIn(path, result["files"])
                        self.assertEqual(archive.extractfile("candidate/" + path).read(), b"b" * 40)
                    self.assertFalse(any(name.endswith(("config.local.json", "private.sqlite")) for name in names))
                if knowledge_sha:
                    knowledge_root = next(destination for repo, _, destination in exported if repo.endswith("team-brain"))
                    self.assertTrue(any(cwd == knowledge_root and args[:3] == ["python", "-m", "unittest"]
                                        and env["MYANC_TEAM_BRAIN_ROOT"] == str(knowledge_root)
                                        for args, cwd, env in commands))

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

    def test_shared_case_candidate_requires_its_paired_journey(self):
        names = ['TestCUJ_CRMIPC1_CustomerApprovalAndContinuedDiscussion',
                 'TestCUJ_CRMIPC2_ProfileThenIndependentFollowup',
                 'TestCUJ_CRMDaily1_ListAndPlanApproval']
        events = [dict(Action='pass',Test=name,Package='fixture/actionhost/crmfollowup') for name in names]
        events.append(dict(Action='pass',Test='TestCUJ_Fixture',Package='fixture/core'))
        with patch.object(Path,'is_file',return_value=True):
            with patch.object(builder.subprocess,'check_output',return_value='\n'.join(map(json.dumps,events))):
                with self.assertRaises(ValueError):
                    builder.paired_tests(Path('gateway'),{})
            events.append(dict(Action='pass',Test='TestCUJ_CASEIPC_SharedProgressPrivateGrantAndRevision',Package='fixture/actionhost/crmfollowup'))
            with patch.object(builder.subprocess,'check_output',return_value='\n'.join(map(json.dumps,events))):
                self.assertIn(events[-1]['Test'],builder.paired_tests(Path('gateway'),{}))
                with self.assertRaises(ValueError):
                    builder.paired_tests(Path('gateway'), {'MYANC_SPIKE_CRM_ROOT': 'fresh-crm'})
            events.append(dict(Action='pass',Test='TestCUJ_CASEIPC_ProjectMembershipAcrossPrivateEntries',Package='fixture/actionhost/crmfollowup'))
            with patch.object(builder.subprocess,'check_output',return_value='\n'.join(map(json.dumps,events))):
                with self.assertRaises(ValueError):
                    builder.paired_tests(Path('gateway'), {'MYANC_SPIKE_CRM_ROOT': 'fresh-crm'})
            events.append(dict(Action='pass',Test='TestCUJ_CASEIPC_NaturalClarificationAndConfirmedContinuation',Package='fixture/actionhost/crmfollowup'))
            with patch.object(builder.subprocess,'check_output',return_value='\n'.join(map(json.dumps,events))):
                self.assertIn(events[-1]['Test'],builder.paired_tests(Path('gateway'), {'MYANC_SPIKE_CRM_ROOT': 'fresh-crm'}))

    def test_knowledge_source_is_explicit_and_ambient_canaries_are_disabled(self):
        with patch.dict(builder.os.environ, {"MYANC_TEAM_BRAIN_ROOT": "dirty-worktree",
                                            "MYANC_REAL_CLAUDE_CANARY": "1", "MYANC_REAL_KNOWLEDGE_COMMAND": "external"}):
            old = builder.build_environment("crm")
            new = builder.build_environment("crm", "fresh-knowledge")
        self.assertNotIn("MYANC_TEAM_BRAIN_ROOT", old)
        self.assertEqual(new["MYANC_TEAM_BRAIN_ROOT"], "fresh-knowledge")
        self.assertNotIn("MYANC_REAL_CLAUDE_CANARY", new)
        self.assertNotIn("MYANC_REAL_KNOWLEDGE_COMMAND", new)

    def test_three_source_pair_requires_knowledge_journey_not_just_old_green_tests(self):
        names = ["TestCUJ_CRMIPC1_CustomerApprovalAndContinuedDiscussion",
                 "TestCUJ_CRMIPC2_ProfileThenIndependentFollowup",
                 "TestCUJ_CRMDaily1_ListAndPlanApproval"]
        events = [dict(Action="pass", Test=name, Package="fixture/actionhost/crmfollowup") for name in names]
        events.append(dict(Action="pass", Test="TestCUJ_REMINDER1_ClockCreateKnowledgeAndCRM", Package="fixture/core"))
        env = {"MYANC_TEAM_BRAIN_ROOT": "fresh"}
        for action in ("skip", "fail"):
            extra = dict(Action=action, Test="TestCUJ_KNOWLEDGEIPC2_CatalogReadFollowupAndScope")
            with patch.object(builder.subprocess, "check_output", return_value="\n".join(map(json.dumps, [*events, extra]))):
                with self.assertRaises(ValueError):
                    builder.paired_tests(Path("gateway"), env)
        events.append(dict(Action="pass", Test="TestCUJ_KNOWLEDGEIPC2_CatalogReadFollowupAndScope", Package="fixture/actionhost/crmfollowup"))
        with patch.object(builder.subprocess, "check_output", return_value="\n".join(map(json.dumps, events))):
            self.assertIn(events[-1]["Test"], builder.paired_tests(Path("gateway"), env))

    def fake_run(self, args, cwd):
        if "archive" in args:
            archive_path = next(arg.split("=", 1)[1] for arg in args if arg.startswith("--output="))
            with tarfile.open(archive_path, "w") as archive:
                member = tarfile.TarInfo(self.member)
                content = b"committed content\n"
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))

    def test_archive_overrides_autocrlf_for_linux_scripts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            def git(*args):
                return subprocess.check_output(["git", "-C", str(root), *args])
            git("config", "core.autocrlf", "false")
            script = b"#!/usr/bin/env python3\nprint('fixture')\n"
            (root / "script.py").write_bytes(script)
            git("add", "script.py")
            git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                "commit", "-qm", "fixture")
            commit = git("rev-parse", "HEAD").decode().strip()
            git("config", "core.autocrlf", "true")
            # Prove the old command exhibits the actual CRLF corruption.
            git("archive", "--format=tar", f"--output={root / 'old.tar'}", commit)
            with tarfile.open(root / "old.tar") as archive:
                self.assertIn(b"\r\n", archive.extractfile("script.py").read())
            builder.archive_commit(root, commit, root / "fixed.tar")
            with tarfile.open(root / "fixed.tar") as archive:
                self.assertEqual(script, archive.extractfile("script.py").read())

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
