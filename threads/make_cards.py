"""posts.json의 글마다 카드 이미지(1080x1350)를 cards/NN.png에, posts_en.json은 cards/en/NN.png에 만든다."""
import json
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "diary", "fonts")
OUT = os.path.join(ROOT, "cards")
W, H = 1080, 1350
PAPER, INK, MUTED, RED, LINE = "#fbfaf7", "#1c2230", "#6b7180", "#d8342c", "#e4e2dc"
URL = "yeoncha-2027.kohs1195123.workers.dev"

LANG = {"ko": dict(font="bhs.ttf", brand="2027 연차 꿀조합", cta="내 연차로 계산해 보기", url=URL),
        "en": dict(font="archivo-black.ttf", brand="2027 PTO HACK", cta="Try your PTO number", url=URL + "/en")}
FONT = "bhs.ttf"
display = lambda s: ImageFont.truetype(os.path.join(FONTS, FONT), s)
body = lambda s: ImageFont.truetype(os.path.join(FONTS, "plex-r.ttf"), s)
bold = lambda s: ImageFont.truetype(os.path.join(FONTS, "plex-b.ttf"), s)


def wrap(draw, text, font, width):
    """띄어쓰기 단위로 줄바꿈하고, 한 단어가 너무 길 때만 글자 단위로 자른다."""
    lines, cur = [], ""
    for word in text.split(" "):
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=font) <= width:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        cur = ""
        for ch in word:
            if draw.textlength(cur + ch, font=font) > width:
                lines.append(cur)
                cur = ch
            else:
                cur += ch
    if cur:
        lines.append(cur)
    return lines


def card(text, lang="ko"):
    global FONT
    L = LANG[lang]
    FONT = L["font"]
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 18], fill=RED)
    d.text((80, 90), L["brand"], font=bold(34), fill=MUTED)
    paras = [p for p in text.split("\n\n") if p.strip()]
    head = paras[0].replace("\n", " ")
    rest = ["\n".join(l for l in p.split("\n") if "workers.dev" not in l and "gumroad" not in l and "http" not in l) for p in paras[1:]]
    rest = [p for p in rest if p.strip()]
    y = 210
    hs = 92 if lang == "ko" else 72
    for line in wrap(d, head, display(hs), W - 160)[:4]:
        d.text((80, y), line, font=display(hs), fill=INK)
        y += hs + 22
    y += 30
    d.line([80, y, W - 80, y], fill=LINE, width=3)
    y += 44
    for p in rest:
        for raw in p.split("\n"):
            is_key = any(k in raw for k in ("→", "일 연휴", "연차", "PTO", "days off"))
            f = bold(48) if is_key else body(46)
            for line in wrap(d, raw, f, W - 160):
                if y > H - 200:
                    break
                d.text((80, y), line, font=f, fill=RED if "→" in raw else INK)
                y += 70
        y += 26
    d.rectangle([0, H - 140, W, H], fill=INK)
    d.text((80, H - 92), L["cta"], font=bold(34), fill=PAPER)
    d.text((W - 80, H - 92), L["url"], font=body(28), fill="#c9ccd3", anchor="ra")
    return img


GOLD, HOLC, WKND = "#ffd23f", "#d8342c", "#f2c9c5"
CAL = {"ko": dict(days="일월화수목금토", pto="연차", hol="공휴일", wk="주말", total="{n}일 연속"),
       "en": dict(days="SMTWTFS", pto="PTO", hol="Holiday", wk="Weekend", total="{n} DAYS IN A ROW")}


def big_line(d, xy, text, size, fill, lang):
    """큰 숫자 문구. 화살표는 디스플레이 폰트에 없을 수 있어 plex-b로 그린다."""
    x, y = xy
    parts = text.split("→")
    for k, part in enumerate(parts):
        part = part.strip()
        if k:
            f = bold(size)
            d.text((x, y - size * 0.08), " → ", font=f, fill=GOLD)
            x += d.textlength(" → ", font=f)
        d.text((x, y), part, font=display(size), fill=fill)
        x += d.textlength(part, font=display(size))


