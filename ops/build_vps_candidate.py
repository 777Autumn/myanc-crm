"""Build a candidate from explicit merged SHAs; never install or contact the VPS."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import release_gate as gate
import mock_wiki

TARGETS = ("linux/amd64", "darwin/arm64")
MAC_JOBS = ("mac-codex (ubuntu-latest)", "mac-codex (macos-latest)")


def run(args, cwd, env=None):
    if os.name == "nt" and args[0] == "pnpm":
        args = ["pnpm.cmd", *args[1:]]
    subprocess.run(args, cwd=cwd, env=env, check=True)


def build_environment(crm, knowledge=None):
    env = os.environ.copy()
    for name in ("GOOS", "GOARCH", "CGO_ENABLED", "GOFLAGS", "GOWORK", "GOENV"):
        env.pop(name, None)
    for name in list(env):
        if name == "MYANC_TEAM_BRAIN_ROOT" or name.startswith(("MYANC_REAL_CLAUDE_", "MYANC_REAL_KNOWLEDGE_")):
            env.pop(name)
    if knowledge is not None:
        env["MYANC_TEAM_BRAIN_ROOT"] = str(knowledge)
    env.update(GOENV="off", GOWORK="off", GOFLAGS="", GOTOOLCHAIN="local",
               GOEXPERIMENT="", GOAMD64="v1", MYANC_SPIKE_CRM_ROOT=str(crm))
    return env


def paired_tests(gateway, env):
    output = subprocess.check_output(
        ["go", "test", "./actionhost/crmfollowup", "./core", "-run",
         "TestCUJ|Test.*Journey", "-count=1", "-json"], cwd=gateway, env=env,
        text=True, encoding="utf-8")
    events = [json.loads(line) for line in output.splitlines() if line.strip()]
    required = {"TestCUJ_CRMIPC1_CustomerApprovalAndContinuedDiscussion",
                "TestCUJ_CRMIPC2_ProfileThenIndependentFollowup",
                "TestCUJ_CRMDaily1_ListAndPlanApproval"}
    if "MYANC_TEAM_BRAIN_ROOT" in env:
        required.add("TestCUJ_KNOWLEDGEIPC2_CatalogReadFollowupAndScope")
    if (gateway / 'actionhost/crmfollowup/shared_case_journey_test.go').is_file():
        required.add('TestCUJ_CASEIPC_SharedProgressPrivateGrantAndRevision')
    if 'MYANC_SPIKE_CRM_ROOT' in env and (Path(env['MYANC_SPIKE_CRM_ROOT']) / 'tests/test_project_context.py').is_file():
        required.add('TestCUJ_CASEIPC_ProjectMembershipAcrossPrivateEntries')
    if 'MYANC_SPIKE_CRM_ROOT' in env and (Path(env['MYANC_SPIKE_CRM_ROOT']) / 'tests/test_case_confirmation.py').is_file():
        required.add('TestCUJ_CASEIPC_NaturalClarificationAndConfirmedContinuation')
    passed = {item.get("Test") for item in events if item.get("Action") == "pass"}
    gate.require(required <= passed, "required cross-repo journeys did not execute successfully")
    gate.require(any(item.get("Action") == "pass" and item.get("Test", "").startswith("TestCUJ")
                     and item.get("Package", "").endswith("/core") for item in events),
                 "core CUJ tests did not execute successfully")
    return sorted(required)


def archive_commit(scratch, commit, archive):
    # git archive applies working-tree conversions, including system autocrlf.
    # Linux shebang scripts must retain their committed LF representation.
    run(["git", "-c", "core.autocrlf=false", "-c", "core.eol=lf", "archive",
         "--format=tar", f"--output={archive}", commit], scratch)


def export(repo, commit, destination):
    gate.sha(commit)
    gate.require(repo in gate.REPOS, "unsupported source repository")
    destination.mkdir()
    with tempfile.TemporaryDirectory(prefix="release-fetch-") as scratch:
        run(["git", "init", scratch], scratch)
        run(["git", "remote", "add", "origin", f"https://github.com/{repo}.git"], scratch)
        run(["git", "fetch", "--depth=1", "origin", commit], scratch)
        actual = gate.command("git", "-C", scratch, "rev-parse", "FETCH_HEAD")
        gate.require(actual == commit, "fetched source SHA mismatch")
        archive = Path(scratch) / "source.tar"
        archive_commit(scratch, commit, archive)
        with tarfile.open(archive) as source:
            for member in source.getmembers():
                target = (destination / member.name).resolve()
                gate.require(target.is_relative_to(destination.resolve())
                             and not member.issym() and not member.islnk()
                             and (member.isfile() or member.isdir()), "unsafe source archive")
            source.extractall(destination, filter="data")


def copy_file_runtime_templates(gateway, bundle):
    sources = [gateway / "ops" / name for name in ("file_tool.py", "work_sandbox.py")]
    if not any(path.exists() for path in sources):
        return  # Historical gateway commits have no file-work capability.
    gate.require(all(path.is_file() and not path.is_symlink() for path in sources),
                 "file runtime requires both static client and launcher")
    destination = bundle / "gateway-ops"
    destination.mkdir()
    for path in sources:
        shutil.copy2(path, destination / path.name)


def build(crm_sha, gateway_sha, output, knowledge_sha=None, target="linux/amd64"):
    gate.require(target in TARGETS, "unsupported candidate target")
    output = Path(output).resolve()
    gate.require(not output.exists(), "candidate output already exists")
    gate.ordinary_allowed()
    sources = gate.source_commits(crm_sha, gateway_sha, knowledge_sha)
    evidence = {repo: gate.released(repo, commit) for repo, commit in sources.items()}
    if target == "darwin/arm64":
        evidence["77AutumN/cc-connect-anc"]["native_ci"] = gate.ci(
            "77AutumN/cc-connect-anc", gateway_sha, "push", required_jobs=MAC_JOBS)
    versions = {name: gate.command("pnpm.cmd" if os.name == "nt" and name == "pnpm" else name, *args) for name, args in
                (("go", ("version",)), ("node", ("--version",)), ("pnpm", ("--version",)),
                 ("python", ("--version",)))}
    gate.require(versions["pnpm"].startswith("10."), "pnpm 10 required")
    with tempfile.TemporaryDirectory(prefix="vps-candidate-") as scratch:
        root = Path(scratch)
        crm, gateway = root / "crm", root / "gateway"
        export("77AutumN/myanc-crm", crm_sha, crm)
        export("77AutumN/cc-connect-anc", gateway_sha, gateway)
        knowledge = root / "knowledge" if knowledge_sha is not None else None
        if knowledge is not None:
            export("77AutumN/myanc-team-brain", knowledge_sha, knowledge)
        # No worktree or pre-existing ignored web assets are consulted.
        run(["pnpm", "install", "--frozen-lockfile"], gateway / "web")
        run(["pnpm", "build"], gateway / "web")
        env = build_environment(crm, knowledge)
        run(["go", "mod", "verify"], gateway, env)
        run(["python", "-m", "unittest", "discover", "-s", "tests"], crm, env)
        run(["python", "-m", "unittest", "discover", "-s", "spikes"], crm, env)
        if knowledge is not None:
            run(["python", "-m", "unittest", "discover", "-s", "tests"], knowledge, env)
        journeys = paired_tests(gateway, env)
        goos, goarch = target.split("/")
        env.update(GOOS=goos, GOARCH=goarch, CGO_ENABLED="0")
        binary = root / "cc-connect-anc"
        build_args = ["go", "build", "-trimpath", "-buildvcs=false", "-o", str(binary),
                      "./cmd/cc-connect"]
        run(build_args, gateway, env)
        manifest = {"created_at": datetime.now(timezone.utc).isoformat(),
                    "sources": sources,
                    "github": evidence, "toolchain": versions, "build": build_args[:-3] + build_args[-1:],
                    "target": f"{target} CGO_ENABLED=0 GOENV=off GOWORK=off GOFLAGS=",
                    "vcs": "exported source; buildvcs=false",
                    "paired_tests": {"crm_sha": crm_sha, "gateway_sha": gateway_sha,
                                     "MYANC_SPIKE_CRM_ROOT": "fresh CRM export", "passed": journeys},
                    "files": {}}
        if knowledge_sha is not None:
            manifest["paired_tests"].update(knowledge_sha=knowledge_sha, MYANC_TEAM_BRAIN_ROOT="fresh knowledge export")
        bundle = root / "bundle"
        bundle.mkdir()
        shutil.copy2(binary, bundle / binary.name)
        shutil.copytree(crm / "myanc_crm", bundle / "myanc_crm",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(crm / "ops", bundle / "ops",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        wiki_root = bundle / 'ops' / mock_wiki.RELATIVE_ROOT
        if wiki_root.exists():
            # The frozen source commit is known only after merge, not in its own tree.
            wiki_source = mock_wiki.manifest(wiki_root, crm_sha)
            (wiki_root / 'SOURCE.json').write_text(
                json.dumps(wiki_source, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        copy_file_runtime_templates(gateway, bundle)
        if knowledge is not None:
            for directory in ("team_brain", "skills"):
                shutil.copytree(knowledge / directory, bundle / "knowledge" / directory,
                                ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            templates = bundle / "knowledge" / "ops"
            templates.mkdir()
            for name in ("team-brain-host.example", "host.example.json"):
                shutil.copy2(knowledge / "ops" / name, templates / name)
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                manifest["files"][path.relative_to(bundle).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        # Recheck after the potentially long build, before publishing the candidate.
        with gate.state_lock():
            gate.check_debt()
            for repo, commit in manifest["sources"].items():
                gate.released(repo, commit)
            if target == "darwin/arm64":
                gate.ci("77AutumN/cc-connect-anc", gateway_sha, "push", required_jobs=MAC_JOBS)
            (bundle / "candidate.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as stream:
                with tarfile.open(fileobj=stream, mode="w:gz") as archive:
                    archive.add(bundle, arcname="candidate")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("crm_sha", type=gate.sha)
    parser.add_argument("gateway_sha", type=gate.sha)
    parser.add_argument("--knowledge-sha", type=gate.sha)
    parser.add_argument("--output", required=True)
    parser.add_argument("--target", choices=TARGETS, default="linux/amd64")
    args = parser.parse_args()
    print(json.dumps(build(args.crm_sha, args.gateway_sha, args.output, args.knowledge_sha, args.target), indent=2))
