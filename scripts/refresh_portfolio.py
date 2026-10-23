#!/usr/bin/env python3
"""Build a public, safely bounded GitHub portfolio snapshot for GitHub Pages."""
import argparse
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

OWNER = "jeffaxe81"
REPOS = (
    "crm-vendas", "dispatch", "pabx-mvp", "axe-voice-desktop",
    "dispatch-v2", "centralizador-controle", "aderencia_tecnica",
    "axe-gestao-convites", "central-despacho-alertas-publicacao",
)
NOW = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def request_json(url):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "axe-delivery-hub-snapshot",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=22) as r:
                return json.load(r)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 * (attempt + 1))


def api(repo, path):
    return request_json("https://api.github.com/repos/" + OWNER + "/" + urllib.parse.quote(repo) + "/" + path)


def short(value, length=160):
    return str(value or "").split("\n", 1)[0][:length]


def commits(repo):
    data = api(repo, "commits?sha=main&per_page=100")
    if not isinstance(data, list):
        raise ValueError("Invalid commit response")
    result = []
    for c in data:
        if not isinstance(c, dict) or not isinstance(c.get("sha"), str) or not re.fullmatch(r"[0-9a-fA-F]{40}", c["sha"]):
            continue
        info = c.get("commit") or {}
        stamp = (info.get("committer") or {}).get("date")
        if not isinstance(stamp, str) or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", stamp):
            continue
        result.append({"sha": c["sha"].lower(), "date": stamp[:10],
                       "committed_at": stamp, "title": short(info.get("message"))})
    return result


def prs(repo):
    """Sample recent PRs and independently fetch current open work.

    The legacy open/merged/closed counts retain their meaning: last 20 updates.
    """
    data = api(repo, "pulls?state=all&sort=updated&direction=desc&per_page=20")
    if not isinstance(data, list):
        raise ValueError("Invalid PR response")
    active = api(repo, "pulls?state=open&sort=updated&direction=desc&per_page=12")
    if not isinstance(active, list):
        raise ValueError("Invalid open PR response")
    entries = []
    for item in active:
        number, url = item.get("number"), item.get("html_url")
        if (type(number) is not int or number <= 0 or
            url != "https://github.com/" + OWNER + "/" + repo + "/pull/" + str(number) or
            item.get("state") != "open" or not isinstance(item.get("updated_at"), str)):
            continue
        entries.append({
            "number": number, "title": short(item.get("title"), 150),
            "url": url, "updated_at": short(item["updated_at"], 35),
            "draft": bool(item.get("draft", False)),
        })
    return {
        "open": sum(p.get("state") == "open" for p in data),
        "merged": sum(bool(p.get("merged_at")) for p in data),
        "closed": sum(p.get("state") == "closed" and not p.get("merged_at") for p in data),
        "sample_size": len(data),
        "active": entries,
        "active_sample_size": len(entries),
        "active_limit": 12,
        "recent": [{
            "number": p["number"],
            "updated_at": p["updated_at"],
            "state": "merged" if p.get("merged_at") else p.get("state"),
            "url": "https://github.com/" + OWNER + "/" + repo + "/pull/" + str(p["number"]),
        } for p in data if isinstance(p, dict) and type(p.get("number")) is int and p["number"] > 0
          and isinstance(p.get("updated_at"), str)
          and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", p["updated_at"])],
        "recent_limit": 20,
        "latest": ({
            "number": data[0].get("number"), "title": short(data[0].get("title")),
            "state": "merged" if data[0].get("merged_at") else data[0].get("state"),
            "url": data[0].get("html_url"), "updated_at": data[0].get("updated_at"),
        } if data else None),
    }


def ci(repo):
    data = api(repo, "actions/runs?branch=main&per_page=1")
    if not isinstance(data, dict) or not isinstance(data.get("workflow_runs"), list):
        raise ValueError("Invalid workflow response")
    if not data["workflow_runs"]:
        return None
    r = data["workflow_runs"][0]
    return {
        "id": r.get("id"), "name": short(r.get("name"), 120), "status": short(r.get("status"), 40),
        "conclusion": short(r.get("conclusion"), 40),
        "url": short(r.get("html_url"), 300), "updated_at": short(r.get("updated_at"), 35),
        "head_sha": r.get("head_sha") if isinstance(r.get("head_sha"), str) and re.fullmatch(r"[0-9a-f]{40}", r["head_sha"]) else None,
    }



RELEASE_TAG_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,99}$")


def valid_tag_name(name):
    return isinstance(name, str) and bool(RELEASE_TAG_PATTERN.fullmatch(name)) and ".." not in name


