"""2027 PTO planner PDF generator (US holidays).

Usage: python3 make_planner_us.py --pto 15 --set fed --out planner-15.pdf
Same planning rules as /en/ on the site. Weeks start on Sunday.
"""
import argparse
import bisect
import datetime as dt
import os

from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

YEAR = 2027
FED = {
    (1, 1): "New Year's Day", (1, 18): "MLK Day", (2, 15): "Presidents' Day", (5, 31): "Memorial Day",
    (6, 18): "Juneteenth (obs.)", (7, 5): "July 4th (obs.)", (9, 6): "Labor Day", (10, 11): "Columbus Day",
    (11, 11): "Veterans Day", (11, 25): "Thanksgiving", (12, 24): "Christmas (obs.)", (12, 31): "New Year's (obs.)",
}
PRIV = {
    (1, 1): "New Year's Day", (5, 31): "Memorial Day", (7, 5): "July 4th (obs.)", (9, 6): "Labor Day",
    (11, 25): "Thanksgiving", (11, 26): "Day after Thanksgiving", (12, 24): "Christmas (obs.)",
}
HOL = FED
DOW = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
DOWL = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONL = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
MAXB = 30


def sun_col(d):
    """Sunday = 0."""
    return (d.weekday() + 1) % 7

INK = HexColor("#1c2230")
MUTED = HexColor("#6b7180")
LINE = HexColor("#e4e2dc")
RED = HexColor("#d8342c")
RED_SOFT = HexColor("#fde6e3")
LEAVE = HexColor("#1f6feb")
SPAN = HexColor("#fff3c4")
PAPER = HexColor("#fbfaf7")

W, H = 768, 1024  # 4:3 portrait, GoodNotes default


def build_days():
    days = []
    d = dt.date(YEAR, 1, 1)
    while d <= dt.date(YEAR + 1, 1, 2):  # keep the Jan 1-2, 2028 weekend so the Christmas break is not cut off
        hol = HOL.get((d.month, d.day)) if d.year == YEAR else None
        days.append({"date": d, "hol": hol, "off": d.weekday() >= 5 or hol is not None})
        d += dt.timedelta(days=1)
    return days


def plan(days, budget):
    n = len(days)
    blocks, i = [], 0
    while i < n:
        if days[i]["off"]:
            j = i
            while j + 1 < n and days[j + 1]["off"]:
                j += 1
            blocks.append((i, j))
            i = j
        i += 1
    wins = []
    for a in range(len(blocks)):
        off = 0
        for b in range(a, len(blocks)):
            off += blocks[b][1] - blocks[b][0] + 1
            s, e = blocks[a][0], blocks[b][1]
            length = e - s + 1
            if length > 23:
                break
            cost = length - off
            if 1 <= cost <= MAXB:
                wins.append({"s": s, "e": e, "len": length, "cost": cost,
                             "score": round(length ** 1.3 * 1000) - cost})
    wins.sort(key=lambda w: (w["e"], w["s"]))
    ends = [w["e"] for w in wins]
    before = [bisect.bisect_left(ends, w["s"]) for w in wins]
    dp = [[0] * (budget + 1) for _ in range(len(wins) + 1)]
    for k in range(1, len(wins) + 1):
        w, q = wins[k - 1], before[k - 1]
        for b in range(budget + 1):
            v = dp[k - 1][b]
            if w["cost"] <= b:
                v = max(v, dp[q][b - w["cost"]] + w["score"])
            dp[k][b] = v
    picked, k, b = [], len(wins), budget
    while k > 0:
        if dp[k][b] == dp[k - 1][b]:
            k -= 1
            continue
        w = wins[k - 1]
        picked.append(w)
        b -= w["cost"]
        k = before[k - 1]
    return list(reversed(picked))


def fmt(days, i):
    d = days[i]["date"]
    return f"{DOW[sun_col(d)]} {MON[d.month - 1]} {d.day}" + (", 2028" if d.year > YEAR else "")


def reason(days, w):
    names = []
    for i in range(w["s"], w["e"] + 1):
        h = days[i]["hol"]
        if h:
            base = h.replace(" (obs.)", "")
            if base not in names:
                names.append(base)
    return " · ".join(names) if names else "Weekend bridge"


def register_fonts():
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    pdfmetrics.registerFont(TTFont("Display", os.path.join(here, "archivo-black.ttf")))
    pdfmetrics.registerFont(TTFont("Body", os.path.join(here, "plex-r.ttf")))
    pdfmetrics.registerFont(TTFont("Bold", os.path.join(here, "plex-b.ttf")))


def page_bg(c):
    c.setFillColor(PAPER)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(RED)
    c.rect(0, H - 8, W, 8, stroke=0, fill=1)