def hook_card(h, lang):
    """조회수용 카드: 빨간 배경에 큰 숫자, 아래에 실제 달력."""
    import datetime as dt
    global FONT
    L, C = LANG[lang], CAL[lang]
    FONT = L["font"]
    img = Image.new("RGB", (W, H), RED)
    d = ImageDraw.Draw(img)
    d.text((80, 80), h["sub"], font=bold(40), fill=GOLD)
    size = 120
    while True:
        t = h["big"].replace("→", " → ")
        if d.textlength(t, font=display(size)) <= W - 160 or size <= 60:
            break
        size -= 6
    big_line(d, (80, 150), h["big"], size, "white", lang)
    head = h["text"].split("\n\n")[0].replace("\n", " ")
    y = 150 + size + 50
    for line in wrap(d, head, bold(44), W - 160)[:2]:
        d.text((80, y), line, font=bold(44), fill="white")
        y += 62
    if "start" in h:
        s, e = dt.date.fromisoformat(h["start"]), dt.date.fromisoformat(h["end"])
        pto, hol = set(h["pto"]), set(h["hol"])
        first = s - dt.timedelta(days=(s.weekday() + 1) % 7)
        last = e + dt.timedelta(days=(5 - e.weekday()) % 7)
        weeks = ((last - first).days + 1) // 7
        top = max(y + 40, 560)
        cw, gap = 124, 10
        ch = min(124, (H - 330 - top - 60) // max(weeks, 1) - gap)
        x0 = (W - (7 * cw + 6 * gap)) // 2
        panel = [x0 - 30, top - 30, W - x0 + 30, top + 60 + weeks * (ch + gap) + 90]
        d.rounded_rectangle(panel, 28, fill=PAPER)
        for c in range(7):
            d.text((x0 + c * (cw + gap) + cw / 2, top), C["days"][c], font=bold(30), fill=RED if c in (0, 6) else MUTED, anchor="ma")
        top += 60
        day = first
        while day <= last:
            i = (day - first).days
            r, c = divmod(i, 7)
            bx, by = x0 + c * (cw + gap), top + r * (ch + gap)
            iso = day.isoformat()
            inside = s <= day <= e
            if not inside:
                fill, fg = "#efede8", "#b9bcc4"
            elif iso in pto:
                fill, fg = GOLD, INK
            elif iso in hol:
                fill, fg = HOLC, "white"
            elif day.weekday() >= 5:
                fill, fg = WKND, INK
            else:
                fill, fg = "#efede8", INK
            d.rounded_rectangle([bx, by, bx + cw, by + ch], 18, fill=fill)
            label = f"{day.month}/{day.day}" if day.day == 1 or day == first else str(day.day)
            d.text((bx + cw / 2, by + ch / 2), label, font=bold(40 if len(label) < 3 else 32), fill=fg, anchor="mm")
            day += dt.timedelta(days=1)
        ly = panel[3] - 64
        x = x0 - 10
        for col, name in ((GOLD, C["pto"]), (HOLC, C["hol"]), (WKND, C["wk"])):
            d.rounded_rectangle([x, ly, x + 34, ly + 34], 8, fill=col)
            d.text((x + 48, ly + 2), name, font=bold(30), fill=INK)
            x += 70 + d.textlength(name, font=bold(30)) + 30
        n = (e - s).days + 1
        d.text((W - x0 + 10, ly + 2), C["total"].format(n=n), font=bold(30), fill=RED, anchor="ra")
    else:
        y += 40
        for p in h["text"].split("\n\n")[1:]:
            for raw in p.split("\n"):
                for line in wrap(d, raw, bold(46), W - 160):
                    if y > H - 220:
                        break
                    d.text((80, y), line, font=bold(46), fill="white")
                    y += 70
            y += 30
    d.rectangle([0, H - 140, W, H], fill=INK)
    d.text((80, H - 92), L["cta"], font=bold(34), fill=PAPER)
    d.text((W - 80, H - 92), L["url"], font=body(28), fill="#c9ccd3", anchor="ra")
    return img


def main():
    hooks = json.load(open(os.path.join(ROOT, "threads", "hooks.json"), encoding="utf-8"))
    for lang, name, out in (("ko", "posts.json", OUT), ("en", "posts_en.json", os.path.join(OUT, "en"))):
        posts = json.load(open(os.path.join(ROOT, "threads", name), encoding="utf-8"))
        by_text = {h["text"]: h for h in hooks[lang]}
        os.makedirs(out, exist_ok=True)
        for i, t in enumerate(posts, 1):
            img = hook_card(by_text[t], lang) if t in by_text else card(t, lang)
            img.save(os.path.join(out, f"{i:02d}.png"), optimize=True)
        print(f"{lang}: {len(posts)}장 생성")


if __name__ == "__main__":
    main()
