"""Build a candidate from two merged SHAs; never install or contact the VPS."""
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


def run(args, cwd, env=None):
    if os.name == "nt" and args[0] == "pnpm":
        args = ["pnpm.cmd", *args[1:]]
    subprocess.run(args, cwd=cwd, env=env, check=True)


def build_environment(crm):
    env = os.environ.copy()
    for name in ("GOOS", "GOARCH", "CGO_ENABLED", "GOFLAGS", "GOWORK", "GOENV"):
        env.pop(name, None)
    env.update(GOENV="off", GOWORK="off", GOFLAGS="", MYANC_SPIKE_CRM_ROOT=str(crm))
    return env


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
        run(["git", "archive", "--format=tar", f"--output={archive}", commit], scratch)
        with tarfile.open(archive) as source:
            for member in source.getmembers():
                target = (destination / member.name).resolve()
                gate.require(target.is_relative_to(destination.resolve())
                             and not member.issym() and not member.islnk()
                             and (member.isfile() or member.isdir()), "unsafe source archive")
            source.extractall(destination, filter="data")


def build(crm_sha, gateway_sha, output):
    output = Path(output).resolve()
    gate.require(not output.exists(), "candidate output already exists")
    gate.ordinary_allowed()
    evidence = {repo: gate.released(repo, commit) for repo, commit in
                zip(gate.REPOS, (crm_sha, gateway_sha))}
    versions = {name: gate.command("pnpm.cmd" if os.name == "nt" and name == "pnpm" else name, *args) for name, args in
                (("go", ("version",)), ("node", ("--version",)), ("pnpm", ("--version",)),
                 ("python", ("--version",)))}
    gate.require(versions["pnpm"].startswith("10."), "pnpm 10 required")
    with tempfile.TemporaryDirectory(prefix="vps-candidate-") as scratch:
        root = Path(scratch)
        crm, gateway = root / "crm", root / "gateway"
        export("77AutumN/myanc-crm", crm_sha, crm)
        export("77AutumN/cc-connect-anc", gateway_sha, gateway)
        # No worktree or pre-existing ignored web assets are consulted.
        run(["pnpm", "install", "--frozen-lockfile"], gateway / "web")
        run(["pnpm", "build"], gateway / "web")
        env = build_environment(crm)
        run(["go", "mod", "verify"], gateway, env)
        run(["python", "-m", "unittest", "discover", "-s", "tests"], crm, env)
        run(["python", "-m", "unittest", "discover", "-s", "spikes"], crm, env)
        run(["go", "test", "./actionhost/crmfollowup", "./core", "-run",
             "TestCUJ|Test.*Journey", "-count=1", "-v"], gateway, env)
        env.update(GOOS="linux", GOARCH="amd64", CGO_ENABLED="0")
        binary = root / "cc-connect-anc"
        build_args = ["go", "build", "-trimpath", "-buildvcs=false", "-o", str(binary),
                      "./cmd/cc-connect"]
        run(build_args, gateway, env)
        manifest = {"created_at": datetime.now(timezone.utc).isoformat(),
                    "sources": dict(zip(gate.REPOS, (crm_sha, gateway_sha))),
                    "github": evidence, "toolchain": versions, "build": build_args[:-3] + build_args[-1:],
                    "target": "linux/amd64 CGO_ENABLED=0 GOENV=off GOWORK=off GOFLAGS=",
                    "vcs": "exported source; buildvcs=false",
                    "paired_tests": {"crm_sha": crm_sha, "gateway_sha": gateway_sha,
                                     "MYANC_SPIKE_CRM_ROOT": "fresh CRM export", "passed": True},
                    "files": {}}
        bundle = root / "bundle"
        bundle.mkdir()
        shutil.copy2(binary, bundle / binary.name)
        shutil.copytree(crm / "myanc_crm", bundle / "myanc_crm",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(crm / "ops", bundle / "ops",
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                manifest["files"][path.relative_to(bundle).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        # Recheck after the potentially long build, before publishing the candidate.
        with gate.state_lock():
            gate.check_debt()
            for repo, commit in manifest["sources"].items():
                gate.released(repo, commit)
            (bundle / "candidate.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("xb") as target:
                with tarfile.open(fileobj=target, mode="w:gz") as archive:
                    archive.add(bundle, arcname="candidate")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("crm_sha", type=gate.sha)
    parser.add_argument("gateway_sha", type=gate.sha)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.crm_sha, args.gateway_sha, args.output), indent=2))