def month_grid(c, days, marks, month, x, y, w, h, big, link_prefix=None):
    """(x, y) is the top-left corner. big=True draws the large monthly-page cells."""
    first = next(i for i, d in enumerate(days) if d["date"].month == month)
    start_col = sun_col(days[first]["date"])
    count = sum(1 for d in days if d["date"].month == month and d["date"].year == YEAR)
    rows = (start_col + count + 6) // 7
    head = 22 if big else 12
    cw, ch = w / 7, (h - head) / rows
    c.setFont("Bold" if big else "Body", 11 if big else 6.5)
    for k, name in enumerate(DOW):
        c.setFillColor(RED if k == 0 else MUTED)
        c.drawCentredString(x + cw * k + cw / 2, y - head + (7 if big else 4), name)
    for n in range(count):
        i = first + n
        d = days[i]
        pos = start_col + n
        r, col = divmod(pos, 7)
        cx, cy = x + col * cw, y - head - (r + 1) * ch
        if marks["span"][i]:
            c.setFillColor(RED_SOFT if d["hol"] else SPAN)
            c.rect(cx + 1, cy + 1, cw - 2, ch - 2, stroke=0, fill=1)
        if marks["leave"][i]:
            c.setFillColor(LEAVE)
            c.rect(cx + 1, cy + 1, cw - 2, ch - 2, stroke=0, fill=1)
        if big:
            c.setStrokeColor(LINE)
            c.setLineWidth(0.6)
            c.rect(cx, cy, cw, ch, stroke=1, fill=0)
        color = INK
        if sun_col(d["date"]) == 0 or d["hol"]:
            color = RED
        elif sun_col(d["date"]) == 6:
            color = MUTED
        if marks["leave"][i]:
            color = HexColor("#ffffff")
        c.setFillColor(color)
        if big:
            c.setFont("Bold", 13)
            c.drawString(cx + 6, cy + ch - 17, str(d["date"].day))
            c.setFont("Body", 7.5)
            label = "PTO" if marks["leave"][i] else (d["hol"] or "")
            if label:
                c.drawString(cx + 6, cy + ch - 30, label[:16])
            c.linkAbsolute("", f"w{week_of(days, i)}", (cx, cy, cx + cw, cy + ch))
        else:
            c.setFont("Bold" if d["hol"] or marks["leave"][i] else "Body", 7)
            c.drawCentredString(cx + cw / 2, cy + ch / 2 - 2.5, str(d["date"].day))
    if link_prefix:
        c.linkAbsolute("", f"{link_prefix}{month}", (x, y - h, x + w, y + 14))


def week_of(days, i):
    """Sunday-start week number. Week 0 holds Jan 1."""
    return (i + sun_col(days[0]["date"])) // 7


def week_page(c, days, marks, picked, k):
    off = sun_col(days[0]["date"])
    idx = [k * 7 + j - off for j in range(7)]
    real = [i for i in idx if 0 <= i < len(days)]
    first, last = days[real[0]]["date"], days[real[-1]]["date"]
    page_bg(c)
    c.bookmarkPage(f"w{k}")
    c.setFillColor(INK)
    c.setFont("Display", 34)
    c.drawString(48, H - 82, f"{MON[first.month - 1]} {first.day} – {MON[last.month - 1]} {last.day}")
    c.setFillColor(MUTED)
    c.setFont("Body", 11)
    c.drawRightString(W - 48, H - 76, f"← {MONL[first.month - 1]}")
    c.linkAbsolute("", f"m{first.month}", (W - 140, H - 82, W - 44, H - 64))
    top, row = H - 112, (H - 112 - 48) / 7
    for j, i in enumerate(idx):
        y0 = top - (j + 1) * row
        c.setStrokeColor(LINE)
        c.setLineWidth(0.8)
        c.line(48, y0, W - 48, y0)
        if not 0 <= i < len(days):
            continue
        d = days[i]
        if marks["span"][i]:
            c.setFillColor(RED_SOFT if d["hol"] else SPAN)
            c.rect(48, y0 + 1, 118, row - 2, stroke=0, fill=1)
        if marks["leave"][i]:
            c.setFillColor(LEAVE)
            c.rect(48, y0 + 1, 118, row - 2, stroke=0, fill=1)
        wd = sun_col(d["date"])
        color = HexColor("#ffffff") if marks["leave"][i] else (RED if wd == 0 or d["hol"] else (MUTED if wd == 6 else INK))
        c.setFillColor(color)
        c.setFont("Display", 40)
        c.drawString(60, y0 + row - 50, str(d["date"].day))
        c.setFont("Bold", 12)
        c.drawString(60, y0 + row - 70, DOWL[wd])
        tag = "PTO day" if marks["leave"][i] else (d["hol"] or "")
        if tag:
            c.setFont("Body", 9)
            c.drawString(60, y0 + 12, tag[:20])
        c.setStrokeColor(LINE)
        c.setLineWidth(0.5)
        for t in range(1, 4):
            ly = y0 + row - t * (row / 4)
            c.line(184, ly, W - 48, ly)
    c.showPage()


