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
    return [
        {"sha": c["sha"], "date": c["commit"]["committer"]["date"][:10], "title": short(c["commit"]["message"])}
        for c in data if isinstance(c.get("sha"), str) and len(c["sha"]) == 40
        and ((c.get("commit") or {}).get("committer") or {}).get("date")
    ]


def prs(repo):
    data = api(repo, "pulls?state=all&sort=updated&direction=desc&per_page=20")
    if not isinstance(data, list):
        raise ValueError("Invalid PR response")
    return {
        "open": sum(p.get("state") == "open" for p in data),
        "merged": sum(bool(p.get("merged_at")) for p in data),
        "closed": sum(p.get("state") == "closed" and not p.get("merged_at") for p in data),
        "sample_size": len(data),
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
    }


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


def append_progress_history(old, progress):
    """Append only actual changes; never manufacture intermediate dates/percentages."""
    history = old.get("progress_history", []) if isinstance(old, dict) else []
    if not isinstance(history, list):
        history = []
    history = [item for item in history if isinstance(item, dict) and isinstance(item.get("projects"), dict)]
    if not history or history[-1]["projects"] != progress:
        history.append({"observed_at": NOW, "projects": progress})
    return history[-365:]


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
    for repo in REPOS:
        prev = old.get(repo, {}) if isinstance(old.get(repo), dict) else {}
        item = {"errors": {}, "verified_at": {}}
        for key, getter in (("commits", commits), ("prs", prs), ("ci", ci)):
            try:
                item[key] = getter(repo)
                item["verified_at"][key] = NOW
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, KeyError, TypeError) as exc:
                item[key] = prev.get(key)
                item["verified_at"][key] = (prev.get("verified_at") or {}).get(key)
                item["errors"][key] = type(exc).__name__
                failures.append(repo + ":" + key)
        result[repo] = item
    # Prevent an empty successful-looking collection when every source is down.
    if not any(
        item.get("commits") is not None or item.get("prs") is not None or item.get("verified_at", {}).get("ci")
        for item in result.values()
    ):
        raise RuntimeError("All sources failed; keeping the previous snapshot")
    progress = extract_milestone_progress(html_file.read_text(encoding="utf-8"))
    history = append_progress_history(saved, progress)
    payload = {"schema_version": 1, "generated_at": NOW, "collection_interval_minutes": 5, "owner": OWNER, "projects": result, "progress": progress, "progress_history": history}
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
