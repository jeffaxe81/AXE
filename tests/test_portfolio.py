"""Offline regression tests for the public AXE portfolio collector."""
import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import refresh_portfolio as p


class PortfolioTests(unittest.TestCase):
    def test_all_projects_have_explicit_milestones(self):
        source = pathlib.Path(__file__).resolve().parents[2] / "pages" / "index.html"
        self.assertTrue(source.is_file(), "The gh-pages checkout is required")
        data = p.extract_milestone_progress(source.read_text(encoding="utf-8"))
        self.assertEqual(set(data), set(p.REPOS))
        self.assertTrue(all(0 <= row["completed"] <= row["total"] for row in data.values()))
        self.assertGreater(sum(row["total"] for row in data.values()), 0)

    def test_progress_history_records_only_real_changes(self):
        example = {"crm-vendas": {"completed": 4, "total": 7}}
        first = p.append_progress_history({}, example)
        self.assertEqual(len(first), 1)
        same = p.append_progress_history({"progress_history": first}, example)
        self.assertEqual(len(same), 1)
        changed = {"crm-vendas": {"completed": 5, "total": 7}}
        advanced = p.append_progress_history({"progress_history": same}, changed)
        self.assertEqual(len(advanced), 2)
        self.assertEqual(advanced[0]["projects"], example)
        self.assertEqual(advanced[1]["projects"], changed)

    def test_malformed_input_fails_closed(self):
        with self.assertRaises(ValueError):
            p.extract_milestone_progress('const PROJECTS = [{id:"broken", milestones:[["fake",true]]}];')


    def test_curated_evidence_links_are_bounded(self):
        page = pathlib.Path(__file__).resolve().parents[2] / "pages" / "index.html"
        html = page.read_text(encoding="utf-8")
        progress = p.extract_milestone_progress(html)
        links = p.extract_milestone_links(html, progress)
        self.assertEqual(sum(len(refs) for m in links.values() for refs in m.values()), 15)
        self.assertEqual(links["crm-vendas"]["2"], [{"kind": "pr", "number": 281}])
        self.assertEqual(links["axe-gestao-convites"]["2"], [{"kind": "pr", "number": 1}])

    def test_curated_evidence_link_validation_rejects_bad_data(self):
        progress = {"crm-vendas": {"completed": 0, "total": 2}}
        for payload in (
            '{"crm-vendas":{"2":[{"kind":"pr","number":1}]}}',
            '{"crm-vendas":{"1":[{"kind":"pr","number":0}]}}',
            '{"crm-vendas":{"1":[{"kind":"url","number":5}]}}',
            '{"other":{"0":[{"kind":"pr","number":1}]}}',
            '{"crm-vendas":{"1":[{"kind":"pr","number":1,"url":"https://evil.invalid"}]}}'
        ):
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    p.extract_milestone_links("const MILESTONE_LINKS = " + payload + ";", progress)

    def test_curated_evidence_state_not_equivalent_to_milestone(self):
        from unittest.mock import patch
        mapping = {"crm-vendas": {"0": [{"kind": "pr", "number": 123}]}}
        with patch.object(p, "fetch_tracking", return_value={"kind": "pr", "number": 123,
                    "state": "merged", "verified_at": p.NOW, "error": None}):
            recorded = p.collect_tracking(mapping, {})
            self.assertEqual(recorded["crm-vendas"]["0"][0]["state"], "merged")
        # Tracking enrichment never edits the reviewed percentage.
        self.assertEqual(mapping["crm-vendas"]["0"][0]["kind"], "pr")
        with patch.object(p, "fetch_tracking", side_effect=ValueError("broken")):
            failed = p.collect_tracking(mapping, recorded)
            self.assertEqual(failed["crm-vendas"]["0"][0]["state"], "merged")
            self.assertEqual(failed["crm-vendas"]["0"][0]["error"], "ValueError")


    def test_stage_gate_mapping_covers_each_milestone_once(self):
        import re
        source = pathlib.Path(__file__).resolve().parents[2] / "pages" / "index.html"
        html = source.read_text(encoding="utf-8")
        match = re.search(r'^const GATE_MATRIX = (\{[^\n]+\});$', html, re.M)
        self.assertIsNotNone(match, "Explicit gate mapping is required")
        stages = json.loads(match.group(1))
        progress = p.extract_milestone_progress(html)
        self.assertEqual(set(stages), set(progress))
        for repo, config in stages.items():
            self.assertEqual(set(config), {"dev", "tests", "homolog", "release"})
            all_indices = []
            for category in ("dev", "tests", "homolog", "release"):
                values = config[category]
                self.assertIsInstance(values, list)
                self.assertTrue(all(type(v) is int for v in values))
                all_indices.extend(values)
            self.assertEqual(len(all_indices), progress[repo]["total"])
            self.assertEqual(set(all_indices), set(range(progress[repo]["total"])))


    def test_release_manifest_covers_every_project_with_no_implicit_go(self):
        page = pathlib.Path(__file__).resolve().parents[2] / "pages"
        html = (page / "index.html").read_text(encoding="utf-8")
        progress = p.extract_milestone_progress(html)
        manifest = p.load_release_control(page / "release-approvals.json", html, progress)
        self.assertEqual(set(manifest["projects"]), set(p.REPOS))
        for project in manifest["projects"].values():
            self.assertEqual(set(project["checks"]), set(p.RELEASE_CHECKS))
            self.assertTrue(all(v["status"] == "not_recorded" for v in project["checks"].values()))
            self.assertEqual(project["decisions"], [])

    def test_release_go_requires_real_evidence_and_completed_stage_gates(self):
        import tempfile
        page = pathlib.Path(__file__).resolve().parents[2] / "pages"
        html = (page / "index.html").read_text(encoding="utf-8")
        progress = p.extract_milestone_progress(html)
        base = json.loads((page / "release-approvals.json").read_text(encoding="utf-8"))
        url = "https://github.com/jeffaxe81/crm-vendas/pull/281"
        with tempfile.TemporaryDirectory() as directory:
            location = pathlib.Path(directory) / "release-approvals.json"
            def validate(data):
                location.write_text(json.dumps(data), encoding="utf-8")
                return p.load_release_control(location, html, progress)
            # Explicit NO_GO can be recorded without any automatic green checks.
            denial = json.loads(json.dumps(base))
            denial["projects"]["crm-vendas"]["decisions"].append({
                "outcome": "NO_GO", "reviewer": "github-reviewer",
                "recorded_at": p.NOW, "sha": "a" * 40, "reference": url,
                "reason": "Homologação de produção ainda não foi concluída."
            })
            self.assertEqual(validate(denial)["projects"]["crm-vendas"]["decisions"][0]["outcome"], "NO_GO")
            # A GO statement without evidence must never be accepted.
            unproven = json.loads(json.dumps(denial))
            unproven["projects"]["crm-vendas"]["decisions"][0]["outcome"] = "GO"
            with self.assertRaises(ValueError):
                validate(unproven)
            # Even documented checks cannot override unfinished release milestones.
            proof = json.loads(json.dumps(unproven))
            for entry in proof["projects"]["crm-vendas"]["checks"].values():
                entry.update(status="verified", evidence=url,
                             note="Revisão pública vinculada ao registro de implantação",
                             verified_at=p.NOW)
            with self.assertRaises(ValueError):
                validate(proof)
            wrong = json.loads(json.dumps(proof))
            wrong["projects"]["crm-vendas"]["checks"]["security"]["evidence"] = \
                "https://github.com/other-account/private-repository/pull/1"
            with self.assertRaises(ValueError):
                validate(wrong)
            unknown = json.loads(json.dumps(base))
            unknown["projects"]["crm-vendas"]["checks"].pop("functional")
            with self.assertRaises(ValueError):
                validate(unknown)


    def test_version_history_distinguishes_release_from_tag(self):
        previous={"version_history":{"crm-vendas":[{"version":"v1.0.0","kind":"tag",
            "name":"v1.0.0","sha":"a"*40,"url":"https://github.com/jeffaxe81/crm-vendas/tree/v1.0.0",
            "published_at":None,"prerelease":False,"notes":None,
            "first_seen_at":"2026-09-01T00:00:00Z"}]}}
        versions=[{"version":"v1.0.0","kind":"release","name":"Released v1.0.0",
            "sha":"a"*40,"url":"https://github.com/jeffaxe81/crm-vendas/releases/tag/v1.0.0",
            "published_at":"2026-10-20T12:00:00Z","prerelease":False,"notes":"Shipping"}]
        projects={"crm-vendas":{"versions":versions,"errors":{}}}
        result=p.merge_version_history(previous,projects)
        one=[x for x in result["crm-vendas"] if x["version"]=="v1.0.0"]
        self.assertEqual(len(one),1)
        self.assertEqual(one[0]["kind"],"release")
        self.assertEqual(one[0]["first_seen_at"],"2026-09-01T00:00:00Z")
        stale=p.merge_version_history({"version_history":result},{"crm-vendas":{"versions":[],"errors":{"versions":"HTTPError"}}})
        self.assertEqual(stale["crm-vendas"][0]["version"],"v1.0.0")

    def test_repo_versions_never_publish_drafts_or_invent_release_from_tag(self):
        from unittest.mock import patch
        sample_tags=[{"name":"v0.2.0","commit":{"sha":"a"*40}},
                     {"name":"checkpoint/safe","commit":{"sha":"b"*40}},
                     {"name":"../../private","commit":{"sha":"b"*40}}]
        sample_releases=[{"tag_name":"v0.2.0","name":"Stable","draft":False,"prerelease":False,
                          "html_url":"https://github.com/jeffaxe81/crm-vendas/releases/tag/v0.2.0",
                          "published_at":"2026-10-22T10:30:00Z","body":"Reviewed notes"},
                         {"tag_name":"v3.0.0","name":"Draft","draft":True,"prerelease":False}]
        with patch.object(p,"api", side_effect=[sample_releases,sample_tags]) as api:
            result=p.repo_versions("crm-vendas")
            self.assertEqual(len(result),2)
            self.assertEqual({x["version"]:x["kind"] for x in result},
                             {"v0.2.0":"release","checkpoint/safe":"tag"})
            self.assertIsNone(next(x for x in result if x["kind"]=="tag")["published_at"])
            self.assertTrue(next(x for x in result if x["kind"]=="tag")["url"].endswith("checkpoint%2Fsafe"))
            self.assertEqual(api.call_count,2)

    def test_active_prs_sample_is_bounded_and_validated(self):
        from unittest.mock import patch
        repo="crm-vendas"
        valid={"number":25,"title":"Test feature","state":"open","updated_at":"2026-10-22T12:00:00Z",
               "html_url":"https://github.com/jeffaxe81/crm-vendas/pull/25","draft":False}
        malformed=dict(valid,number=26,html_url="https://evil.invalid/pull/26")
        with patch.object(p,"api",side_effect=[[],[valid,malformed]]) as mock:
            result=p.prs(repo)
            self.assertEqual(result["active_sample_size"],1)
            self.assertEqual(result["active"][0]["number"],25)
            self.assertEqual(result["open"],0)
            self.assertEqual(mock.call_count,2)


    def test_test_counter_parses_actual_runner_summaries(self):
        cases = [
            ("2026-10-23T06:14:37.8703874Z 393 passed in 2.79s", (393, 0, 0, 1)),
            ("\x1b[2m      Tests \x1b[22m \x1b[32m1366 passed\x1b[39m (1366)", (1366, 0, 0, 1)),
            ("Tests:       526 passed, 2 failed, 3 skipped, 531 total", (526, 2, 3, 1)),
            ("  Tests 112 passed | 1 skipped (113)", (112, 0, 1, 1)),
            ("  2 failed, 127 passed, 1 skipped in 0.55s", (127, 2, 1, 1)),
            ("Ran 17 tests in 0.523s\n\nOK", (17, 0, 0, 1)),
            ("Ran 9 tests in 0.004s\nFAILED (failures=1, errors=1)", (7, 2, 0, 1)),
            (" Test Files 298 passed (298)\nTesting 7 passed tickets", (0, 0, 0, 0)),
        ]
        for log, expected in cases:
            with self.subTest(log=log):
                result = p.test_counts_from_log(log)
                self.assertEqual((result["passed"], result["failed"], result["skipped"],
                                  result["summaries"]), expected)

    def test_test_counter_does_not_claim_success_without_evidence(self):
        from unittest.mock import patch
        ci = {"id": 765, "name": "Quality", "status": "completed",
              "conclusion": "failure", "updated_at": "2026-10-23T06:14:37Z"}
        with patch.object(p, "api", return_value={"jobs": [
            {"name": "quality", "status": "completed", "id": 1234},
            {"name": "deploy", "status": "completed", "id": 4567},
        ]}), patch.object(p, "fetch_job_text", return_value="Tests: 12 passed, 2 failed, 14 total"):
            measured = p.collect_test_counts("dispatch", ci, None)
            self.assertEqual(measured["passed"], 12)
            self.assertEqual(measured["failed"], 2)
            self.assertEqual(measured["skipped"], 0)
            self.assertEqual(measured["scanned_jobs"], 1)
            self.assertEqual(measured["run_conclusion"], "failure")
        with patch.object(p, "api", side_effect=AssertionError("Cached run must not hit network")):
            self.assertEqual(p.collect_test_counts("dispatch", ci, measured)["run_id"], 765)
        with patch.object(p, "api", return_value={"jobs": [
            {"name": "pytest", "status": "completed", "id": 123}
        ]}), patch.object(p, "fetch_job_text", side_effect=ValueError("Unavailable")):
            empty = p.collect_test_counts("dispatch", ci, None)
            self.assertEqual(empty["status"], "no_summary")
            self.assertIsNone(empty["passed"])
            self.assertTrue(empty["partial"])

    def test_history_only_adds_distinct_verified_runs(self):
        record = {"run_id": 123, "status": "available", "passed": 17,
                  "failed": 0, "skipped": 0, "parser_version": p.TEST_PARSER_VERSION}
        rows = {"crm-vendas": {"tests": record, "errors": {}}}
        initial = p.append_test_history({}, rows)
        self.assertEqual(len(initial["crm-vendas"]), 1)
        repeat = p.append_test_history({"test_history": initial}, rows)
        self.assertEqual(len(repeat["crm-vendas"]), 1)
        self.assertEqual(repeat["crm-vendas"][0]["first_seen_at"], initial["crm-vendas"][0]["first_seen_at"])
        rows["crm-vendas"]["errors"]["tests"] = "HTTPError"
        errors = p.append_test_history({"test_history": initial}, rows)
        self.assertEqual(len(errors["crm-vendas"]), 1)


if __name__ == "__main__":
    unittest.main()
