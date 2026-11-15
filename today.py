"""
Builds dark_mode.svg and light_mode.svg: a neofetch-style GitHub profile card.
Run locally:   python today.py               (stats show as "--")
In Actions:    GITHUB_TOKEN=... python today.py   (stats fetched live)
"""
import os, datetime, json, urllib.request
from xml.sax.saxutils import escape

USER = "LeoHeinn"
# Date for the "Uptime" line. Set this to your birthday if you want Andrew-style age uptime.
UPTIME_SINCE = datetime.date(2025, 9, 1)   

INFO = [
    ("title", "leo@heinaung"),
    ("OS", "macOS"),
    ("Uptime", None),  # filled in from UPTIME_SINCE
    ("Host", "Liberty IT"),
    ("Kernel", "Software Engineering Intern"),
    ("IDE", "IntelliJ IDEA, VS Code"),
    ("Terminal", "zsh, bash"),

    ("", ""),
    ("Languages.Programming", "Java, C++, TypeScript, React, Express"),
    ("Languages.Computer", "SQL, JSON, YAML, MD, shell"),
    ("Languages.Real", "English"),

    ("", ""),
    ("Hobbies.Software", "Claude Code, Spotify"),
    ("Hobbies.Hardware", "Overclocking, Undervolting"),


    ("", ""),
    ("section", "Contact"),
    ("Email.Personal", "leo.he1nn.contact@gmail.com"),
    ("LinkedIn", "linkedin.com/in/leoheinn/"),
    ("LeetCode", "leetcode.com/u/FTi5DjCwOI/"),

    ("", ""),
    ("section", "Config"),
    ("Keyboard", "Keychron K2, Wooting 60HE"),
    ("Fuel", "Red Bull, Caffeine"),
    ("Games", "Sheepy : Short Adventure, eFootball"),
    ("Favourite.DS", "HashMap, TreeSet"),
]

COLS = 64          # characters per info line
FONT = 16
LINE = 20
CHAR_W = 9.62      # approx advance width of a 16px monospace glyph
ART_X = 15
ART_FONT = 13     # portrait is drawn smaller for more detail
ART_LINE = 16
INFO_X = 510

THEMES = {
    "dark":  dict(bg="#161b22", text="#c9d1d9", key="#ffa657", val="#a5d6ff",
                  dots="#616e7f", add="#3fb950", dele="#f85149",
                  art="#c9d1d9", frame="#ffffff"),
    "light": dict(bg="#f6f8fa", text="#24292f", key="#953800", val="#0a3069",
                  dots="#c2cfde", add="#1a7f37", dele="#cf222e",
                  art="#424a53", frame="#0d1117"),
}


def uptime(since):
    t = datetime.date.today()
    y = t.year - since.year
    m = t.month - since.month
    d = t.day - since.day
    if d < 0:
        m -= 1
        prev = (t.replace(day=1) - datetime.timedelta(days=1))
        d += prev.day
    if m < 0:
        y -= 1
        m += 12
    pl = lambda n, w: f"{n} {w}{'' if n == 1 else 's'}"
    return f"{pl(y,'year')}, {pl(m,'month')}, {pl(d,'day')}"


# ---------------------------------------------------------------- GitHub stats
def gql(query, variables, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}"})
    with urllib.request.urlopen(req) as r:
        out = json.load(r)
    if "errors" in out:
        raise RuntimeError(out["errors"])
    return out["data"]


