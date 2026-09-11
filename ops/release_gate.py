"""Fail-closed GitHub delivery checks. No VPS access or installation capability."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from contextlib import contextmanager
from pathlib import Path

REPOS = {
    "77AutumN/myanc-crm": {"test"},
    "77AutumN/cc-connect-anc": {
        "lint", "unit-test", "smoke-test", "regression-test", "performance-test"
    },
    "77AutumN/myanc-team-brain": {
        f"test ({runner}, {python})"
        for runner in ("ubuntu-latest", "windows-latest") for python in ("3.11", "3.13")
    },
}
WORKFLOW = ".github/workflows/ci.yml"
STATE = Path("D:/MYANC/.release-state/state.json")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(value):
    require(bool(re.fullmatch(r"[0-9a-f]{40}", value)), "full commit SHA required")
    return value


def source_commits(crm_sha, gateway_sha, knowledge_sha=None):
    sources = {"77AutumN/myanc-crm": sha(crm_sha), "77AutumN/cc-connect-anc": sha(gateway_sha)}
    if knowledge_sha is not None:
        sources["77AutumN/myanc-team-brain"] = sha(knowledge_sha)
    return sources


def command(*args):
    return subprocess.check_output(args, text=True, encoding="utf-8").strip()


def api(path):
    # A failed API request raises; absence is never interpreted as success.
    return json.loads(command("gh", "api", path))


def pages(path, field):
    result = []
    for page in range(1, 101):
        data = api(f"{path}{'&' if '?' in path else '?'}per_page=100&page={page}")
        items = data[field] if field else data
        require(isinstance(items, list), "malformed GitHub collection")
        result.extend(items)
        if len(items) < 100:
            return result
    raise ValueError("GitHub pagination exceeded safe bound")


def validate_run(repo, commit, event, run, jobs):
    require(repo in REPOS, "repository is not supported")
    require(run.get("head_sha") == sha(commit), "CI SHA mismatch")
    require(run.get("path") == WORKFLOW, "wrong workflow")
    require(run.get("event") == event, "wrong CI event")
    if event == "push":
        require(run.get("head_branch") == "main", "push CI is not for main")
    require(run.get("status") == "completed" and run.get("conclusion") == "success",
            "CI is incomplete or unsuccessful")
    names = [job.get("name") for job in jobs]
    for name in REPOS[repo]:
        require(names.count(name) == 1, f"missing or duplicate required job: {name}")
        job = next(job for job in jobs if job.get("name") == name)
        require(job.get("status") == "completed" and job.get("conclusion") == "success",
                f"required job is not successful: {name}")
    require(all(job.get("status") == "completed" and job.get("conclusion") == "success"
                for job in jobs), "incomplete or skipped check in CI job set")


def ci(repo, commit, event, pr_number=None, base=None):
    require(repo in REPOS, "repository is not supported")
    sha(commit)
    runs = pages(f"repos/{repo}/actions/workflows/ci.yml/runs?head_sha={commit}&event={event}",
                 "workflow_runs")
    if pr_number is not None:
        runs = [run for run in runs if any(pr.get("number") == pr_number
                                          for pr in run.get("pull_requests", []))]
    require(bool(runs), "no matching CI run")
    latest = max(runs, key=lambda run: run["id"])
    # Fetch again to observe reruns of the latest run, not an old green attempt.
    run = api(f"repos/{repo}/actions/runs/{latest['id']}")
    if base is not None:
        require(any(pr.get("number") == pr_number and pr.get("base", {}).get("sha") == base
                    for pr in run.get("pull_requests", [])), "CI base mismatch")
    attempt = run["run_attempt"]
    jobs = pages(f"repos/{repo}/actions/runs/{run['id']}/attempts/{attempt}/jobs", "jobs")
    validate_run(repo, commit, event, run, jobs)
    current = api(f"repos/{repo}/actions/runs/{run['id']}")
    require(current.get("run_attempt") == attempt and current.get("status") == "completed"
            and current.get("conclusion") == "success", "CI changed while checking")
    return {"run_id": run["id"], "attempt": attempt, "url": run["html_url"], "sha": commit}


def review(path, repo, head, base):
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    require(record.get("repo") == repo and record.get("head") == head
            and record.get("base") == base, "review binding mismatch")
    axes = record.get("reviews", [])
    require({item.get("axis") for item in axes} == {"spec", "standards"}
            and len(axes) == 2, "both review axes required")
    require(len({item.get("reviewer") for item in axes}) == 2, "independent reviewers required")
    require(all(item.get("reviewer") and item.get("evidence")
                and item.get("result") == "pass" for item in axes), "review not passed")
    return record


def merge_check(repo, number, review_file, merge=False):
    require(repo in REPOS, "repository is not supported")
    endpoint = f"repos/{repo}/pulls/{number}"
    pr = api(endpoint)
    head, base = pr["head"]["sha"], pr["base"]["sha"]
    require(pr["base"]["ref"] == "main" and pr["base"]["repo"]["full_name"] == repo,
            "wrong merge target")
    require(pr["state"] == "open" and not pr["draft"], "PR is not ready")
    require(api(f"repos/{repo}/commits/main")["sha"] == base, "base must be refreshed")
    review(review_file, repo, head, base)
    evidence = ci(repo, head, "pull_request", number, base)
    again = api(endpoint)
    require(again["head"]["sha"] == head and again["base"]["sha"] == base,
            "PR changed after review/checks")
    require(api(f"repos/{repo}/commits/main")["sha"] == base, "main changed after checks")
    if merge:
        command("gh", "pr", "merge", str(number), "--repo", repo, "--squash",
                "--match-head-commit", head)
    return evidence


def released(repo, commit):
    require(repo in REPOS, "repository is not supported")
    sha(commit)
    pulls = pages(f"repos/{repo}/commits/{commit}/pulls", None)
    matches = [pr for pr in pulls if pr.get("merged_at") and pr.get("merge_commit_sha") == commit
               and pr["base"]["ref"] == "main" and pr["base"]["repo"]["full_name"] == repo]
    require(len(matches) == 1, "commit is not an unambiguous merged main PR")
    comparison = api(f"repos/{repo}/compare/{commit}...main")
    require(comparison["status"] in ("ahead", "identical"), "commit is not on current main")
    return {"pr": matches[0]["html_url"], "ci": ci(repo, commit, "push")}


def read_state():
    record = json.loads(STATE.read_text(encoding="utf-8"))
    require(record.get("version") == 1 and record.get("reconciliation"), "state not initialized")
    require(isinstance(record.get("incidents"), list), "invalid incident ledger")
    for item in record["incidents"]:
        require(item.get("id") and item.get("status") in ("open", "closed"), "invalid incident")
    return record


def check_debt():
    record = read_state()
    require(not any(item["status"] != "closed" for item in record["incidents"]),
            "unresolved emergency release blocks ordinary release")


@contextmanager
def state_lock():
    lock = STATE.with_suffix(".lock")
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        yield
    finally:
        os.close(descriptor)
        lock.unlink()


def ordinary_allowed():
    with state_lock():
        check_debt()


def state_change(action, evidence_file):
    """Explicit operator action, serialized across worktrees; no expiry unlock."""
    evidence = json.loads(Path(evidence_file).read_text(encoding="utf-8"))
    require(evidence.get("owner_approval") and evidence.get("audit_reference"),
            "explicit Owner approval and audit reference required")
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with state_lock():
        if action == "initialize":
            require(not STATE.exists(), "state already exists")
            require(evidence.get("reconciliation"), "completed reconciliation required")
            record = {"version": 1, "reconciliation": evidence, "incidents": []}
        else:
            record = read_state()
            incident_id = evidence.get("id")
            require(isinstance(incident_id, str) and incident_id.strip(), "incident id required")
            if action == "open":
                require(not any(item["id"] == incident_id for item in record["incidents"]),
                        "incident already recorded")
                source_commits(evidence.get("crm_sha", ""), evidence.get("gateway_sha", ""), evidence.get("knowledge_sha"))
                require("knowledge_sha" not in evidence or evidence["knowledge_sha"] is not None,
                        "knowledge SHA cannot be null")
                require(bool(re.fullmatch(r"[0-9a-f]{64}", evidence.get("candidate_sha256", ""))),
                        "frozen candidate digest required")
                require(evidence.get("validation") and evidence.get("backup"),
                        "validation and backup evidence required")
                record["incidents"].append(dict(evidence, status="open"))
            else:
                items = [item for item in record["incidents"] if item["id"] == incident_id]
                require(len(items) == 1 and items[0]["status"] == "open", "open incident not found")
                item = items[0]
                mappings = evidence.get("mappings", {})
                originals = source_commits(item["crm_sha"], item["gateway_sha"], item.get("knowledge_sha"))
                require(set(mappings) == set(originals), "all and only original source mappings required")
                for repo, original in originals.items():
                    mapping = mappings.get(repo, {})
                    require(mapping.get("original") == original and mapping.get("evidence"),
                            "original-to-merged mapping evidence required")
                    mapping["github"] = released(repo, mapping.get("merged", ""))
                item.update(status="closed", resolution=evidence)
        record["updated_at"] = datetime.now(timezone.utc).isoformat()
        temporary = STATE.with_suffix(".new")
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, STATE)
        return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    check = sub.add_parser("merge")
    check.add_argument("repo", choices=REPOS)
    check.add_argument("number", type=int)
    check.add_argument("--review", required=True, help="external SHA-bound review JSON")
    check.add_argument("--execute", action="store_true", help="squash merge after checks")
    release = sub.add_parser("release")
    release.add_argument("crm_sha", type=sha)
    release.add_argument("gateway_sha", type=sha)
    release.add_argument("--knowledge-sha", type=sha)
    state = sub.add_parser("state")
    state.add_argument("operation", choices=("initialize", "open", "close"))
    state.add_argument("--evidence", required=True)
    args = parser.parse_args()
    if args.action == "merge":
        result = merge_check(args.repo, args.number, args.review, args.execute)
    elif args.action == "state":
        result = state_change(args.operation, args.evidence)
    else:
        ordinary_allowed()
        result = {repo: released(repo, commit) for repo, commit in
                  source_commits(args.crm_sha, args.gateway_sha, args.knowledge_sha).items()}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
