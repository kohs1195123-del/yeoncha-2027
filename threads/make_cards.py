"""posts.json의 글마다 인스타용 카드 이미지(1080x1350)를 cards/에 만든다."""
import json
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "diary", "fonts")
OUT = os.path.join(ROOT, "cards")
W, H = 1080, 1350
PAPER, INK, MUTED, RED, LINE = "#fbfaf7", "#1c2230", "#6b7180", "#d8342c", "#e4e2dc"
URL = "yeoncha-2027.kohs1195123.workers.dev"

display = lambda s: ImageFont.truetype(os.path.join(FONTS, "bhs.ttf"), s)
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


def card(text, n, total):
    img = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 18], fill=RED)
    d.text((80, 90), "2027 연차 꿀조합", font=bold(34), fill=MUTED)
    paras = [p for p in text.split("\n\n") if p.strip()]
    head = paras[0].replace("\n", " ")
    rest = [p for p in paras[1:] if "workers.dev" not in p and "http" not in p]
    y = 210
    for line in wrap(d, head, display(92), W - 160)[:4]:
        d.text((80, y), line, font=display(92), fill=INK)
        y += 114
    y += 30
    d.line([80, y, W - 80, y], fill=LINE, width=3)
    y += 44
    for p in rest:
        for raw in p.split("\n"):
            is_key = any(k in raw for k in ("→", "일 연휴", "연차"))
            f = bold(48) if is_key else body(46)
            for line in wrap(d, raw, f, W - 160):
                if y > H - 200:
                    break
                d.text((80, y), line, font=f, fill=RED if "→" in raw else INK)
                y += 70
        y += 26
    d.rectangle([0, H - 140, W, H], fill=INK)
    d.text((80, H - 92), "내 연차로 계산해 보기", font=bold(34), fill=PAPER)
    d.text((W - 80, H - 92), URL, font=body(28), fill="#c9ccd3", anchor="ra")
    return img


def main():
    posts = json.load(open(os.path.join(ROOT, "threads", "posts.json"), encoding="utf-8"))
    os.makedirs(OUT, exist_ok=True)
    for i, t in enumerate(posts, 1):
        card(t, i, len(posts)).save(os.path.join(OUT, f"{i:02d}.png"), optimize=True)
    print(f"{len(posts)}장 생성")


if __name__ == "__main__":
    main()
