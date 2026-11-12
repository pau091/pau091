"""Genera assets/stats.svg y assets/activity.svg con datos reales de GitHub.

Se ejecuta a diario desde .github/workflows/stats.yml. Solo usa la librería estándar.
Para probar el diseño sin conexión: python scripts/stats.py --demo
"""
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USER = os.environ.get("GH_USER", "pau091")

BG, CARD, BORDER = "#0b0911", "#15111e", "#2b2140"
PURPLE, PURPLE_D, LILAC = "#c06cff", "#7b3fbf", "#e4b8ff"
TEXT, MUTED = "#ece6f7", "#8c80a6"
LANG_COLORS = ["#c06cff", "#e4b8ff", "#9b5de5", "#7b3fbf", "#5a2d91", "#3d2366"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}"""


def fetch():
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        sys.exit(f"Error de la API: {body['errors']}")
    u = body["data"]["user"]
    cc = u["contributionsCollection"]
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    langs = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    return {
        "contributions": cc["contributionCalendar"]["totalContributions"],
        "commits": cc["totalCommitContributions"],
        "repos": u["repositories"]["totalCount"],
        "stars": sum(r["stargazerCount"] for r in u["repositories"]["nodes"]),
        "followers": u["followers"]["totalCount"],
        "langs": sorted(langs.items(), key=lambda kv: -kv[1]),
        "days": [(d["date"], d["contributionCount"]) for d in days],
    }


def demo():
    today = dt.date.today()
    days = [((today - dt.timedelta(days=i)).isoformat(), (i * 7) % 5 if i % 3 else 0) for i in range(364, -1, -1)]
    return {"contributions": 104, "commits": 88, "repos": 11, "stars": 9, "followers": 3,
            "langs": [("Java", 900), ("JavaScript", 500), ("Python", 300), ("HTML", 200), ("CSS", 120), ("Shell", 10)],
            "days": days}


def style():
    fonts = json.loads((ROOT / "scripts" / "fonts.json").read_text())
    faces = "".join(
        f"@font-face{{font-family:'M';font-weight:{w};src:url(data:font/woff;base64,{b}) format('woff');}}"
        for w, b in fonts.items()
    )
    return f"<style>{faces} text{{font-family:'M','Montserrat','Segoe UI',Arial,sans-serif;}}</style>"


DEFS = f"""<defs>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <linearGradient id="col" x1="0" y1="1" x2="0" y2="0">
    <stop offset="0" stop-color="{PURPLE_D}" stop-opacity="0.55"/><stop offset="1" stop-color="{PURPLE}"/>
  </linearGradient>
