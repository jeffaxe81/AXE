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


if __name__ == "__main__":
    unittest.main()
