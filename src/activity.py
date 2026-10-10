"""Rewrites the activity log block in README.md from the public events feed.

Runs daily in .github/workflows/activity.yml. Standard library only.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

USER = os.environ.get("GH_USER", "PurnaJear06")
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
README = Path(__file__).resolve().parent.parent / "README.md"
IST = timezone(timedelta(hours=5, minutes=30))
ROWS = 8
START, END = "<!-- activity:start -->", "<!-- activity:end -->"


def api(url):
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USER}-profile-activity",
        **({"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}),
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def pr_title(url):
    try:
        return api(url).get("title", "")
    except Exception:
        return ""


def collect():
    events = []
    for page in (1, 2, 3):  # the feed caps at 300 events / 90 days
        batch = api(f"https://api.github.com/users/{USER}/events/public?per_page=100&page={page}")
        events += batch
        if len(batch) < 100:
            break
    now = datetime.now(timezone.utc)
    rows, pushes = [], {}
    recent_repos, recent_count = Counter(), 0
    for e in events:
        repo = e["repo"]["name"]
        short = repo.split("/", 1)[1] if repo.startswith(USER + "/") else repo
        if short == USER:
            continue
        at = datetime.fromisoformat(e["created_at"].replace("Z", "+00:00"))
        if now - at <= timedelta(days=30):
            recent_count += 1
            recent_repos[short] += 1
        pl, typ = e.get("payload", {}), e["type"]
        if typ == "PullRequestEvent":
            pr = pl.get("pull_request", {})
            act = pl.get("action")
            if act == "merged" or (act == "closed" and pr.get("merged")):
                verb = "MERGED"
            elif act == "opened":
                verb = "OPENED"
            else:
                continue
            title = pr.get("title") or pr_title(pr.get("url", ""))
            rows.append([at, verb, short, f"#{pl.get('number', pr.get('number', ''))} {title}".strip()])
        elif typ == "PushEvent":
            branch = pl.get("ref", "").rsplit("/", 1)[-1]
            key = (short, at.astimezone(IST).date())
            row = pushes.get(key)
            if row is None:
                row = pushes[key] = [at, "PUSH", short, "", 0, set()]
                rows.append(row)
            row[4] += 1
            row[5].add(branch)
            n, b = row[4], row[5]
            row[3] = (f"{n} push{'es' if n > 1 else ''} to {next(iter(b))}" if len(b) == 1
                      else f"{n} pushes across {len(b)} branches")
        elif typ == "CreateEvent" and pl.get("ref_type") == "repository":
            rows.append([at, "NEW", short, (pl.get("description") or "new repository")])
        elif typ == "ReleaseEvent":
            rows.append([at, "RELEASE", short, pl.get("release", {}).get("tag_name", "")])
        elif typ == "PublicEvent":
            rows.append([at, "PUBLIC", short, "repository opened up"])
    rows.sort(key=lambda r: r[0], reverse=True)
    capped = len(events) >= 300
    return rows[:ROWS], f"{recent_count}{'+' if capped else ''}", recent_repos


def render(rows, recent_count, recent_repos):
    lines = [f"$ tail -n {ROWS} ~/ops/activity.log"]
    if not rows:
        lines.append("(quiet shift: no public activity yet)")
    for at, verb, repo, detail, *_ in rows:
        stamp = at.astimezone(IST).strftime("%Y-%m-%d %H:%M")
        detail = detail if len(detail) <= 48 else detail[:47] + "…"
        lines.append(f"{stamp}  {verb:<7} {repo:<14} {detail}")
    synced = datetime.now(IST).strftime("%Y-%m-%d %H:%M IST")
    n_repos = len(recent_repos)
    lines.append("")
    lines.append(f"# synced {synced} · 30d: {recent_count} public events across "
                 f"{n_repos} repo{'s' if n_repos != 1 else ''}")
    return "```text\n" + "\n".join(lines) + "\n```"


def main():
    block = render(*collect())
    text = README.read_text(encoding="utf-8")
    new = re.sub(f"{re.escape(START)}.*?{re.escape(END)}", f"{START}\n{block}\n{END}", text, flags=re.S)
    README.write_text(new, encoding="utf-8")
    print(block)


if __name__ == "__main__":
    main()
