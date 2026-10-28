"""스레드 자동 게시: posts.json에서 다음 글을 골라 공식 Threads API로 올린다.

환경변수 THREADS_TOKEN(장기 접근 토큰)이 필요하다. 게시한 위치는 state.json에 기록한다.
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

API = "https://graph.threads.net/v1.0"
HERE = os.path.dirname(os.path.abspath(__file__))
POSTS = os.path.join(HERE, "posts.json")
STATE = os.path.join(HERE, "state.json")


def call(method, url, params):
    data = urllib.parse.urlencode(params).encode()
    if method == "GET":
        req = urllib.request.Request(url + "?" + data.decode())
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def main():
    token = os.environ.get("THREADS_TOKEN")
    if not token:
        sys.exit("THREADS_TOKEN 시크릿이 없어요.")
    posts = json.load(open(POSTS, encoding="utf-8"))
    state = json.load(open(STATE)) if os.path.exists(STATE) else {"next": 0}
    i = state["next"]
    if i >= len(posts):
        print("올릴 글이 다 떨어졌어요. posts.json에 새 글을 추가해 주세요.")
        return
    created = call("POST", f"{API}/me/threads", {"media_type": "TEXT", "text": posts[i], "access_token": token})
    time.sleep(5)  # 메타 권장: 컨테이너 생성 후 잠시 대기
    published = call("POST", f"{API}/me/threads_publish", {"creation_id": created["id"], "access_token": token})
    print(f"{i + 1}/{len(posts)}번 글 게시 완료: {published.get('id')}")
    state["next"] = i + 1
    json.dump(state, open(STATE, "w"))


if __name__ == "__main__":
    main()
