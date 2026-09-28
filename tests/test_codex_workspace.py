"""Native discovery and sandbox checks; fictional files, no login or model turn."""
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import tomllib
import unittest


OPS = Path(__file__).resolve().parents[1] / "ops"
TEMPLATE = OPS / "runtime/codex.config.example.toml"


class CodexWorkspaceTests(unittest.TestCase):
    def test_template_keeps_native_profile_and_credential_boundary(self):
        config = tomllib.loads(TEMPLATE.read_text(encoding="utf-8"))
        self.assertEqual((config["model"], config["model_reasoning_effort"]),
                         ("gpt-6-luna", "medium"))
        profile = config["permissions"][config["default_permissions"]]
        self.assertEqual(profile["extends"], ":workspace")
        self.assertEqual(profile["filesystem"]["~/.codex"], "deny")
        self.assertFalse(profile["network"]["allow_upstream_proxy"])
        self.assertNotIn("sandbox_mode", config)

    @unittest.skipUnless(sys.platform == "darwin" and os.environ.get("ANC_CODEX_BIN"),
                         "requires pinned native Mac CLI; no model or credentials")
    def test_native_discovery_and_protected_workspace(self):
        cli = os.environ["ANC_CODEX_BIN"]
        self.assertNotEqual(os.geteuid(), 0, "model tools must run as an ordinary UID")
        self.assertEqual(subprocess.check_output([cli, "--version"], text=True).strip(),
                         "codex-cli 0.157.1")
        with tempfile.TemporaryDirectory(prefix="anc-codex-workspace-") as tmp:
            root = Path(tmp).resolve()
            auth, workspace = root / ".codex", root / "workspace"
            auth.mkdir(mode=0o700)
            workspace.mkdir(mode=0o700)
            shutil.copyfile(TEMPLATE, auth / "config.toml")
            (auth / "private-fixture").write_text("fictional-private-data", encoding="utf-8")
            shutil.copyfile(OPS / "CLAUDE.vps.md", workspace / "CLAUDE.md")
            (workspace / "AGENTS.md").symlink_to("CLAUDE.md")
            shutil.copytree(OPS / "skills/team-files", workspace / ".claude/skills/team-files")
            (workspace / ".agents").mkdir()
            (workspace / ".agents/skills").symlink_to("../.claude/skills", target_is_directory=True)
            env = {"HOME": str(root), "CODEX_HOME": str(auth), "PATH": "/usr/bin:/bin"}
            with tempfile.TemporaryFile(mode="w+") as errors:
                process = subprocess.Popen([cli, "app-server", "--listen", "stdio://"],
                                           cwd=workspace, env=env, stdin=subprocess.PIPE,
                                           stdout=subprocess.PIPE, stderr=errors, text=True)
                messages = queue.Queue()

                def receive():
                    try:
                        for line in process.stdout:
                            messages.put(json.loads(line))
                    finally:
                        messages.put({"closed": True})

                reader = threading.Thread(target=receive, daemon=True)
                reader.start()

                def request(i, method, params):
                    process.stdin.write(json.dumps({"id": i, "method": method, "params": params}) + "\n")
                    process.stdin.flush()
                    while True:
                        message = messages.get(timeout=30)
                        self.assertNotIn("closed", message, "app-server closed before response")
                        if message.get("id") == i:
                            self.assertNotIn("error", message)
                            return message["result"]

                try:
                    request(1, "initialize", {"clientInfo": {"name": "anc_offline_workspace", "version": "1"},
                                              "capabilities": {"experimentalApi": True}})
                    entries = request(2, "skills/list", {"cwds": [str(workspace)], "forceReload": True})["data"]
                    entry = next(item for item in entries if item["cwd"] == str(workspace))
                    self.assertFalse(entry["errors"])
                    skill = next(item for item in entry["skills"] if item["name"] == "team-files")
                    self.assertTrue(skill["enabled"])
                    self.assertEqual(Path(skill["path"]).resolve(),
                                     workspace / ".claude/skills/team-files/SKILL.md")
                    script = r'''set -eu
grep -q REMOTE_WORKSPACE_BOUNDARY_V3 AGENTS.md
cat .agents/skills/team-files/SKILL.md > /dev/null
printf 'fictional result v1' > result-v1.txt
printf 'fictional result v2' > result-v2.txt
for file in AGENTS.override.md AGENTS.md CLAUDE.md .agents/new.md .claude/new.md .codex/new.md .mcp.json; do
  if (mkdir -p "$(dirname "$file")"; printf forbidden > "$file") 2>/dev/null; then exit 11; fi
done
if mv .claude renamed-rules 2>/dev/null; then exit 12; fi
if rm AGENTS.md 2>/dev/null; then exit 13; fi
if cat "$HOME/.codex/private-fixture" >/dev/null 2>&1; then exit 14; fi
if (printf forbidden > "$HOME/.codex/config.toml") 2>/dev/null; then exit 15; fi
test -s result-v1.txt && test -s result-v2.txt
printf 'protected workspace passed\n'
'''
                    result = request(3, "command/exec", {"permissionProfile": "anc-work", "cwd": str(workspace),
                                                         "command": ["/bin/sh", "-c", script], "timeoutMs": 10000})
                    self.assertEqual(result["exitCode"], 0, result)
                    self.assertIn("protected workspace passed", result["stdout"])
                    self.assertEqual((workspace / "CLAUDE.md").read_bytes(), (OPS / "CLAUDE.vps.md").read_bytes())
                    self.assertEqual((auth / "config.toml").read_bytes(), TEMPLATE.read_bytes())
                    # Exercise the production monitor inside the actual sandbox:
                    # macOS's setuid ps is forbidden even though libproc is usable.
                    program = ("import sys; sys.path.insert(0, " + repr(str(OPS / "runtime")) + "); "
                               "import team_file_render as r; "
                               "assert r.run(['/bin/sleep', '.3']) == b''; "
                               "r.run(['/bin/sleep', '5'], memory_limit=1)")
                    python_env = [key + "=" + os.environ[key] for key in
                                  ("PYTHONHOME", "DYLD_FRAMEWORK_PATH") if key in os.environ]
                    checked = request(4, "command/exec", {
                        "permissionProfile": "anc-work", "cwd": str(workspace),
                        "command": ["/usr/bin/env", *python_env, sys.executable, "-I", "-c", program],
                        "timeoutMs": 10000})
                    self.assertNotEqual(checked["exitCode"], 0)
                    self.assertIn("document process group exceeded memory budget", checked["stderr"])
                finally:
                    process.stdin.close()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                    reader.join(timeout=5)
                    process.stdout.close()


if __name__ == "__main__":
    unittest.main()
