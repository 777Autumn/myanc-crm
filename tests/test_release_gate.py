import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("release_gate", Path(__file__).parents[1] / "ops/release_gate.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.repo = "77AutumN/cc-connect-anc"
        self.sha = "a" * 40
        self.run = dict(head_sha=self.sha, head_branch="main", path=gate.WORKFLOW, event="push",
                        status="completed", conclusion="success")
        self.jobs = [dict(name=name, status="completed", conclusion="success")
                     for name in gate.REPOS[self.repo]]

    def test_complete_exact_run_passes(self):
        gate.validate_run(self.repo, self.sha, "push", self.run, self.jobs)

    def test_native_candidate_cannot_substitute_linux_only_or_skipped_ci(self):
        required = ("mac-codex (ubuntu-latest)", "mac-codex (macos-latest)")
        with self.assertRaises(ValueError):
            gate.validate_run(self.repo, self.sha, "push", self.run, self.jobs, required)
        jobs = self.jobs + [dict(name=name, status="completed", conclusion="success") for name in required]
        gate.validate_run(self.repo, self.sha, "push", self.run, jobs, required)
        for outcome in ("skipped", "failure", None):
            with self.assertRaises(ValueError):
                gate.validate_run(self.repo, self.sha, "push", self.run,
                                  jobs[:-1] + [dict(jobs[-1], conclusion=outcome)], required)
        with self.assertRaises(ValueError):
            gate.validate_run(self.repo, self.sha, "push", self.run, jobs[1:], required)

    def test_knowledge_requires_all_four_exact_matrix_jobs(self):
        repo = "77AutumN/myanc-team-brain"
        jobs = [dict(name=f"test ({os_name}, {python})", status="completed", conclusion="success")
                for os_name in ("ubuntu-latest", "windows-latest") for python in ("3.11", "3.13")]
        gate.validate_run(repo, self.sha, "push", self.run, jobs)
        for missing in range(4):
            with self.assertRaises(ValueError):
                gate.validate_run(repo, self.sha, "push", self.run, jobs[:missing] + jobs[missing + 1:])
        for changed in ({"name": "test"}, {"conclusion": "skipped"}, {"conclusion": "failure"}):
            with self.assertRaises(ValueError):
                gate.validate_run(repo, self.sha, "push", self.run, [dict(jobs[0], **changed), *jobs[1:]])

    def test_explicit_source_mapping_supports_legacy_and_three_repositories(self):
        old = {"77AutumN/myanc-crm": "a" * 40, "77AutumN/cc-connect-anc": "b" * 40}
        self.assertEqual(gate.source_commits("a" * 40, "b" * 40), old)
        self.assertEqual(gate.source_commits("a" * 40, "b" * 40, "c" * 40),
                         {**old, "77AutumN/myanc-team-brain": "c" * 40})
        with self.assertRaises(ValueError):
            gate.source_commits("a" * 40, "b" * 40, "")

    def test_three_source_incident_cannot_be_closed_with_two_source_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = root / "state.json"
            record.write_text(json.dumps(dict(version=1, reconciliation="audit", incidents=[])), encoding="utf-8")
            evidence = root / "evidence.json"
            opened = dict(id="synthetic", owner_approval="explicit fixture approval", audit_reference="fixture",
                          crm_sha="a" * 40, gateway_sha="b" * 40, knowledge_sha="c" * 40,
                          candidate_sha256="d" * 64, validation="fixture", backup="fixture")
            evidence.write_text(json.dumps(opened), encoding="utf-8")
            with patch.object(gate, "STATE", record), patch.object(gate, "released", return_value={}) as released:
                gate.state_change("open", evidence)
                mappings = {repo: dict(original=sha, merged="e" * 40, evidence="audited")
                            for repo, sha in gate.source_commits("a" * 40, "b" * 40).items()}
                resolution = dict(id="synthetic", owner_approval="explicit", audit_reference="fixture", mappings=mappings)
                evidence.write_text(json.dumps(resolution), encoding="utf-8")
                with self.assertRaises(ValueError):
                    gate.state_change("close", evidence)
                self.assertEqual(gate.read_state()["incidents"][0]["status"], "open")
                mappings["77AutumN/myanc-team-brain"] = dict(original="c" * 40, merged="f" * 40, evidence="audited")
                evidence.write_text(json.dumps(resolution), encoding="utf-8")
                self.assertEqual(gate.state_change("close", evidence)["incidents"][0]["status"], "closed")
                released.assert_any_call("77AutumN/myanc-team-brain", "f" * 40)

    def test_stale_sha_wrong_workflow_event_or_incomplete_run_rejected(self):
        for key, value in [("head_sha", "b" * 40), ("path", ".github/workflows/stale.yml"),
                           ("event", "schedule"), ("status", "in_progress"),
                           ("conclusion", "failure")]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                gate.validate_run(self.repo, self.sha, "push", dict(self.run, **{key: value}), self.jobs)

    def test_missing_skipped_pending_failed_and_duplicate_jobs_rejected(self):
        variants = [self.jobs[:-1], self.jobs + [self.jobs[0]]]
        for outcome in ("skipped", "failure", None):
            jobs = copy.deepcopy(self.jobs)
            jobs[0]["conclusion"] = outcome
            variants.append(jobs)
        for jobs in variants:
            with self.subTest(jobs=jobs), self.assertRaises(ValueError):
                gate.validate_run(self.repo, self.sha, "push", self.run, jobs)

    def test_query_failure_propagates(self):
        with patch.object(gate, "api", side_effect=RuntimeError("offline")):
            with self.assertRaises(RuntimeError):
                gate.ci(self.repo, self.sha, "push")

    def test_unmerged_commit_rejected(self):
        with patch.object(gate, "pages", return_value=[]):
            with self.assertRaises(ValueError):
                gate.released(self.repo, self.sha)

    def test_missing_corrupt_or_unresolved_state_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            with patch.object(gate, "STATE", state):
                with self.assertRaises(FileNotFoundError):
                    gate.ordinary_allowed()
                state.write_text("broken", encoding="utf-8")
                with self.assertRaises(ValueError):
                    gate.ordinary_allowed()
                state.write_text(json.dumps(dict(version=1, reconciliation="audit", incidents=[
                    dict(id="incident", status="open")])), encoding="utf-8")
                with self.assertRaises(ValueError):
                    gate.ordinary_allowed()

    def test_head_changed_after_checks_rejected(self):
        pr = dict(head=dict(sha=self.sha), base=dict(sha="b" * 40, ref="main",
                  repo=dict(full_name=self.repo)), state="open", draft=False)
        changed = copy.deepcopy(pr)
        changed["head"]["sha"] = "c" * 40
        with patch.object(gate, "api", side_effect=[pr, {"sha": "b" * 40}, changed]), \
             patch.object(gate, "review"), patch.object(gate, "ci"):
            with self.assertRaises(ValueError):
                gate.merge_check(self.repo, 1, "external-review.json", True)

    def test_new_failed_run_does_not_use_previous_green(self):
        with patch.object(gate, "pages", side_effect=[[{"id": 1}, {"id": 2}], self.jobs]), \
             patch.object(gate, "api", return_value=dict(self.run, id=2, run_attempt=1,
                                                        conclusion="failure")):
            with self.assertRaises(ValueError):
                gate.ci(self.repo, self.sha, "push")

    def test_existing_lock_blocks_even_with_clear_state(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state.json"
            state.write_text(json.dumps(dict(version=1, reconciliation="audit", incidents=[])), encoding="utf-8")
            with patch.object(gate, "STATE", state):
                with gate.state_lock():
                    with self.assertRaises(FileExistsError):
                        gate.ordinary_allowed()
                state.with_suffix(".lock").write_text("crashed writer", encoding="utf-8")
                with self.assertRaises(FileExistsError):
                    gate.ordinary_allowed()


if __name__ == "__main__":
    unittest.main()
