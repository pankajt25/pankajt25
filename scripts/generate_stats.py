import os, json, urllib.request
from collections import Counter

USER = os.environ.get("GH_USER", "pankajt25")
TOKEN = os.environ["GITHUB_TOKEN"]

QUERY = """
query($login:String!){user(login:$login){
  followers{totalCount}
  repositories(ownerAffiliations:OWNER,isFork:false,first:100,privacy:PUBLIC){
    totalCount
    nodes{stargazerCount languages(first:5,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}
  }
  contributionsCollection{totalCommitContributions totalPullRequestContributions totalIssueContributions restrictedContributionsCount}
}}"""

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
    headers={"Authorization": f"bearer {TOKEN}"},
)
u = json.load(urllib.request.urlopen(req))["data"]["user"]

repos = u["repositories"]["nodes"]
stars = sum(r["stargazerCount"] for r in repos)
c = u["contributionsCollection"]
commits = c["totalCommitContributions"] + c["restrictedContributionsCount"]
langs = Counter()
for r in repos:
    for e in r["languages"]["edges"]:
        langs[e["node"]["name"]] += e["size"]
top = langs.most_common(5)
total = sum(v for _, v in top) or 1

rows = [("Public repos", u["repositories"]["totalCount"]), ("Stars earned", stars),
        ("Commits (last year)", commits), ("Pull requests", c["totalPullRequestContributions"]),
        ("Issues", c["totalIssueContributions"]), ("Followers", u["followers"]["totalCount"])]

palette = ["#E53E3E", "#48BB78", "#ED8936", "#4299E1", "#9F7AEA"]
stats_svg = "".join(
    f'<text x="25" y="{72 + i*24}" fill="#A0AEC0" font-size="13">{k}</text>'
    f'<text x="215" y="{72 + i*24}" fill="#48BB78" font-size="13" font-weight="700" text-anchor="end">{v}</text>'
    for i, (k, v) in enumerate(rows))

bar, x, legend = "", 260, ""
for i, (name, size) in enumerate(top):
    w = 210 * size / total
    bar += f'<rect x="{x:.1f}" y="72" width="{w:.1f}" height="10" fill="{palette[i]}"/>'
    x += w
    legend += (f'<circle cx="266" cy="{104 + i*20}" r="5" fill="{palette[i]}"/>'
               f'<text x="278" y="{108 + i*20}" fill="#A0AEC0" font-size="12">{name} {100*size/total:.1f}%</text>')

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="495" height="235" viewBox="0 0 495 235" font-family="Segoe UI, Ubuntu, sans-serif">
<rect width="495" height="235" rx="8" fill="#090909" stroke="#E53E3E" stroke-width="1.5"/>
<text x="25" y="36" fill="#E53E3E" font-size="18" font-weight="700">{USER}'s GitHub Stats</text>
{stats_svg}
<text x="260" y="58" fill="#E53E3E" font-size="13" font-weight="700">Top Languages</text>
{bar}{legend}
</svg>"""

os.makedirs("assets", exist_ok=True)
open("assets/stats.svg", "w").write(svg)
