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
HASHTAGS = "\n\n#연차 #연차꿀조합 #2027공휴일 #황금연휴 #직장인 #연휴 #휴가계획"
HERE = os.path.dirname(os.path.abspath(__file__))
POSTS = os.path.join(HERE, "posts.json")
STATE = os.path.join(HERE, "state.json")


def post(url, params):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{url} 실패: {e.read().decode(errors='replace')}") from None


def to_threads(text, token):
    c = post(f"{THREADS_API}/me/threads", {"media_type": "TEXT", "text": text, "access_token": token})
    time.sleep(5)
    return post(f"{THREADS_API}/me/threads_publish", {"creation_id": c["id"], "access_token": token})["id"]


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
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"next": 0}
    i = state["next"]
    if i >= len(posts):
        print("올릴 글이 다 떨어졌어요. posts.json에 새 글을 추가해 주세요.")
        return
    failed = []
    for name, token, fn in (("스레드", th, lambda t: to_threads(posts[i], t)),
                            ("인스타그램", ig, lambda t: to_instagram(posts[i], i + 1, t))):
        if not token:
            continue
        try:
            print(f"{name}: {i + 1}/{len(posts)}번 게시 완료 ({fn(token)})")
        except Exception as e:  # 한쪽이 실패해도 다른 쪽은 올린다
            print(f"{name}: {e}")
            failed.append(name)
    state["next"] = i + 1
    json.dump(state, open(STATE, "w"))
    if failed:
        sys.exit(f"실패: {', '.join(failed)}")


if __name__ == "__main__":
    main()
