"""Offline regression tests for AXE automatic snapshot recovery."""
import datetime as dt
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import portfolio_watchdog as w


class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.now = dt.datetime(2026, 10, 24, 20, 0, tzinfo=dt.timezone.utc)
        self.calls = []

    def snap(self, age_min):
        return {"schema_version": 1, "owner": "jeffaxe81",
                "projects": {str(i): {} for i in range(9)},
                "generated_at": (self.now - dt.timedelta(minutes=age_min))
                .isoformat().replace("+00:00", "Z")}

    def run_watchdog(self, original=None, runs=None, incoming=None, attempts=3):
        incoming = list(incoming or [])
        def get_runs():
            self.calls.append("check_runs")
            return runs or []
        def dispatch():
            self.calls.append("dispatch")
        def fetch(attempt):
            self.calls.append("fetch")
            return incoming.pop(0) if incoming else self.snap(45)
        def sleep(seconds):
            self.calls.append("sleep")
        return w.recover(original if original is not None else self.snap(45),
                         now=lambda: self.now, get_runs=get_runs,
                         dispatch=dispatch, fetch_snapshot=fetch,
                         sleep=sleep, attempts=attempts)

    def test_tenth_project_must_be_fomento_and_is_accepted(self):
        legacy = self.snap(2)
        promoted = dict(legacy)
        promoted["projects"] = {**legacy["projects"], "axe-fomento": {}}
        self.assertEqual(w.age_seconds(promoted, self.now), 2 * 60)
        fake = dict(legacy)
        fake["projects"] = {**legacy["projects"], "other-project": {}}
        with self.assertRaises(w.RecoveryError):
            w.age_seconds(fake, self.now)
        eleven = dict(promoted)
        eleven["projects"] = {**promoted["projects"], "another": {}}
        with self.assertRaises(w.RecoveryError):
            w.age_seconds(eleven, self.now)

    def test_fresh_snapshot_skips_recovery(self):
        _, state = self.run_watchdog(original=self.snap(2))
        self.assertEqual(state, "fresh")
        self.assertEqual(self.calls, [])

    def test_recovery_waits_for_real_new_publication(self):
        result, state = self.run_watchdog(incoming=[self.snap(45), self.snap(1)])
        self.assertEqual(state, "recovered")
        self.assertEqual(result["generated_at"], self.snap(1)["generated_at"])
        self.assertEqual(self.calls.count("dispatch"), 1)
        self.assertEqual(self.calls.count("fetch"), 2)

    def test_recent_inflight_prevents_duplicate(self):
        active = [{"status": "in_progress", "head_branch": "main",
                   "created_at": self.snap(5)["generated_at"]}]
        _, state = self.run_watchdog(runs=active, incoming=[self.snap(1)])
        self.assertEqual(state, "recovered")
        self.assertNotIn("dispatch", self.calls)

    def test_old_queued_workflow_does_not_block(self):
        queued = [{"status": "queued", "head_branch": "main",
                   "created_at": self.snap(50)["generated_at"]}]
        self.run_watchdog(runs=queued, incoming=[self.snap(1)])
        self.assertEqual(self.calls.count("dispatch"), 1)

    def test_other_branch_is_not_our_recovery(self):
        other = [{"status": "queued", "head_branch": "dev",
                  "created_at": self.snap(1)["generated_at"]}]
        self.run_watchdog(runs=other, incoming=[self.snap(1)])
        self.assertEqual(self.calls.count("dispatch"), 1)

    def test_unrecovered_stale_snapshot_fails(self):
        with self.assertRaisesRegex(w.RecoveryError, "ainda antigo"):
            self.run_watchdog(attempts=2)
        self.assertEqual(self.calls.count("dispatch"), 1)

    def test_threshold_is_inclusive(self):
        self.assertEqual(self.run_watchdog(original=self.snap(20))[1], "fresh")

    def test_future_snapshot_is_rejected(self):
        with self.assertRaisesRegex(w.RecoveryError, "futura"):
            self.run_watchdog(original=self.snap(-10))

    def test_invalid_snapshots_are_rejected(self):
        for sample in ({}, {"schema_version": 1, "owner": "wrong", "projects": {}},
                       {"schema_version": 1, "owner": "jeffaxe81",
                        "projects": {str(i): {} for i in range(9)}, "generated_at": "broken"}):
            with self.subTest(sample=sample), self.assertRaises(w.RecoveryError):
                w.age_seconds(sample, self.now)

    def test_malformed_workflows_are_rejected(self):
        with self.assertRaisesRegex(w.RecoveryError, "inválida"):
            w.inflight_recent({}, self.now)

    def test_unchanged_snapshot_does_not_claim_success(self):
        with self.assertRaises(w.RecoveryError):
            self.run_watchdog(incoming=[self.snap(45)], attempts=1)


if __name__ == "__main__":
    unittest.main()