def repo_versions(repo):
    """GitHub Releases and git tags are different. Never equate tag to published release."""
    releases = api(repo, "releases?per_page=20")
    tags = api(repo, "tags?per_page=30")
    if not isinstance(releases, list) or not isinstance(tags, list):
        raise ValueError("GitHub version endpoints must return arrays")
    rows = {}
    for tag in tags:
        name = tag.get("name")
        sha = (tag.get("commit") or {}).get("sha")
        if not valid_tag_name(name) or not isinstance(sha, str) or not re.fullmatch(r"[a-fA-F0-9]{40}", sha):
            continue
        rows[name] = {"version": name, "kind": "tag",
                      "name": name, "sha": sha.lower(),
                      "url": "https://github.com/" + OWNER + "/" + repo + "/tree/" +
                        urllib.parse.quote(name, safe=""),
                      "published_at": None, "prerelease": False,
                      "notes": None}
    for release in releases:
        name = release.get("tag_name")
        if release.get("draft") or not valid_tag_name(name):
            continue
        canonical = "https://github.com/" + OWNER + "/" + repo + "/releases/tag/" + urllib.parse.quote(name, safe="")
        if release.get("html_url") != canonical or not isinstance(release.get("published_at"), str):
            continue
        rows[name] = {"version": name, "kind": "release",
                      "name": short(release.get("name") or name, 100),
                      "sha": rows.get(name, {}).get("sha"),
                      "url": canonical, "published_at": short(release["published_at"], 35),
                      "prerelease": bool(release.get("prerelease")),
                      "notes": short(release.get("body"), 220) or None}
    return list(rows.values())


def merge_version_history(old, projects):
    """Maintain first-observed version records across collection windows."""
    historical = old.get("version_history", {}) if isinstance(old, dict) else {}
    historical = historical if isinstance(historical, dict) else {}
    result = {}
    for repo in REPOS:
        previous = historical.get(repo, [])
        previous = previous if isinstance(previous, list) else []
        by_tag = {}
        for entry in previous[-100:]:
            if (isinstance(entry, dict) and valid_tag_name(entry.get("version"))
                    and entry.get("kind") in ("tag", "release")):
                by_tag[entry["version"]] = entry
        row = projects.get(repo, {})
        versions = row.get("versions")
        if isinstance(versions, list) and not row.get("errors", {}).get("versions"):
            for entry in versions:
                tag = entry["version"]
                before = by_tag.get(tag, {})
                if before.get("kind") == "release" and entry["kind"] == "tag":
                    continue
                by_tag[tag] = {**entry, "first_seen_at": before.get("first_seen_at") or NOW}
        result[repo] = sorted(
            by_tag.values(),
            key=lambda entry: (entry.get("published_at") or entry.get("first_seen_at") or "", entry["version"]),
            reverse=True,
        )[:60]
    return result



# Only explicit test-runner summaries are counted, never CI job successes.
TEST_PARSER_VERSION = 2
TEST_CATEGORIES = ("unit", "integration", "e2e", "security", "unclassified")

def empty_categories():
    return {category: {"passed": 0, "failed": 0, "skipped": 0} for category in TEST_CATEGORIES}

ANSI_ESC = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TEST_NUM = re.compile(r"(\d[\d,]*)\s+(passed|failed|skipped|pending)\b", re.I)
TEST_JOBS = re.compile(r"pytest|test|qualidade|quality|verify|checks", re.I)
TEST_PYTEST_LINE = re.compile(r"(\d[\d,]*\s+(?:passed|failed|skipped)\b.*(?:\bin\s+\d+(?:\.\d+)?s\b|=+$))", re.I)
TEST_VITEST_LINE = re.compile(r"\bTests\s*:?\s+(?=\d)(.{1,160})$", re.I)
TEST_UNITTEST = re.compile(r"\bRan\s+(\d{1,7})\s+tests?\s+in\s+[\d.]+s\b")
TEST_JEST_LINE = re.compile(r"\bTests:\s*(.{1,160})$", re.I)


