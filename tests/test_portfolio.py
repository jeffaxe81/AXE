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


if __name__ == "__main__":
    unittest.main()
