"""SNS 자동 게시: posts.json에서 다음 글을 골라 공식 API로 스레드와 인스타그램에 올린다.

THREADS_TOKEN이 있으면 스레드에 글로, IG_TOKEN이 있으면 인스타그램에 카드 이미지(cards/NN.png)로 올린다.
게시한 위치는 state.json에 기록한다.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

THREADS_API = "https://graph.threads.net/v1.0"
IG_API = "https://graph.instagram.com/v23.0"
SITE = "https://yeoncha-2027.kohs1195123.workers.dev"
RAW = "https://raw.githubusercontent.com/kohs1195123-del/yeoncha-2027/main"
HASHTAGS = "\n\n#연차 #연차꿀조합 #2027공휴일 #황금연휴 #직장인 #연휴 #휴가계획"
HERE = os.path.dirname(os.path.abspath(__file__))
QUEUE = os.environ.get("QUEUE", "ko")  # "en"이면 영어 글 큐(posts_en.json)를 스레드에만 올린다
POSTS = os.path.join(HERE, "posts_en.json" if QUEUE == "en" else "posts.json")
STATE = os.path.join(HERE, "state.json")


def post(url, params):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{url} 실패: {e.read().decode(errors='replace')}") from None


LINKS = {
    "ko": "내 연차로 계산해 보기 👉 " + SITE + "\n2027 연차 다이어리 👉 https://kohs1195.gumroad.com/l/yeoncha2027",
    "en": "Try your PTO number 👉 " + SITE + "/en/\n2027 PTO planner 👉 https://kohs1195.gumroad.com/l/pto-2027",
}


def get(url):
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.load(r)


def publish(params, token):
    c = post(f"{THREADS_API}/me/threads", {**params, "access_token": token})
    for _ in range(12):  # 이미지는 처리될 때까지 기다린다
        time.sleep(5)
        st = get(f"{THREADS_API}/{c['id']}?fields=status&access_token={token}").get("status")
        if st == "FINISHED":
            break
        if st == "ERROR":
            raise RuntimeError("Threads 컨테이너 처리 실패")
    return post(f"{THREADS_API}/me/threads_publish", {"creation_id": c["id"], "access_token": token})["id"]


def to_threads(text, token, n=None):
    """본문은 카드 이미지와 함께 링크 없이 올리고, 링크는 첫 답글로 단다 (링크 글은 노출이 줄어서)."""
    lang = "en" if QUEUE == "en" else "ko"
    body = "\n".join(l for l in text.split("\n") if "workers.dev" not in l and "gumroad.com" not in l).strip()
    # 카드는 GitHub에서 바로 가져간다 (사이트 배포를 기다리지 않아도 됨)
    img = f"{RAW}/cards/{'en/' if lang == 'en' else ''}{n:02d}.png" if n else None
    try:
        pid = publish({"media_type": "IMAGE", "image_url": img, "text": body} if img else {"media_type": "TEXT", "text": body}, token)
    except Exception as e:
        print(f"이미지 게시 실패, 글만 올려요: {e}")
        pid = publish({"media_type": "TEXT", "text": body}, token)
    try:
        publish({"media_type": "TEXT", "text": LINKS[lang], "reply_to_id": pid}, token)
    except Exception as e:
        print(f"링크 답글 실패: {e}")
    return pid


def to_instagram(text, n, token):
    caption = text.replace(SITE, "프로필 링크") + HASHTAGS
    c = post(f"{IG_API}/me/media", {"image_url": f"{SITE}/cards/{n:02d}.png", "caption": caption, "access_token": token})
    time.sleep(10)
    return post(f"{IG_API}/me/media_publish", {"creation_id": c["id"], "access_token": token})["id"]


def main():
    th, ig = os.environ.get("THREADS_TOKEN"), os.environ.get("IG_TOKEN")
    if not th and not ig:
        sys.exit("THREADS_TOKEN이나 IG_TOKEN 시크릿이 없어요.")
    posts = json.load(open(POSTS, encoding="utf-8"))
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    failed = []
    targets = (("threads_en", "스레드(영어)", th),) if QUEUE == "en" else (("threads", "스레드", th), ("instagram", "인스타그램", ig))
    for key, name, token in targets:
        if not token:
            continue
        i = state.get(key, 0)  # 플랫폼마다 따로 기록해서, 나중에 연결한 쪽도 1번 글부터 올린다
        if i >= len(posts):
            print(f"{name}: 올릴 글이 다 떨어졌어요. posts.json에 새 글을 추가해 주세요.")
            continue
        try:
            pid = to_threads(posts[i], token, i + 1) if key.startswith("threads") else to_instagram(posts[i], i + 1, token)
            print(f"{name}: {i + 1}/{len(posts)}번 게시 완료 ({pid})")
            state[key] = i + 1
        except Exception as e:  # 한쪽이 실패해도 다른 쪽은 올린다
            print(f"{name}: {e}")
            failed.append(name)
    json.dump(state, open(STATE, "w"))
    if failed:
        sys.exit(f"실패: {', '.join(failed)}")

if __name__ == "__main__":
    main()