def make(budget, out, hset="fed"):
    global HOL
    HOL = FED if hset == "fed" else PRIV
    register_fonts()
    days = build_days()
    picked = plan(days, budget)
    n = len(days)
    marks = {"span": [False] * n, "leave": [False] * n}
    for w in picked:
        for i in range(w["s"], w["e"] + 1):
            marks["span"][i] = True
            if not days[i]["off"]:
                marks["leave"][i] = True
    total = sum(w["len"] for w in picked)
    used = sum(w["cost"] for w in picked)
    longest = max((w["len"] for w in picked), default=0)

    c = canvas.Canvas(out, pagesize=(W, H))
    c.setTitle(f"2027 PTO Hack Planner ({budget} PTO days)")

    # Cover
    page_bg(c)
    c.bookmarkPage("cover")
    c.setFillColor(MUTED)
    c.setFont("Bold", 16)
    c.drawString(64, H - 120, "2027 PTO HACK PLANNER")
    c.setFillColor(INK)
    c.setFont("Display", 54)
    c.drawString(64, H - 210, f"{budget} PTO days =")
    c.setFillColor(RED)
    c.setFont("Display", 150)
    c.drawString(56, H - 380, f"{total} days")
    c.setFillColor(INK)
    c.setFont("Display", 54)
    c.drawString(64, H - 460, "off in 2027")
    c.setFillColor(MUTED)
    c.setFont("Body", 15)
    c.drawString(64, H - 505, f"{used} PTO used · longest break {longest} days · {budget - used} PTO left")
    y = H - 580
    for w in sorted(picked, key=lambda w: w["s"])[:10]:
        c.setFillColor(RED)
        c.setFont("Display", 30)
        c.drawString(64, y, f"{w['len']}d")
        c.setFillColor(INK)
        c.setFont("Bold", 15)
        c.drawString(160, y + 8, f"{fmt(days, w['s'])} – {fmt(days, w['e'])}")
        c.setFillColor(MUTED)
        c.setFont("Body", 11)
        c.drawString(160, y - 9, f"{reason(days, w)} · {w['cost']} PTO")
        c.linkAbsolute("", f"m{days[w['s']]['date'].month}", (60, y - 14, W - 60, y + 30))
        y -= 52
    c.setFillColor(MUTED)
    c.setFont("Body", 10)
    note = ("2027 observed US federal holidays." if hset == "fed" else
            "Typical company holidays: New Year's, Memorial Day, July 4th, Labor Day, Thanksgiving + Friday, Christmas.")
    c.drawString(64, 48, note + " Check your employer's calendar.")
    c.showPage()

    # Year at a glance
    page_bg(c)
    c.bookmarkPage("year")
    c.setFillColor(INK)
    c.setFont("Display", 40)
    c.drawString(48, H - 80, "2027 at a glance")
    c.setFont("Body", 10)
    c.setFillColor(MUTED)
    c.drawString(48, H - 102, "Tap a month to open it, then tap a date to open its week.   Blue = PTO, yellow = days off, red = holiday")
    gw, gh = (W - 96 - 40) / 3, 190
    for m in range(1, 13):
        r, col = divmod(m - 1, 3)
        x = 48 + col * (gw + 20)
        top = H - 140 - r * (gh + 30)
        c.setFillColor(INK)
        c.setFont("Bold", 13)
        c.drawString(x, top, MONL[m - 1])
        month_grid(c, days, marks, m, x, top - 8, gw, gh - 20, big=False, link_prefix="m")
    c.showPage()

    # Monthly pages
    for m in range(1, 13):
        page_bg(c)
        c.bookmarkPage(f"m{m}")
        c.addOutlineEntry(MONL[m - 1], f"m{m}", level=0)
        c.setFillColor(RED)
        c.setFont("Display", 56)
        c.drawString(48, H - 106, MONL[m - 1])
        c.setFillColor(MUTED)
        c.setFont("Body", 11)
        c.drawRightString(W - 48, H - 100, "← Year at a glance")
        c.linkAbsolute("", "year", (W - 160, H - 106, W - 44, H - 88))
        notes = [w for w in picked if days[w["s"]]["date"].month == m or days[w["e"]]["date"].month == m]
        if notes:
            c.setFont("Bold", 11)
            c.setFillColor(LEAVE)
            txt = "   ".join(f"{fmt(days, w['s'])} – {fmt(days, w['e'])}: {w['len']} days ({w['cost']} PTO)" for w in notes)
            c.drawString(48, H - 140, txt[:100])
        month_grid(c, days, marks, m, 48, H - 160, W - 96, 520, big=True)
        # Note lines
        c.setFillColor(INK)
        c.setFont("Bold", 12)
        c.drawString(48, H - 712, "Notes")
        c.setStrokeColor(LINE)
        c.setLineWidth(0.8)
        yy = H - 740
        while yy > 60:
            c.line(48, yy, W - 48, yy)
            yy -= 30
        c.showPage()

    # Weekly pages (dates on monthly pages link here)
    last2027 = max(i for i, d in enumerate(days) if d["date"].year == YEAR)
    for k in range(week_of(days, last2027) + 1):
        week_page(c, days, marks, picked, k)
    c.save()
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pto", type=int, default=15)
    ap.add_argument("--set", choices=["fed", "company"], default="fed")
    ap.add_argument("--out", default="planner.pdf")
    a = ap.parse_args()
    t = make(a.pto, a.out, a.set)
    print(f"{a.out}: {a.pto} PTO -> {t} days off")
