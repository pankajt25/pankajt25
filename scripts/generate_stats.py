import os, json, urllib.request, datetime

NOW = datetime.datetime.now(datetime.timezone.utc)
USER = os.environ.get("GH_USER", "pankajt25")
TOKEN = os.environ.get("STATS_TOKEN") or os.environ["GITHUB_TOKEN"]
NUM, TITLE, LABEL = "#58A6FF", "#E6EDF3", "#8B949E"   # NUM = number colour, e.g. "#48BB78" for green

QUERY = """
query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){
  repos: repositories(ownerAffiliations:OWNER,privacy:PUBLIC,first:100){totalCount nodes{stargazerCount}}
  pullRequests{totalCount}
  contributionsCollection{contributionCalendar{weeks{contributionDays{contributionCount}}}}
  year: contributionsCollection(from:$from,to:$to){contributionCalendar{totalContributions}}
}}"""

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": QUERY, "variables": {"login": USER, "from": f"{NOW.year}-01-01T00:00:00Z", "to": NOW.strftime("%Y-%m-%dT%H:%M:%SZ")}}).encode(),
    headers={"Authorization": f"bearer {TOKEN}"},
)
u = json.load(urllib.request.urlopen(req))["data"]["user"]

cal = u["contributionsCollection"]["contributionCalendar"]
counts = [d["contributionCount"] for w in cal["weeks"] for d in w["contributionDays"]]

longest = run = 0
for c in counts:
    run = run + 1 if c > 0 else 0
    longest = max(longest, run)

i = len(counts) - 1
if i >= 0 and counts[i] == 0:      # today may not have contributions yet
    i -= 1
current = 0
while i >= 0 and counts[i] > 0:
    current += 1
    i -= 1

stars = sum(r["stargazerCount"] for r in u["repos"]["nodes"])
items = [
    (str(u["year"]["contributionCalendar"]["totalContributions"]), f"Contributions ({NOW.year})"),
    (f"{current}d", "Current streak"),
    (f"{longest}d", "Longest streak"),
    (str(stars), "Stars earned"),
    (str(u["repos"]["totalCount"]), "Repositories"),
    (str(u["pullRequests"]["totalCount"]), "Pull requests"),
]

stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%d %b %Y')
W, H = 1000, 190
cols = ""
for n, (v, l) in enumerate(items):
    x = W / len(items) * (n + 0.5)
    cols += (f'<text x="{x:.0f}" y="112" fill="{NUM}" font-size="40" font-weight="700" text-anchor="middle">{v}</text>'
             f'<text x="{x:.0f}" y="142" fill="{LABEL}" font-size="15" text-anchor="middle">{l}</text>')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Ubuntu, Helvetica, Arial, sans-serif">
<rect x="0.75" y="0.75" width="{W-1.5}" height="{H-1.5}" rx="10" fill="#0D1117" stroke="#30363D" stroke-width="1.5"/>
<text x="30" y="46" fill="{TITLE}" font-size="20" font-weight="600">{USER}'s GitHub Stats</text>
{cols}
<text x="{W-24}" y="{H-14}" fill="{LABEL}" font-size="11" text-anchor="end">Updated {stamp} UTC</text>
</svg>'''

os.makedirs("assets", exist_ok=True)
open("assets/stats.svg", "w").write(svg)