def test_counts_from_log(raw):
    """Count terminal pytest/Vitest/Jest/unittest summaries, not individual test lines."""
    clean = ANSI_ESC.sub("", raw)
    lines = clean.splitlines()
    summaries = []
    for idx, line in enumerate(lines):
        line = re.sub(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d+Z\s*", "", line).strip()
        if len(line) > 400:
            continue
        candidates = []
        jest = TEST_JEST_LINE.search(line)
        vitest = TEST_VITEST_LINE.search(line) if not jest else None
        pytest = TEST_PYTEST_LINE.search(line) if not jest and not vitest else None
        if jest:
            candidates.append(jest.group(1))
        elif vitest:
            candidates.append(vitest.group(1))
        elif pytest and (line.startswith("=") or re.match(r"^\d+\s+", line) or line.startswith("FAILED ")):
            candidates.append(pytest.group(1))
        else:
            unit = TEST_UNITTEST.search(line)
            if unit:
                following = ANSI_ESC.sub("", "\n".join(lines[idx+1:idx+9]))
                if re.search(r"\bOK\b|\bFAILED\s*\(", following):
                    fail_match = re.search(r"\bFAILED\s*\(([^)]+)\)", following)
                    failed = 0
                    if fail_match:
                        failed = sum(int(n) for _, n in re.findall(r"\b(failures|errors)=(\d+)", fail_match.group(1)))
                    n = int(unit.group(1))
                    summaries.append({"passed": max(0, n - failed), "failed": failed, "skipped": 0})
                continue
        for candidate in candidates:
            counts = {"passed": 0, "failed": 0, "skipped": 0}
            for number, kind in TEST_NUM.findall(candidate):
                key = "skipped" if kind.lower() == "pending" else kind.lower()
                counts[key] += int(number.replace(",", ""))
            if sum(counts.values()) > 0 and sum(counts.values()) <= 1000000:
                summaries.append(counts)
    return {
        "passed": sum(row["passed"] for row in summaries),
        "failed": sum(row["failed"] for row in summaries),
        "skipped": sum(row["skipped"] for row in summaries),
        "summaries": len(summaries),
    }


def fetch_job_text(repo, job_id):
    """Read at most 3MB of a public Actions job log; never publish log text."""
    url = "https://api.github.com/repos/" + OWNER + "/" + repo + "/actions/jobs/" + str(job_id) + "/logs"
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "axe-delivery-hub-test-counts",
               "X-GitHub-Api-Version": "2022-11-28"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        data = response.read(3_000_001)
    if len(data) > 3_000_000:
        raise ValueError("Oversized test log")
    return data.decode("utf-8", errors="replace")



def load_verified_test_observations(path):
    """Manual backfill from original GitHub job logs, strictly tied to CI run IDs."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or set(data) != {"schema_version", "owner", "method", "observed_at", "projects"}:
        raise ValueError("Unexpected test observation schema")
    if data["schema_version"] != 1 or data["owner"] != OWNER or not isinstance(data["projects"], dict):
        raise ValueError("Invalid test observation schema")
    if not isinstance(data["method"], str) or len(data["method"]) > 200:
        raise ValueError("Test evidence method missing")
    iso_timestamp(data["observed_at"])
    if not set(data["projects"]).issubset(set(REPOS)):
        raise ValueError("Unknown project in test observations")
    for repo, item in data["projects"].items():
        if not isinstance(item, dict) or set(item) != {
            "run_id", "run_url", "observed_at", "run_conclusion", "source",
            "partial", "counts", "breakdown"
        }:
            raise ValueError("Invalid documented test observation")
        run_id = item["run_id"]
        if type(run_id) is not int or run_id <= 0 or item["run_url"] != (
            "https://github.com/" + OWNER + "/" + repo + "/actions/runs/" + str(run_id)
        ):
            raise ValueError("Test observation must link to a canonical CI run")
        if item["source"] != "github_job_logs_verified" or item["run_conclusion"] not in (
            "success", "failure", "timed_out", "cancelled"
        ) or type(item["partial"]) is not bool:
            raise ValueError("Invalid test observation provenance")
        iso_timestamp(item["observed_at"])
        rows = item["breakdown"]
        if not isinstance(rows, list) or not 1 <= len(rows) <= 12:
            raise ValueError("Test observations require a bounded job breakdown")
        counts = {"passed": 0, "failed": 0, "skipped": 0}
        categories = empty_categories()
        for entry in rows:
            if not isinstance(entry, dict) or set(entry) != {"name", "category", "passed", "failed", "skipped"}:
                raise ValueError("Unexpected breakdown fields")
            if not isinstance(entry["name"], str) or not 3 <= len(entry["name"]) <= 90:
                raise ValueError("Invalid test breakdown name")
            category = entry["category"]
            if category not in TEST_CATEGORIES:
                raise ValueError("Unrecognized or unjustified test category")
            for key in counts:
                if type(entry[key]) is not int or not 0 <= entry[key] <= 1000000:
                    raise ValueError("Invalid verified test count")
                counts[key] += entry[key]
                categories[category][key] += entry[key]
        if counts != item["counts"] or sum(counts.values()) <= 0:
            raise ValueError("Test totals do not reconcile with job reports")
    return data["projects"]


def collect_test_counts(repo, ci_record, previous, verified_record=None):
    """Only latest completed main CI. Cache by workflow run to limit GitHub traffic."""
    if ci_record is None:
        return None
    run_id = ci_record.get("id")
    if type(run_id) is not int or run_id <= 0:
        raise ValueError("CI run ID missing")
    if ci_record.get("status") != "completed":
        return {"run_id": run_id, "status": "running", "parser_version": TEST_PARSER_VERSION}
    if isinstance(verified_record, dict) and verified_record.get("run_id") == run_id and verified_record.get("run_conclusion") == ci_record.get("conclusion"):
        counts = verified_record["counts"]
        categories = empty_categories()
        for part in verified_record["breakdown"]:
            for key in ("passed", "failed", "skipped"):
                categories[part["category"]][key] += part[key]
        return {"run_id": run_id, "status": "available",
                "parser_version": TEST_PARSER_VERSION, "checked_at": NOW,
                "observed_at": verified_record["observed_at"],
                "method": "reviewed_job_logs",
                "run_url": verified_record["run_url"],
                "run_name": short(ci_record.get("name"), 120),
                "run_updated_at": short(ci_record.get("updated_at"), 35),
                "run_conclusion": ci_record["conclusion"],
                "parsed_jobs": len(verified_record["breakdown"]),
                "scanned_jobs": len(verified_record["breakdown"]),
                "missing_logs": 0, "partial": verified_record["partial"],
                "categories": categories,
                "head_sha": ci_record.get("head_sha"),
                **counts}
    if isinstance(previous, dict) and previous.get("run_id") == run_id and previous.get("parser_version") == TEST_PARSER_VERSION and previous.get("status") in ("available", "no_summary"):
        return {**previous, "checked_at": NOW}
    data = api(repo, "actions/runs/" + str(run_id) + "/jobs?per_page=40")
    if not isinstance(data, dict) or not isinstance(data.get("jobs"), list):
        raise ValueError("CI job list unavailable")
    jobs = [j for j in data["jobs"] if isinstance(j, dict) and
            TEST_JOBS.search(str(j.get("name", ""))) and j.get("status") == "completed"]
    if len(jobs) > 12:
        jobs = jobs[:12]
    results = {"passed": 0, "failed": 0, "skipped": 0}
    categories = empty_categories()
    parsed_jobs = 0
    missing_logs = 0
    for job in jobs:
        job_id = job.get("id")
        if type(job_id) is not int or job_id <= 0:
            missing_logs += 1
            continue
        try:
            counts = test_counts_from_log(fetch_job_text(repo, job_id))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, OSError):
            missing_logs += 1
            continue
        if counts["summaries"] == 0:
            continue
        parsed_jobs += 1
        for key in results:
            results[key] += counts[key]
            categories["unclassified"][key] += counts[key]
    available = parsed_jobs > 0
    return {
        "run_id": run_id, "run_url": "https://github.com/" + OWNER + "/" + repo + "/actions/runs/" + str(run_id),
        "run_name": short(ci_record.get("name"), 120), "run_updated_at": short(ci_record.get("updated_at"), 35),
        "run_conclusion": short(ci_record.get("conclusion"), 40),
        "status": "available" if available else "no_summary",
        "parser_version": TEST_PARSER_VERSION, "checked_at": NOW,
        "head_sha": ci_record.get("head_sha"),
        "categories": categories if available else None,
        "parsed_jobs": parsed_jobs, "scanned_jobs": len(jobs), "missing_logs": missing_logs,
        "partial": missing_logs > 0 or parsed_jobs < len(jobs) or len(data["jobs"]) >= 40,
        "passed": results["passed"] if available else None,
        "failed": results["failed"] if available else None,
        "skipped": results["skipped"] if available else None,
    }



def append_test_history(saved, rows):
    """Append distinct observed workflow runs; no synthetic results or duplicate polling."""
    old = saved.get("test_history", {}) if isinstance(saved, dict) else {}
    old = old if isinstance(old, dict) else {}
    history = {}
    for repo in REPOS:
        previous = old.get(repo, [])
        previous = previous if isinstance(previous, list) else []
        output = [row for row in previous[-99:] if isinstance(row, dict)
                  and type(row.get("run_id")) is int and row.get("run_id") > 0
                  and row.get("status") == "available"]
        test = rows.get(repo, {}).get("tests")
        if isinstance(test, dict) and test.get("status") == "available" and not rows[repo].get("errors", {}).get("tests"):
            rid = test.get("run_id")
            if type(rid) is int and rid > 0:
                match = next((i for i, x in enumerate(output) if x["run_id"] == rid), None)
                if match is None:
                    output.append({**test, "first_seen_at": NOW})
                elif isinstance(test.get("categories"), dict):
                    output[match] = {**output[match], **test, "first_seen_at": output[match].get("first_seen_at") or NOW}
        history[repo] = output[-100:]
    return history


def extract_milestone_progress(html):
    """Read only literal milestone lists from the reviewed page (no JS execution)."""
    pattern = re.compile(
        r'\{id:"([A-Za-z0-9_-]+)",name:"([^"]+)"[\s\S]*?milestones:\[([\s\S]*?)\],history:\['
    )
    matches = list(pattern.finditer(html))
    expected = len(REPOS)
    if len(matches) != expected or html.count("milestones:[") != expected:
        raise ValueError("Expected exactly %d milestone lists, found %d" % (expected, len(matches)))
    progress = {}
    for match in matches:
        repo_id = match.group(1)
        if repo_id not in REPOS or repo_id in progress:
            raise ValueError("Unknown or duplicate portfolio project: " + repo_id)
        raw = "[" + match.group(3) + "]"
        milestones = json.loads(raw)
        if not isinstance(milestones, list) or not milestones:
            raise ValueError("Milestones must be a nonempty list: " + repo_id)
        if not all(
            isinstance(row, list) and len(row) == 2
            and isinstance(row[0], str) and bool(row[0].strip())
            and type(row[1]) is bool
            for row in milestones
        ):
            raise ValueError("Invalid milestone declaration: " + repo_id)
        progress[repo_id] = {
            "completed": sum(row[1] for row in milestones),
            "total": len(milestones),
        }
    if set(progress) != set(REPOS):
        raise ValueError("Portfolio and collector repository lists differ")
    return progress



def append_progress_samples(saved, progress, observed_at=NOW):
    """Record periodic editorial snapshots; only real observation times are admissible."""
    parsed_now = dt.datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    old = saved.get("progress_samples", []) if isinstance(saved, dict) else []
    old = old if isinstance(old, list) else []
    samples = []
    for row in old[-700:]:
        if not isinstance(row, dict) or set(row) != {"observed_at", "projects"}:
            continue
        stamp = row["observed_at"]
        try:
            moment = dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        except (AttributeError, ValueError):
            continue
        if moment.tzinfo is None or not parsed_now - dt.timedelta(hours=48) <= moment < parsed_now:
            continue
        projects = row["projects"]
        if not isinstance(projects, dict) or set(projects) != set(progress):
            continue
        if any(not isinstance(v, dict) or
               type(v.get("completed")) is not int or type(v.get("total")) is not int or
               v["total"] < 1 or not 0 <= v["completed"] <= v["total"] or
               v["total"] != progress[k]["total"] for k, v in projects.items()):
            continue
        samples.append(row)
    samples.sort(key=lambda row: row["observed_at"])
    # Re-running a collector with an identical timestamp cannot create duplicate observations.
    samples = [row for row in samples if row["observed_at"] != observed_at]
    samples.append({"observed_at": observed_at, "projects": progress})
    return samples[-600:]


def progress_for_window(samples, minutes=60, at=NOW):
    """Compare two genuine snapshots; tolerates at most 20 minutes of scheduler lag."""
    if minutes not in (60, 360, 1440):
        raise ValueError("Unsupported progress window")
    current = samples[-1]
    now = dt.datetime.fromisoformat(at.replace("Z", "+00:00"))
    cutoff = now - dt.timedelta(minutes=minutes)
    candidates = []
    for sample in samples[:-1]:
        try:
            date = dt.datetime.fromisoformat(sample["observed_at"].replace("Z", "+00:00"))
        except (KeyError, AttributeError, ValueError):
            continue
        if cutoff - dt.timedelta(minutes=20) <= date <= cutoff:
            candidates.append((date, sample))
    output = {"window_minutes": minutes, "measured_at": at, "baseline_at": None,
              "status": "insufficient_history", "portfolio": None, "projects": {}}
    if not candidates:
        return output
    _, baseline = max(candidates, key=lambda item: item[0])
    output["baseline_at"] = baseline["observed_at"]
    output["status"] = "measured"

    def comparison(previous, latest):
        initial_done = previous["completed"]
        initial_total = previous["total"]
        final_done = latest["completed"]
        final_total = latest["total"]
        if initial_total != final_total:
            return None
        points = round(100 * (final_done - initial_done) / final_total, 2)
        return {"before_percent": round(100 * initial_done / initial_total, 2),
                "after_percent": round(100 * final_done / final_total, 2),
                "delta_points": points, "delta_milestones": final_done - initial_done,
                "before_completed": initial_done, "after_completed": final_done,
                "total": final_total}

    before = baseline["projects"]
    after = current["projects"]
    output["projects"] = {repo: comparison(before[repo], row) for repo, row in after.items()}
    start = {"completed": sum(row["completed"] for row in before.values()),
             "total": sum(row["total"] for row in before.values())}
    end = {"completed": sum(row["completed"] for row in after.values()),
           "total": sum(row["total"] for row in after.values())}
    output["portfolio"] = comparison(start, end)
    return output


def hourly_progress(samples, at=NOW):
    """Backwards-compatible last-hour view for existing dashboard consumers."""
    return progress_for_window(samples, 60, at)


def append_progress_history(old, progress):
    """Append only actual changes; never manufacture intermediate dates/percentages."""
    history = old.get("progress_history", []) if isinstance(old, dict) else []
    if not isinstance(history, list):
        history = []
    history = [item for item in history if isinstance(item, dict) and isinstance(item.get("projects"), dict)]
    if not history or history[-1]["projects"] != progress:
        history.append({"observed_at": NOW, "projects": progress})
    return history[-365:]


def extract_milestone_links(html, progress):
    """Read strictly typed, explicit references from the reviewed page."""
    m = re.search(r'^const MILESTONE_LINKS = (\{[^\n]+\});$', html, re.M)
    if not m:
        raise ValueError("MILESTONE_LINKS literal missing")
    links = json.loads(m.group(1))
    if not isinstance(links, dict):
        raise ValueError("MILESTONE_LINKS must be an object")
    count = 0
    for repo, items in links.items():
        if repo not in progress or not isinstance(items, dict):
            raise ValueError("Unknown project in MILESTONE_LINKS")
        for key, refs in items.items():
            if not isinstance(key, str) or not key.isdecimal() or str(int(key)) != key or int(key) >= progress[repo]["total"]:
                raise ValueError("Invalid milestone index")
            if not isinstance(refs, list) or not 1 <= len(refs) <= 3:
                raise ValueError("Invalid milestone references")
            seen = set()
            for ref in refs:
                if not isinstance(ref, dict) or set(ref.keys()) != {"kind", "number"}:
                    raise ValueError("Unexpected milestone reference fields")
                kind, number = ref["kind"], ref["number"]
                if kind not in ("pr", "issue") or type(number) is not int or not 1 <= number <= 100000 or (kind, number) in seen:
                    raise ValueError("Invalid or duplicate reference")
                seen.add((kind, number))
                count += 1
    if count > 30:
        raise ValueError("Too many remote lookups")
    return links


def fetch_tracking(repo, kind, number):
    path = ("pulls/" if kind == "pr" else "issues/") + str(number)
    obj = api(repo, path)
    if not isinstance(obj, dict) or obj.get("number") != number:
        raise ValueError("GitHub returned unrelated reference")
    if kind == "issue" and obj.get("pull_request"):
        raise ValueError("This issue number belongs to a pull request")
    state = "merged" if kind == "pr" and obj.get("merged_at") else obj.get("state")
    if state not in ("open", "closed", "merged"):
        raise ValueError("Invalid reference state")
    url = "https://github.com/" + OWNER + "/" + repo + "/" + ("pull/" if kind == "pr" else "issues/") + str(number)
    return {"kind": kind, "number": number, "state": state, "title": short(obj.get("title"), 150),
            "url": url, "verified_at": NOW, "error": None}


def collect_tracking(mapping, previous):
    previous = previous if isinstance(previous, dict) else {}
    results = {}
    for repo, items in mapping.items():
        results[repo] = {}
        for index, refs in items.items():
            old_rows = previous.get(repo, {}).get(index, [])
            old_rows = old_rows if isinstance(old_rows, list) else []
            old = {(x.get("kind"), x.get("number")): x for x in old_rows if isinstance(x, dict)}
            results[repo][index] = []
            for ref in refs:
                kind, number = ref["kind"], ref["number"]
                try:
                    results[repo][index].append(fetch_tracking(repo, kind, number))
                except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
                    prev = old.get((kind, number), {})
                    results[repo][index].append({
                        "kind": kind, "number": number, "state": prev.get("state"),
                        "title": prev.get("title"), "url": None,
                        "verified_at": prev.get("verified_at"), "error": type(exc).__name__})
    return results


RELEASE_CHECKS = ("functional", "security", "data", "rollback", "approval")
EVIDENCE_URL_RE = re.compile(
    r"^https://github\.com/jeffaxe81/([A-Za-z0-9_-]+)/"
    r"(?:pull/[1-9][0-9]*|issues/[1-9][0-9]*|commit/[a-fA-F0-9]{40}|actions/runs/[1-9][0-9]*)$"
)


def safe_public_reference(repo, value):
    if not isinstance(value, str) or len(value) > 300:
        return False
    m = EVIDENCE_URL_RE.fullmatch(value)
    return bool(m and m.group(1) == repo)


def iso_timestamp(value):
    if not isinstance(value, str) or len(value) != 20 or not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", value):
        raise ValueError("Evidence and decision timestamps must be UTC ISO-8601")
    try:
        parsed = dt.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
    except ValueError as exc:
        raise ValueError("Invalid ISO timestamp") from exc
    if parsed > dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=5):
        raise ValueError("Future-dated evidence is forbidden")
    return parsed


def load_release_control(path, html, progress):
    """Validate public decision ledger before publishing. Missing/invalid data fails closed."""
    source = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(source, dict) or set(source) != {"schema_version", "owner", "purpose", "projects"}:
        raise ValueError("Unexpected release ledger schema")
    if type(source["schema_version"]) is not int or source["schema_version"] != 1 or source["owner"] != OWNER:
        raise ValueError("Invalid release ledger owner or version")
    if not isinstance(source["purpose"], str) or len(source["purpose"]) > 180:
        raise ValueError("Invalid ledger description")
    projects = source["projects"]
    if not isinstance(projects, dict) or set(projects) != set(REPOS):
        raise ValueError("Release ledger must enumerate exactly monitored repositories")
    gate_match = re.search(r'^const GATE_MATRIX = (\{[^\n]+\});$', html, re.M)
    if not gate_match:
        raise ValueError("Reviewed stage gate map required")
    gates = json.loads(gate_match.group(1))
    if set(gates) != set(REPOS):
        raise ValueError("Stage gate and release ledger project mismatch")
    for repo, row in projects.items():
        if not isinstance(row, dict) or set(row) != {"checks", "decisions"}:
            raise ValueError("Unexpected project release fields")
        checks = row["checks"]
        if not isinstance(checks, dict) or set(checks) != set(RELEASE_CHECKS):
            raise ValueError("Missing or unexpected release criterion")
        for key, entry in checks.items():
            if not isinstance(entry, dict) or set(entry) != {"status", "evidence", "note", "verified_at"}:
                raise ValueError("Invalid release check payload")
            status = entry["status"]
            if status == "not_recorded":
                if any(entry[field] is not None for field in ("evidence", "note", "verified_at")):
                    raise ValueError("Unverified release criterion cannot show evidence")
            elif status == "verified":
                if not safe_public_reference(repo, entry["evidence"]):
                    raise ValueError("Verified criterion requires a canonical same-repo GitHub reference")
                note = entry["note"]
                if not isinstance(note, str) or not 8 <= len(note.strip()) <= 400 or "\n" in note:
                    raise ValueError("Verified criterion requires a useful public note")
                iso_timestamp(entry["verified_at"])
            else:
                raise ValueError("Invalid release check status")
        events = row["decisions"]
        if not isinstance(events, list) or len(events) > 30:
            raise ValueError("Decision history must be a bounded array")
        previous = None
        for event in events:
            if not isinstance(event, dict) or set(event) != {"outcome", "reviewer", "recorded_at", "sha", "reference", "reason"}:
                raise ValueError("Invalid decision event fields")
            if event["outcome"] not in ("GO", "NO_GO"):
                raise ValueError("Decision must explicitly be GO or NO_GO")
            if not isinstance(event["reviewer"], str) or not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})", event["reviewer"]):
                raise ValueError("Decision reviewer must be a GitHub handle")
            if not isinstance(event["sha"], str) or not re.fullmatch(r"[a-f0-9]{40}", event["sha"]):
                raise ValueError("Decision must reference a specific code SHA")
            if not safe_public_reference(repo, event["reference"]):
                raise ValueError("Decision requires same-repo public GitHub evidence")
            if not isinstance(event["reason"], str) or not 15 <= len(event["reason"].strip()) <= 400 or "\n" in event["reason"]:
                raise ValueError("Decision needs an explicit, concise rationale")
            stamp = iso_timestamp(event["recorded_at"])
            if previous is not None and stamp <= previous:
                raise ValueError("Decision events must be strictly chronological")
            previous = stamp
            if event["outcome"] == "GO":
                if any(v["status"] != "verified" for v in checks.values()):
                    raise ValueError("GO requires all five documented evidence checks")
                for key in ("homolog", "release"):
                    indices = gates[repo].get(key)
                    if not isinstance(indices, list) or not indices or any(type(i) is not int or i >= progress[repo]["total"] or i < 0 for i in indices):
                        raise ValueError("GO requires mapped homologation and release milestones")
                match = re.search(
                    r'\{id:"' + re.escape(repo) + r'",name:"[^"]+"[\s\S]*?milestones:\[([\s\S]*?)\],history:\[',
                    html,
                )
                if not match:
                    raise ValueError("GO requires a mapped milestone list")
                milestone_rows = json.loads("[" + match.group(1) + "]")
                if any(not milestone_rows[i][1] for key in ("homolog", "release") for i in gates[repo][key]):
                    raise ValueError("GO requires completed homologation and release milestones")
                if not all(iso_timestamp(v["verified_at"]) <= stamp for v in checks.values()):
                    raise ValueError("GO must postdate all release evidence")
    return source


def generate(output, html_file):
    old = {}
    saved = {}
    if output.is_file():
        try:
            saved = json.loads(output.read_text(encoding="utf-8"))
            if saved.get("schema_version") == 1:
                old = saved.get("projects") or {}
            else:
                saved = {}
        except (OSError, ValueError, TypeError):
            pass
    result = {}
    failures = []
    verified_tests = load_verified_test_observations(output.with_name("test-observations.json"))
    for repo in REPOS:
        prev = old.get(repo, {}) if isinstance(old.get(repo), dict) else {}
        item = {"errors": {}, "verified_at": {}}
        for key, getter in (("commits", commits), ("prs", prs), ("ci", ci), ("versions", repo_versions)):
            try:
                item[key] = getter(repo)
                item["verified_at"][key] = NOW
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
                item[key] = prev.get(key)
                item["verified_at"][key] = (prev.get("verified_at") or {}).get(key)
                item["errors"][key] = type(exc).__name__
                failures.append(repo + ":" + key)
        try:
            item["tests"] = collect_test_counts(repo, item.get("ci"), prev.get("tests"), verified_tests.get(repo))
            item["verified_at"]["tests"] = NOW
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, OSError, KeyError, TypeError) as exc:
            item["tests"] = prev.get("tests")
            item["verified_at"]["tests"] = (prev.get("verified_at") or {}).get("tests")
            item["errors"]["tests"] = type(exc).__name__
            failures.append(repo + ":tests")
        result[repo] = item
    # Prevent an empty successful-looking collection when every source is down.
    if not any(
        item.get("commits") is not None or item.get("prs") is not None or item.get("verified_at", {}).get("ci")
        for item in result.values()
    ):
        raise RuntimeError("All sources failed; keeping the previous snapshot")
    progress = extract_milestone_progress(html_file.read_text(encoding="utf-8"))
    history = append_progress_history(saved, progress)
    progress_samples = append_progress_samples(saved, progress)
    progress_hourly = hourly_progress(progress_samples)
    progress_windows = {str(minutes): progress_for_window(progress_samples, minutes)
                        for minutes in (60, 360, 1440)}
    version_history = merge_version_history(saved, result)
    test_history = append_test_history(saved, result)
    release_control = load_release_control(output.with_name("release-approvals.json"), html_file.read_text(encoding="utf-8"), progress)
    links = extract_milestone_links(html_file.read_text(encoding="utf-8"), progress)
    tracking = collect_tracking(links, saved.get("tracking", {}))
    # Public audit trail: numeric run ID only, no tokens or runner secrets.
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    collector = {
        "run_url": ("https://github.com/jeffaxe81/AXE/actions/runs/" + run_id) if run_id.isdecimal() and len(run_id) <= 20 else None,
        "trigger": os.environ.get("GITHUB_EVENT_NAME") if os.environ.get("GITHUB_EVENT_NAME") in ("push", "schedule", "workflow_dispatch") else None,
    }
    payload = {"schema_version": 1, "generated_at": NOW, "collection_interval_minutes": 5, "owner": OWNER, "projects": result, "progress": progress, "progress_history": history, "progress_samples": progress_samples, "progress_hourly": progress_hourly, "progress_windows": progress_windows, "collector": collector, "tracking": tracking, "release_control": release_control, "version_history": version_history, "test_history": test_history}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    print("Collected", len(result), "repositories;", len(failures), "unavailable sources.")
    if failures:
        print("Unavailable:", ", ".join(failures), file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=pathlib.Path)
    parser.add_argument("--html", required=True, type=pathlib.Path)
    args = parser.parse_args()
    generate(args.output, args.html)
