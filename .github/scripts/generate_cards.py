#!/usr/bin/env python3
"""
Fetches real GitHub stats for GITHUB_USERNAME and regenerates the static
SVG profile cards (stats-card.svg, languages-card.svg,
commits-by-hour-card.svg, contributions-card.svg) in the repo root.

Run by .github/workflows/update-cards.yml on a schedule + manual trigger.
Requires env vars: GITHUB_TOKEN, GITHUB_USERNAME (falls back to repo owner).
"""

import os
import sys
import json
import datetime
import urllib.request
import urllib.error

TOKEN = os.environ["GITHUB_TOKEN"]
USERNAME = os.environ.get("GITHUB_USERNAME") or os.environ["GITHUB_REPOSITORY"].split("/")[0]
UTC_OFFSET_HOURS = float(os.environ.get("UTC_OFFSET_HOURS", "5.5"))  # IST default

API_ROOT = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": USERNAME,
}


def rest_get(path, params=None):
    url = f"{API_ROOT}{path}"
    if params:
        query = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{query}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"WARN: GET {url} -> {e.code}", file=sys.stderr)
        return None


def graphql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(GRAPHQL_URL, data=body, headers={**HEADERS, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"WARN: GraphQL -> {e.code} {e.read()}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# 1. Fetch all repos (owned, not forks) for stars + languages
# ---------------------------------------------------------------------------
def fetch_repos():
    repos, page = [], 1
    while True:
        batch = rest_get(f"/users/{USERNAME}/repos", {"per_page": 100, "page": page, "type": "owner"})
        if not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return [r for r in repos if not r.get("fork")]


def total_stars(repos):
    return sum(r.get("stargazers_count", 0) for r in repos)


def language_breakdown(repos):
    counts = {}
    for r in repos:
        lang = r.get("language")
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)[:5]


# ---------------------------------------------------------------------------
# 2. Contributions calendar + total commits/PRs/issues via GraphQL
# ---------------------------------------------------------------------------
CONTRIB_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoriesWithContributedCommits
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def fetch_contributions():
    data = graphql(CONTRIB_QUERY, {"login": USERNAME})
    if not data or "data" not in data or not data["data"].get("user"):
        return None
    return data["data"]["user"]["contributionsCollection"]


# ---------------------------------------------------------------------------
# 3. Commit hour-of-day histogram (samples recent commits across top repos)
# ---------------------------------------------------------------------------
def commit_hour_histogram(repos, max_repos=6, max_commits_per_repo=100):
    hours = [0] * 24
    sample_repos = sorted(repos, key=lambda r: r.get("pushed_at") or "", reverse=True)[:max_repos]
    for r in sample_repos:
        commits = rest_get(
            f"/repos/{USERNAME}/{r['name']}/commits",
            {"author": USERNAME, "per_page": max_commits_per_repo},
        )
        if not commits:
            continue
        for c in commits:
            date_str = (c.get("commit", {}).get("author", {}) or {}).get("date")
            if not date_str:
                continue
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
            local_hour = int((dt.hour + UTC_OFFSET_HOURS) % 24)
            hours[local_hour] += 1
    return hours


# ---------------------------------------------------------------------------
# SVG renderers
# ---------------------------------------------------------------------------
def render_stats_card(stars, commits, prs, issues, contributed_to):
    return f"""<svg width="340" height="200" viewBox="0 0 340 200" xmlns="http://www.w3.org/2000/svg">
  <rect x="1" y="1" width="338" height="198" rx="12" fill="#0d1117" stroke="#2d3341" stroke-width="1"/>
  <text x="24" y="36" font-family="Segoe UI, Verdana, sans-serif" font-size="18" font-weight="700" fill="#4a90e2">Stats</text>
  <g font-family="Segoe UI, Verdana, sans-serif" font-size="13" fill="#c9d1d9">
    <text x="24" y="68">Total Stars:</text>
    <text x="160" y="68" font-weight="600">{stars}</text>
    <text x="24" y="94">Total Commits:</text>
    <text x="160" y="94" font-weight="600">{commits}</text>
    <text x="24" y="120">Total PRs:</text>
    <text x="160" y="120" font-weight="600">{prs}</text>
    <text x="24" y="146">Total Issues:</text>
    <text x="160" y="146" font-weight="600">{issues}</text>
    <text x="24" y="172">Contributed to:</text>
    <text x="160" y="172" font-weight="600">{contributed_to}</text>
  </g>
  <g transform="translate(265, 100)">
    <circle cx="0" cy="0" r="42" fill="#21262d"/>
    <path transform="translate(-17,-17) scale(1.4167)" fill="#c9d1d9" d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12"/>
  </g>
</svg>
"""


LANG_COLORS = {
    "HTML": "#e2542b", "JavaScript": "#f1e05a", "Python": "#3572A5",
    "Java": "#b07219", "C": "#9e9e9e", "C++": "#f34b7d", "TypeScript": "#3178c6",
    "CSS": "#563d7c", "Jupyter Notebook": "#DA5B0B", "Shell": "#89e051",
}
DEFAULT_COLORS = ["#e2542b", "#f1e05a", "#3572A5", "#b07219", "#555555"]


def render_languages_card(lang_counts):
    if not lang_counts:
        lang_counts = [("N/A", 1)]
    total = sum(c for _, c in lang_counts)
    legend_items = []
    segments = []
    angle_start = -90  # start at top
    import math
    for i, (lang, count) in enumerate(lang_counts):
        color = LANG_COLORS.get(lang, DEFAULT_COLORS[i % len(DEFAULT_COLORS)])
        legend_items.append(
            f'<rect x="24" y="{56 + i * 24}" width="12" height="12" fill="{color}"/>'
            f'<text x="42" y="{66 + i * 24}">{lang}</text>'
        )
        frac = count / total
        angle_end = angle_start + frac * 360
        r_outer, r_inner = 55, 32
        x0 = r_outer * math.cos(math.radians(angle_start))
        y0 = r_outer * math.sin(math.radians(angle_start))
        x1 = r_outer * math.cos(math.radians(angle_end))
        y1 = r_outer * math.sin(math.radians(angle_end))
        xi0 = r_inner * math.cos(math.radians(angle_end))
        yi0 = r_inner * math.sin(math.radians(angle_end))
        xi1 = r_inner * math.cos(math.radians(angle_start))
        yi1 = r_inner * math.sin(math.radians(angle_start))
        large_arc = 1 if (angle_end - angle_start) > 180 else 0
        path = (f'M {x0:.1f} {y0:.1f} A {r_outer} {r_outer} 0 {large_arc} 1 {x1:.1f} {y1:.1f} '
                f'L {xi0:.1f} {yi0:.1f} A {r_inner} {r_inner} 0 {large_arc} 0 {xi1:.1f} {yi1:.1f} Z')
        segments.append(f'<path d="{path}" fill="{color}" stroke="#0d1117" stroke-width="1.5"/>')
        angle_start = angle_end

    height = max(200, 56 + len(lang_counts) * 24 + 20)
    return f"""<svg width="340" height="{height}" viewBox="0 0 340 {height}" xmlns="http://www.w3.org/2000/svg">
  <rect x="1" y="1" width="338" height="{height - 2}" rx="12" fill="#0d1117" stroke="#2d3341" stroke-width="1"/>
  <text x="24" y="34" font-family="Segoe UI, Verdana, sans-serif" font-size="18" font-weight="700" fill="#4a90e2">Top Languages by Repo</text>
  <g font-family="Segoe UI, Verdana, sans-serif" font-size="13" fill="#c9d1d9">
    {''.join(legend_items)}
  </g>
  <g transform="translate(255, {height // 2 + 5})">
    {''.join(segments)}
  </g>
</svg>
"""


def render_commits_by_hour_card(hours):
    max_val = max(hours) if any(hours) else 1
    bars = []
    for h in range(24):
        bar_h = round((hours[h] / max_val) * 60) if max_val else 0
        x = 42 + h * 12
        y = 160 - bar_h
        bars.append(f'<rect x="{x}" y="{y}" width="9" height="{max(bar_h,1)}"/>')
    return f"""<svg width="360" height="200" viewBox="0 0 360 200" xmlns="http://www.w3.org/2000/svg">
  <rect x="1" y="1" width="358" height="198" rx="12" fill="#0d1117" stroke="#2d3341" stroke-width="1"/>
  <text x="24" y="34" font-family="Segoe UI, Verdana, sans-serif" font-size="17" font-weight="700" fill="#4a90e2">Commits (UTC +{UTC_OFFSET_HOURS:.2f})</text>
  <text x="336" y="34" font-family="Segoe UI, Verdana, sans-serif" font-size="10" fill="#8b949e" text-anchor="end">per day hour</text>
  <line x1="40" y1="160" x2="336" y2="160" stroke="#30363d" stroke-width="1"/>
  <g fill="#3fb950">
    {''.join(bars)}
  </g>
  <g font-family="Segoe UI, Verdana, sans-serif" font-size="10" fill="#8b949e">
    <text x="42" y="176">0</text>
    <text x="146" y="176">6</text>
    <text x="245" y="176">12</text>
    <text x="322" y="176">23</text>
  </g>
</svg>
"""


def render_contributions_card(weeks):
    days = []
    for week in weeks:
        for day in week["contributionDays"]:
            days.append(day["contributionCount"])
    if not days:
        days = [0] * 52
    max_val = max(days) or 1
    n = len(days)
    width_span = 520
    step = width_span / max(n - 1, 1)
    points = []
    for i, v in enumerate(days):
        x = 40 + i * step
        y = 153 - (v / max_val) * 108
        points.append((x, y))
    line_path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
    area_path = line_path + f" L{points[-1][0]:.1f},153 L{points[0][0]:.1f},153 Z"

    today = datetime.date.today()
    labels = []
    for i in range(6):
        months_back = 10 - i * 2
        d = today - datetime.timedelta(days=months_back * 30)
        x = 40 + (i / 5) * width_span
        labels.append(f'<text x="{x:.0f}" y="170">{d.strftime("%y/%m")}</text>')

    return f"""<svg width="600" height="180" viewBox="0 0 600 180" xmlns="http://www.w3.org/2000/svg">
  <rect x="1" y="1" width="598" height="178" rx="12" fill="#0d1117" stroke="#2d3341" stroke-width="1"/>
  <text x="24" y="32" font-family="Segoe UI, Verdana, sans-serif" font-size="16" font-weight="700" fill="#4a90e2">{USERNAME}</text>
  <text x="576" y="26" font-family="Segoe UI, Verdana, sans-serif" font-size="11" fill="#8b949e" text-anchor="end">contributions in the last year</text>
  <line x1="40" y1="153" x2="560" y2="153" stroke="#30363d" stroke-width="1"/>
  <path d="{area_path}" fill="#238636" fill-opacity="0.55"/>
  <path d="{line_path}" fill="none" stroke="#3fb950" stroke-width="2"/>
  <g font-family="Segoe UI, Verdana, sans-serif" font-size="10" fill="#8b949e">
    {''.join(labels)}
  </g>
</svg>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print(f"Fetching data for {USERNAME}...")
    repos = fetch_repos()
    stars = total_stars(repos)
    langs = language_breakdown(repos)

    contrib = fetch_contributions()
    if contrib:
        commits = contrib["totalCommitContributions"]
        prs = contrib["totalPullRequestContributions"]
        issues = contrib["totalIssueContributions"]
        contributed_to = contrib["totalRepositoriesWithContributedCommits"]
        weeks = contrib["contributionCalendar"]["weeks"]
    else:
        print("WARN: contributions query failed, using zeros", file=sys.stderr)
        commits = prs = issues = contributed_to = 0
        weeks = []

    hours = commit_hour_histogram(repos)

    out_dir = os.environ.get("OUTPUT_DIR", ".")
    with open(os.path.join(out_dir, "stats-card.svg"), "w") as f:
        f.write(render_stats_card(stars, commits, prs, issues, contributed_to))
    with open(os.path.join(out_dir, "languages-card.svg"), "w") as f:
        f.write(render_languages_card(langs))
    with open(os.path.join(out_dir, "commits-by-hour-card.svg"), "w") as f:
        f.write(render_commits_by_hour_card(hours))
    with open(os.path.join(out_dir, "contributions-card.svg"), "w") as f:
        f.write(render_contributions_card(weeks))

    print("Done. Stars:", stars, "Commits:", commits, "PRs:", prs, "Issues:", issues, "Contributed to:", contributed_to)


if __name__ == "__main__":
    main()