</defs>"""


def card_frame(w, h, title, right=""):
    return f"""  <rect width="{w}" height="{h}" rx="18" fill="{CARD}" stroke="{BORDER}"/>
  <text x="32" y="44" font-size="15" font-weight="800" fill="{TEXT}" letter-spacing="3">{title}</text>
  <text x="{w-32}" y="44" text-anchor="end" font-size="11" font-weight="700" fill="{MUTED}" letter-spacing="2">{right}</text>
  <line x1="32" y1="58" x2="{w-32}" y2="58" stroke="{BORDER}"/>
  <line x1="32" y1="58" x2="140" y2="58" stroke="{PURPLE}" stroke-width="2" filter="url(#glow)"/>"""


def stats_svg(d):
    W, H = 1000, 250
    blocks = [
        ("CONTRIBUCIONES", d["contributions"], "último año"),
        ("COMMITS", d["commits"], "último año"),
        ("REPOSITORIOS", d["repos"], "públicos"),
        ("ESTRELLAS", d["stars"], "recibidas"),
    ]
    out = ""
    bw = 104
    for i, (label, val, sub) in enumerate(blocks):
        x = 32 + i * (bw + 14)
        out += f"""
  <rect x="{x}" y="80" width="{bw}" height="130" rx="12" fill="{BG}" stroke="{BORDER}"/>
  <text x="{x+bw/2}" y="134" text-anchor="middle" font-size="34" font-weight="800" fill="{LILAC}" filter="url(#glow)">{val}</text>
  <text x="{x+bw/2}" y="166" text-anchor="middle" font-size="9.5" font-weight="700" fill="{TEXT}" letter-spacing="1">{label}</text>
  <text x="{x+bw/2}" y="186" text-anchor="middle" font-size="10" font-weight="500" fill="{MUTED}">{sub}</text>"""

    # Lenguajes más usados
    lx, lw = 530, 438
    langs = d["langs"][:6]
    total = sum(s for _, s in langs) or 1
    out += f"""
  <text x="{lx}" y="96" font-size="11" font-weight="700" fill="{MUTED}" letter-spacing="2">LENGUAJES MÁS USADOS</text>
  <rect x="{lx}" y="110" width="{lw}" height="12" rx="6" fill="{BORDER}"/>
  <clipPath id="lc"><rect x="{lx}" y="110" width="{lw}" height="12" rx="6"/></clipPath>
  <g clip-path="url(#lc)">"""
    x = lx
    for i, (name, size) in enumerate(langs):
        w = lw * size / total
        out += f'<rect x="{x:.1f}" y="110" width="{w + 0.5:.1f}" height="12" fill="{LANG_COLORS[i]}"/>'
        x += w
    out += "</g>"
    for i, (name, size) in enumerate(langs):
        cx = lx + (i % 3) * 146
        cy = 152 + (i // 3) * 34
        pct = 100 * size / total
        out += f"""
  <circle cx="{cx+6}" cy="{cy-4}" r="5" fill="{LANG_COLORS[i]}"/>
  <text x="{cx+18}" y="{cy}" font-size="13" font-weight="700" fill="{TEXT}">{name}</text>
  <text x="{cx+18}" y="{cy+15}" font-size="10" font-weight="500" fill="{MUTED}">{pct:.1f}%</text>"""

    stamp = dt.date.today().strftime("%d/%m/%Y")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
{style()}{DEFS}
{card_frame(W, H, "PLAYER STATS", "ACTUALIZADO " + stamp)}{out}
</svg>"""


def activity_svg(d):
    W, H = 1000, 300
    days = d["days"][-30:]
    peak = max([c for _, c in days] + [1])
    cx0, cy0, cw, ch = 60, 90, 908, 160
    n = len(days)
    slot = cw / n
    bw = slot * 0.62
    grid = ""
    for i in range(5):
        y = cy0 + ch * i / 4
        val = round(peak * (4 - i) / 4)
        grid += f'<line x1="{cx0}" y1="{y:.1f}" x2="{cx0+cw}" y2="{y:.1f}" stroke="{BORDER}" stroke-dasharray="3 5"/>'
        grid += f'<text x="{cx0-12}" y="{y+4:.1f}" text-anchor="end" font-size="10" font-weight="500" fill="{MUTED}">{val}</text>'
    bars = ""
    for i, (date, c) in enumerate(days):
        x = cx0 + i * slot + (slot - bw) / 2
        h = ch * c / peak
        y = cy0 + ch - h
        if c:
            bars += f"""<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="4" fill="url(#col)">
    <animate attributeName="height" from="0" to="{h:.1f}" dur="1s" fill="freeze"/>
    <animate attributeName="y" from="{cy0+ch}" to="{y:.1f}" dur="1s" fill="freeze"/></rect>
  <rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" height="5" rx="2.5" fill="{LILAC}" filter="url(#glow)"/>"""
        else:
            bars += f'<rect x="{x:.1f}" y="{cy0+ch-3}" width="{bw:.1f}" height="3" rx="1.5" fill="{BORDER}"/>'
        if i % 5 == 0 or i == n - 1:
            label = dt.date.fromisoformat(date).strftime("%d/%m")
            bars += f'<text x="{x + bw/2:.1f}" y="{cy0+ch+22}" text-anchor="middle" font-size="10" font-weight="500" fill="{MUTED}">{label}</text>'
    total30 = sum(c for _, c in days)
    active = sum(1 for _, c in days if c)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
{style()}{DEFS}
{card_frame(W, H, "HABIT TRACKER", f"{total30} CONTRIBUCIONES · {active} DÍAS ACTIVOS · ÚLTIMOS 30 DÍAS")}
  {grid}
  {bars}
</svg>"""


def main():
    data = demo() if "--demo" in sys.argv else fetch()
    (ROOT / "assets" / "stats.svg").write_text(stats_svg(data))
    (ROOT / "assets" / "activity.svg").write_text(activity_svg(data))
    print("SVG generados")


if __name__ == "__main__":
    main()
