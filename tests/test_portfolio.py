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
        self.assertEqual(sum(len(refs) for m in links.values() for refs in m.values()), 10)
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


if __name__ == "__main__":
    unittest.main()