def rest(path, token):
    req = urllib.request.Request(f"https://api.github.com{path}",
                                 headers={"Authorization": f"bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return r.status, (json.load(r) if r.status == 200 else None)


def fetch_stats(token):
    d = gql("""query($login:String!){ user(login:$login){
        createdAt followers{totalCount}
        repositories(first:100, ownerAffiliations:OWNER){ totalCount
            nodes{ nameWithOwner stargazerCount } }
        repositoriesContributedTo(first:1, contributionTypes:[COMMIT,PULL_REQUEST,REPOSITORY]){ totalCount } } }""",
            {"login": USER}, token)["user"]
    repos = d["repositories"]
    stars = sum(n["stargazerCount"] for n in repos["nodes"])

    # commits: sum every year since the account was created
    commits = 0
    start = int(d["createdAt"][:4])
    for year in range(start, datetime.date.today().year + 1):
        c = gql("""query($login:String!,$from:DateTime!,$to:DateTime!){ user(login:$login){
            contributionsCollection(from:$from,to:$to){ totalCommitContributions restrictedContributionsCount } } }""",
                {"login": USER, "from": f"{year}-01-01T00:00:00Z", "to": f"{year}-12-31T23:59:59Z"}, token)
        cc = c["user"]["contributionsCollection"]
        commits += cc["totalCommitContributions"]

    # lines of code: your additions/deletions across your own repos
    add = dele = 0
    for n in repos["nodes"]:
        for _ in range(3):  # stats endpoint returns 202 while GitHub computes it
            status, body = rest(f"/repos/{n['nameWithOwner']}/stats/contributors", token)
            if status == 200:
                break
            import time; time.sleep(3)
        for c in body or []:
            if c.get("author") and c["author"]["login"].lower() == USER.lower():
                add += sum(w["a"] for w in c["weeks"])
                dele += sum(w["d"] for w in c["weeks"])
    return dict(repos=repos["totalCount"], contributed=d["repositoriesContributedTo"]["totalCount"],
                stars=stars, commits=commits, followers=d["followers"]["totalCount"],
                loc=add - dele, add=add, dele=dele)


# ---------------------------------------------------------------- SVG building
def t(cls, s):
    return f'<tspan class="{cls}">{escape(s)}</tspan>'


def kv_line(key, val, width=COLS):
    """'. Key: ........ value' padded to exactly `width` chars."""
    head = f". {key}:"
    gap = width - len(head) - len(val) - 2
    dots = " " + "." * max(gap, 1) + " "
    return t("cc", ". ") + t("key", key) + ":" + t("cc", dots) + t("value", val)


def header_line(title, width=COLS):
    lead = "- " if title != "leo@heinaung" else ""
    rest = width - len(lead) - len(title) - 4
    return lead + escape(title) + " " + "-" * max(rest, 1) + "-—-"


def stat_pair(k1, v1, k2, v2):
    left = f". {k1}: "
    lpad = 31 - len(left) - len(v1)
    right = f" | {k2}: "
    rpad = COLS - 31 - len(right) - len(v2)
    return (t("cc", ". ") + t("key", k1) + ":" + t("cc", " " + "." * (lpad - 1) + " ") + t("value", v1)
            + " | " + t("key", k2) + ":" + t("cc", " " + "." * (rpad - 1) + " ") + t("value", v2))


def build(theme, s):
    c = THEMES[theme]
    here = os.path.dirname(os.path.abspath(__file__))
    art = open(os.path.join(here, "ascii.txt")).read().split("\n")
    gpath = os.path.join(here, "glasses.txt")
    frames = open(gpath).read().split("\n") if os.path.exists(gpath) else []
    fmt = lambda v: "--" if v is None else f"{v:,}"

    lines = []
    for key, val in INFO:
        if key == "title":
            lines.append(header_line(val))
        elif key == "section":
            lines.append(header_line(val))
        elif key == "":
            lines.append(t("cc", ". "))
        elif key == "Uptime":
            lines.append(kv_line(key, uptime(UPTIME_SINCE)))
        elif key == "stats1":
            r = f"{fmt(s['repos'])} {{Contributed: {fmt(s['contributed'])}}}"
            lines.append(stat_pair("Repos", r, "Stars", fmt(s["stars"])))
        elif key == "stats2":
            lines.append(stat_pair("Commits", fmt(s["commits"]), "Followers", fmt(s["followers"])))
        elif key == "loc":
            tail = f"{fmt(s['loc'])} ( {fmt(s['add'])}++, {fmt(s['dele'])}-- )"
            head = ". Lines of Code on GitHub:"
            dots = COLS - len(head) - len(tail) - 2
            lines.append(t("cc", ". ") + t("key", "Lines of Code on GitHub") + ":" + t("cc", " " + "." * max(dots, 1) + " ")
                         + t("value", f"{fmt(s['loc'])}") + " ( " + t("addColor", f"{fmt(s['add'])}++") + ", "
                         + t("delColor", f"{fmt(s['dele'])}--") + " )")
        else:
            lines.append(kv_line(key, val))

    height = max(len(art) * ART_LINE, len(lines) * LINE) + 40
    width = INFO_X + COLS * CHAR_W + 20
    info_top = 30 + max(0, (len(art) * ART_LINE - len(lines) * LINE) // 2)

    out = [f'<?xml version="1.0" encoding="utf-8"?>',
           f'<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,\'Courier New\',monospace" '
           f'width="{width:.0f}px" height="{height}px" font-size="{FONT}px">',
           f'<style>@font-face{{src:local(\'Consolas\'),local(\'Consolas Bold\');font-family:\'ConsolasFallback\';'
           f'font-display:swap;-webkit-size-adjust:109%;size-adjust:109%;}}'
           f'.key{{fill:{c["key"]};}}.value{{fill:{c["val"]};}}.addColor{{fill:{c["add"]};}}'
           f'.delColor{{fill:{c["dele"]};}}.cc{{fill:{c["dots"]};}}.frame{{fill:{c["frame"]};font-weight:bold;}}text,tspan{{white-space:pre;}}</style>',
           f'<rect width="{width:.0f}px" height="{height}px" fill="{c["bg"]}" rx="15"/>']
    out.append(f'<text x="{ART_X}" y="30" fill="{c["art"]}" font-size="{ART_FONT}px" class="ascii">')
    for i, row in enumerate(art):
        fr = frames[i] if i < len(frames) else ""
        runs, cur, cur_is = [], "", None
        for j, ch in enumerate(row):
            is_f = j < len(fr) and fr[j] != " "
            if is_f != cur_is and cur:
                runs.append((cur_is, cur)); cur = ""
            cur += ch; cur_is = is_f
        if cur: runs.append((cur_is, cur))
        body = "".join(f'<tspan class="frame">{escape(r)}</tspan>' if f else escape(r) for f, r in runs)
        out.append(f'<tspan x="{ART_X}" y="{30 + i*ART_LINE}">{body}</tspan>')
    out.append('</text>')
    out.append(f'<text x="{INFO_X}" y="{info_top}" fill="{c["text"]}">')
    for i, ln in enumerate(lines):
        out.append(f'<tspan x="{INFO_X}" y="{info_top + i*LINE}">{ln}</tspan>')
    out.append('</text></svg>')
    return "\n".join(out)


if __name__ == "__main__":
    token = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    empty = dict.fromkeys(["repos", "contributed", "stars", "commits", "followers", "loc", "add", "dele"])
    stats = empty  # stats lines removed from the card, so skip the API
    here = os.path.dirname(os.path.abspath(__file__))
    for theme in THEMES:
        with open(os.path.join(here, f"{theme}_mode.svg"), "w") as f:
            f.write(build(theme, stats))
    print("written", stats)
