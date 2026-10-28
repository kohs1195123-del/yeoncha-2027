"""2027 연차 맞춤 다이어리 PDF 생성기.

사용법: python3 make_diary.py --leave 15 --out diary-15.pdf
연차 개수를 받아 웹 계산기와 같은 규칙으로 연휴 계획을 짜고,
그 계획이 표시된 굿노트용(4:3 세로) 다이어리를 만든다.
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
HOL = {
    (1, 1): "신정", (2, 5): "설날 연휴", (2, 6): "설날", (2, 7): "설날 연휴", (2, 8): "설날 대체공휴일",
    (3, 1): "삼일절", (5, 1): "노동절", (5, 3): "노동절 대체", (5, 5): "어린이날", (5, 13): "부처님오신날",
    (6, 6): "현충일", (7, 17): "제헌절", (7, 19): "제헌절 대체", (8, 15): "광복절", (8, 16): "광복절 대체",
    (9, 14): "추석 연휴", (9, 15): "추석", (9, 16): "추석 연휴", (10, 3): "개천절", (10, 4): "개천절 대체",
    (10, 9): "한글날", (10, 11): "한글날 대체", (12, 25): "성탄절", (12, 27): "성탄절 대체",
}
DOW = ["월", "화", "수", "목", "금", "토", "일"]  # Python weekday 순서

INK = HexColor("#1c2230")
MUTED = HexColor("#6b7180")
LINE = HexColor("#e4e2dc")
RED = HexColor("#d8342c")
RED_SOFT = HexColor("#fde6e3")
LEAVE = HexColor("#1f6feb")
SPAN = HexColor("#fff3c4")
PAPER = HexColor("#fbfaf7")

W, H = 768, 1024  # 4:3 세로, 굿노트 기본 비율


def build_days():
    days = []
    d = dt.date(YEAR, 1, 1)
    while d.year == YEAR:
        hol = HOL.get((d.month, d.day))
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
            if 1 <= cost <= 25:
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
    return f"{d.month}/{d.day}({DOW[d.weekday()]})"


def reason(days, w):
    names = []
    for i in range(w["s"], w["e"] + 1):
        h = days[i]["hol"]
        if h:
            base = h.replace(" 연휴", "").replace(" 대체공휴일", "").replace(" 대체", "")
            if base not in names:
                names.append(base)
    return " · ".join(names) if names else "주말 붙이기"


def register_fonts():
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    pdfmetrics.registerFont(TTFont("Display", os.path.join(here, "bhs.ttf")))
    pdfmetrics.registerFont(TTFont("Body", os.path.join(here, "plex-r.ttf")))
    pdfmetrics.registerFont(TTFont("Bold", os.path.join(here, "plex-b.ttf")))


def page_bg(c):
    c.setFillColor(PAPER)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    c.setFillColor(RED)
    c.rect(0, H - 8, W, 8, stroke=0, fill=1)


def month_grid(c, days, marks, month, x, y, w, h, big, link_prefix=None):
    """(x, y)는 왼쪽 위. big=True면 월간 페이지용 큰 칸."""
    first = next(i for i, d in enumerate(days) if d["date"].month == month)
    start_col = days[first]["date"].weekday()  # 월요일 시작
    count = sum(1 for d in days if d["date"].month == month)
    rows = (start_col + count + 6) // 7
    head = 22 if big else 12
    cw, ch = w / 7, (h - head) / rows
    c.setFont("Bold" if big else "Body", 11 if big else 6.5)
    for k, name in enumerate(DOW):
        c.setFillColor(RED if k == 6 else MUTED)
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
        if d["date"].weekday() == 6 or d["hol"]:
            color = RED
        elif d["date"].weekday() == 5:
            color = MUTED
        if marks["leave"][i]:
            color = HexColor("#ffffff")
        c.setFillColor(color)
        if big:
            c.setFont("Bold", 13)
            c.drawString(cx + 6, cy + ch - 17, str(d["date"].day))
            c.setFont("Body", 8.5)
            label = "연차" if marks["leave"][i] else (d["hol"] or "")
            if label:
                c.drawString(cx + 6, cy + ch - 30, label[:7])
        else:
            c.setFont("Bold" if d["hol"] or marks["leave"][i] else "Body", 7)
            c.drawCentredString(cx + cw / 2, cy + ch / 2 - 2.5, str(d["date"].day))
    if link_prefix:
        c.linkAbsolute("", f"{link_prefix}{month}", (x, y - h, x + w, y + 14))


def make(budget, out):
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
    c.setTitle(f"2027 연차 꿀조합 다이어리 (연차 {budget}개)")

    # 표지
    page_bg(c)
    c.bookmarkPage("cover")
    c.setFillColor(MUTED)
    c.setFont("Bold", 16)
    c.drawString(64, H - 120, "2027 연차 꿀조합 다이어리")
    c.setFillColor(INK)
    c.setFont("Display", 64)
    c.drawString(64, H - 220, f"연차 {budget}개로")
    c.setFillColor(RED)
    c.setFont("Display", 170)
    c.drawString(56, H - 400, f"{total}일")
    c.setFillColor(INK)
    c.setFont("Display", 64)
    c.drawString(64, H - 480, "쉬는 해")
    c.setFillColor(MUTED)
    c.setFont("Body", 15)
    c.drawString(64, H - 525, f"연차 {used}개 사용 · 가장 긴 연휴 {longest}일 · 남는 연차 {budget - used}개")
    y = H - 600
    for w in sorted(picked, key=lambda w: w["s"]):
        c.setFillColor(RED)
        c.setFont("Display", 30)
        c.drawString(64, y, f"{w['len']}일")
        c.setFillColor(INK)
        c.setFont("Bold", 15)
        c.drawString(160, y + 8, f"{fmt(days, w['s'])} ~ {fmt(days, w['e'])}")
        c.setFillColor(MUTED)
        c.setFont("Body", 11)
        c.drawString(160, y - 9, f"{reason(days, w)} · 연차 {w['cost']}개")
        c.linkAbsolute("", f"m{days[w['s']]['date'].month}", (60, y - 14, W - 60, y + 30))
        y -= 52
    c.setFillColor(MUTED)
    c.setFont("Body", 10)
    c.drawString(64, 48, "2026년 10월 기준 관공서 공휴일(노동절·제헌절, 대체공휴일 포함). 임시공휴일은 반영되지 않았어요.")
    c.showPage()

    # 연간 한눈에
    page_bg(c)
    c.bookmarkPage("year")
    c.setFillColor(INK)
    c.setFont("Display", 40)
    c.drawString(48, H - 80, "2027 한눈에")
    c.setFont("Body", 10)
    c.setFillColor(MUTED)
    c.drawString(48, H - 102, "월을 누르면 그 달 페이지로 이동해요.  파랑 = 연차, 노랑 = 쉬는 기간, 빨강 = 공휴일")
    gw, gh = (W - 96 - 40) / 3, 190
    for m in range(1, 13):
        r, col = divmod(m - 1, 3)
        x = 48 + col * (gw + 20)
        top = H - 140 - r * (gh + 30)
        c.setFillColor(INK)
        c.setFont("Bold", 13)
        c.drawString(x, top, f"{m}월")
        month_grid(c, days, marks, m, x, top - 8, gw, gh - 20, big=False, link_prefix="m")
    c.showPage()

    # 월간 페이지
    for m in range(1, 13):
        page_bg(c)
        c.bookmarkPage(f"m{m}")
        c.addOutlineEntry(f"{m}월", f"m{m}", level=0)
        c.setFillColor(RED)
        c.setFont("Display", 72)
        c.drawString(48, H - 110, f"{m}")
        c.setFillColor(INK)
        c.setFont("Display", 28)
        c.drawString(48 + c.stringWidth(f"{m}", "Display", 72) + 10, H - 108, "월")
        c.setFillColor(MUTED)
        c.setFont("Body", 11)
        c.drawRightString(W - 48, H - 100, "← 한눈에 보기")
        c.linkAbsolute("", "year", (W - 160, H - 106, W - 44, H - 88))
        notes = [w for w in picked if days[w["s"]]["date"].month == m or days[w["e"]]["date"].month == m]
        if notes:
            c.setFont("Bold", 11)
            c.setFillColor(LEAVE)
            txt = "   ".join(f"{fmt(days, w['s'])}~{fmt(days, w['e'])} {w['len']}일 연휴 (연차 {w['cost']})" for w in notes)
            c.drawString(48, H - 140, txt[:90])
        month_grid(c, days, marks, m, 48, H - 160, W - 96, 520, big=True)
        # 메모 줄
        c.setFillColor(INK)
        c.setFont("Bold", 12)
        c.drawString(48, H - 712, "메모")
        c.setStrokeColor(LINE)
        c.setLineWidth(0.8)
        yy = H - 740
        while yy > 60:
            c.line(48, yy, W - 48, yy)
            yy -= 30
        c.showPage()
    c.save()
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--leave", type=int, default=15)
    ap.add_argument("--out", default="diary.pdf")
    a = ap.parse_args()
    t = make(a.leave, a.out)
    print(f"{a.out}: 연차 {a.leave}개 → 연휴 합계 {t}일")
