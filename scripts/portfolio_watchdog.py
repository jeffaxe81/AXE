#!/usr/bin/env python3
"""Independent AXE Pages watchdog; recover stale published snapshots via Actions."""
import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.parse
import urllib.request

REPOSITORY = "jeffaxe81/AXE"
WORKFLOW = "portfolio-refresh.yml"
SITE = "https://jeffaxe81.github.io/AXE/portfolio-status.json"
MAX_AGE = 20 * 60
INFLIGHT_MAX_AGE = 30 * 60


class RecoveryError(RuntimeError):
    pass


def timestamp(value):
    if not isinstance(value, str):
        raise RecoveryError("Timestamp de coleta ausente")
    try:
        moment = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RecoveryError("Timestamp de coleta inválido") from exc
    if moment.tzinfo is None:
        raise RecoveryError("Timestamp sem fuso horário")
    return moment.astimezone(dt.timezone.utc)


def age_seconds(snapshot, now):
    if (not isinstance(snapshot, dict) or snapshot.get("schema_version") != 1
            or snapshot.get("owner") != "jeffaxe81"
            or not isinstance(snapshot.get("projects"), dict)
            or len(snapshot["projects"]) != 9):
        raise RecoveryError("Snapshot inválido/incompleto")
    age = (now - timestamp(snapshot.get("generated_at"))).total_seconds()
    if age < -300:
        raise RecoveryError("Coleta com data futura inválida")
    return age


def inflight_recent(runs, now):
    if not isinstance(runs, list):
        raise RecoveryError("Lista de workflows inválida")
    for run in runs:
        if (not isinstance(run, dict) or run.get("head_branch") != "main"
                or run.get("status") not in ("queued", "in_progress", "requested", "waiting")):
            continue
        try:
            age = (now - timestamp(run.get("created_at"))).total_seconds()
        except RecoveryError:
            continue
        if -300 <= age <= INFLIGHT_MAX_AGE:
            return True
    return False


def recover(old, *, now, get_runs, dispatch, fetch_snapshot, sleep, attempts=18):
    age = age_seconds(old, now())
    if age <= MAX_AGE:
        return old, "fresh"
    if inflight_recent(get_runs(), now()):
        print("Coleta recente já em andamento; sem disparo duplicado.")
    else:
        dispatch()
        print("::warning::Coleta atrasada; nova coleta solicitada no GitHub Actions.")
    previous_at = timestamp(old["generated_at"])
    for attempt in range(attempts):
        sleep(10)
        try:
            candidate = fetch_snapshot(attempt)
            new_age = age_seconds(candidate, now())
            new_at = timestamp(candidate["generated_at"])
        except (OSError, ValueError, RecoveryError, TimeoutError) as exc:
            print("Consulta %d/%d: %s" % (attempt + 1, attempts, type(exc).__name__))
            continue
        if new_at > previous_at and -300 <= new_age <= MAX_AGE:
            print("Snapshot público recuperado: " + candidate["generated_at"])
            return candidate, "recovered"
    raise RecoveryError("Snapshot ainda antigo após recuperação; verificação deve falhar")


def request_json(url, token=None, payload=None):
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "axe-portfolio-watchdog", "Cache-Control": "no-cache"}
    if token:
        headers["Authorization"] = "Bearer " + token
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, headers=headers, data=payload,
                                 method="POST" if payload is not None else "GET")
    with urllib.request.urlopen(req, timeout=8) as response:
        raw = response.read(5_000_001)
    if len(raw) > 5_000_000:
        raise RecoveryError("Resposta maior que o limite")
    return json.loads(raw) if raw else None


def main():
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise RecoveryError("Watchdog não autorizado fora do repositório AXE")
    path = pathlib.Path("/tmp/axe-status.json")
    old = json.loads(path.read_text(encoding="utf-8"))
    token = os.environ.get("GH_TOKEN", "")
    base = "https://api.github.com/repos/" + REPOSITORY + "/actions/workflows/" + WORKFLOW

    def get_runs():
        if not token:
            raise RecoveryError("Token ausente para inspecionar workflows")
        response = request_json(base + "/runs?per_page=15", token=token)
        if not isinstance(response, dict) or not isinstance(response.get("workflow_runs"), list):
            raise RecoveryError("API do GitHub retornou lista inválida")
        return response["workflow_runs"]

    def dispatch():
        if not token:
            raise RecoveryError("Token ausente para acionar recuperação")
        request_json(base + "/dispatches", token=token, payload=b'{"ref":"main"}')

    def fetch_snapshot(attempt):
        params = urllib.parse.urlencode({"watchdog": os.environ.get("GITHUB_RUN_ID", "0"),
                                        "attempt": attempt})
        return request_json(SITE + "?" + params)

    new, state = recover(old, now=lambda: dt.datetime.now(dt.timezone.utc),
                         get_runs=get_runs, dispatch=dispatch,
                         fetch_snapshot=fetch_snapshot, sleep=time.sleep)
    if state == "recovered":
        path.write_text(json.dumps(new, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Watchdog: " + state + ". Agendamento GitHub permanece best-effort.")


if __name__ == "__main__":
    try:
        main()
    except (RecoveryError, OSError, ValueError) as exc:
        print("::error::" + str(exc), file=sys.stderr)
        sys.exit(1)
