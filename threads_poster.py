#!/usr/bin/env python3
"""
쿠대 스레드 자동 포스팅
매일 오전 9시 실행
Gemini로 아이템 서치 → Claude가 스레드용 글 작성 → Threads API 포스팅
"""

import os
import json
import requests
import anthropic
from google import genai
from google.genai import types
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── 설정 ─────────────────────────────────────────────────
ANTHROPIC_API_KEY    = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY       = os.environ.get("GEMINI_API_KEY", "")
THREADS_ACCESS_TOKEN = os.environ.get("THREADS_ACCESS_TOKEN", "")
THREADS_USER_ID      = os.environ.get("THREADS_USER_ID", "")

# ─── 요일별 포스팅 주제 ───────────────────────────────────
DAILY_TOPICS = {
    0: ("마진 좋은 아이템 TOP 3", "이번 주 마진 40% 이상 기대되는 구매대행 추천 아이템 3개. 국가 무관, 실제 판매 가능한 것만. 각 아이템 예상마진율 포함"),
    1: ("일본 소싱 추천 아이템", "일본 라쿠텐·야후재팬·슈퍼딜리버리에서 지금 인기 있는 구매대행 추천 아이템. 국내 미출시 위주"),
    2: ("미국·유럽 소싱 추천", "아마존US·이베이에서 지금 트렌딩 중인 구매대행 추천 아이템. 국내에 없거나 가격 차이 큰 것"),
    3: ("중국·알리 소싱 추천", "알리익스프레스·타오바오에서 급상승 중인 구매대행 추천 아이템. 품질 좋고 마진 남는 것"),
    4: ("지금 당장 팔 수 있는 아이템", "계절·트렌드 고려한 즉시 판매 가능한 구매대행 아이템. 수요 검증된 것만"),
    5: ("국내 미출시 희소 아이템", "해외에서 인기지만 국내 정식 출시 안 된 희소 아이템. 선점 기회 있는 것"),
    6: ("이번 주 구매대행 총정리", "이번 주 가장 주목받은 구매대행 트렌드와 핵심 아이템 총정리"),
}


# ─── 1. Gemini로 아이템 서치 ──────────────────────────────
def search_items_with_gemini(topic: str, query: str) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                f"구매대행 소싱 전문가 입장에서 다음을 조사해줘: {query}\n"
                f"각 아이템마다: 상품명, 소싱 국가/플랫폼, 예상 마진율, "
                f"국내 판매 가능 여부, 한줄 추천 이유를 포함해줘. "
                f"오늘 날짜 기준 최신 트렌드 반영해줘."
            ),
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        return resp.text
    except Exception as e:
        print(f"  ⚠️  Gemini 서치 실패: {e}")
        return ""


# ─── 2. Claude로 스레드 글 작성 ──────────────────────────
def generate_threads_post(topic: str, search_result: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today  = datetime.now().strftime("%Y년 %m월 %d일")
    weekday = ["월", "화", "수", "목", "금", "토", "일"][datetime.now().weekday()]

    prompt = f"""
당신은 구매대행 전문가 '쿠대' 스레드 계정 운영자입니다.
오늘은 {today}({weekday}요일)입니다.

아래 조사된 정보를 바탕으로 스레드 포스팅 글을 작성하세요.

===== 조사 결과 =====
{search_result}
=====================

## 작성 규칙
- **200~300자 이내** (스레드 최적 길이)
- 첫 줄은 강렬한 훅으로 시작 (이모지 포함)
- 핵심 아이템 2~3개만 간결하게
- 예상 마진율 반드시 포함
- 마지막 줄: "자세한 내용은 쿠대 카페에서 👉 cafe.naver.com/coudae"
- 해시태그 3~5개 (#구매대행 #해외직구 #소싱 등)
- 광고처럼 느껴지지 않게 자연스럽게
- 사람이 직접 쓴 것처럼 친근한 말투

## 오늘 주제
{topic}

글만 작성하세요. 설명 없이.
"""

    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.content[0].text.strip()


# ─── 3. Threads API 포스팅 ────────────────────────────────
def post_to_threads(text: str) -> bool:
    """Threads API로 포스팅"""

    # Step 1: 컨테이너 생성
    container_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads"
    container_resp = requests.post(container_url, data={
        "media_type": "TEXT",
        "text": text,
        "access_token": THREADS_ACCESS_TOKEN
    })

    if container_resp.status_code != 200:
        print(f"  ❌ 컨테이너 생성 실패: {container_resp.text}")
        return False

    container_id = container_resp.json().get("id")
    print(f"  ✅ 컨테이너 생성: {container_id}")

    # 컨테이너 준비 대기
    import time
    print("  ⏳ 컨테이너 준비 중... (30초 대기)")
    time.sleep(30)

    # Step 2: 발행
    publish_url = f"https://graph.threads.net/v1.0/{THREADS_USER_ID}/threads_publish"
    publish_resp = requests.post(publish_url, data={
        "creation_id": container_id,
        "access_token": THREADS_ACCESS_TOKEN
    })

    if publish_resp.status_code == 200:
        post_id = publish_resp.json().get("id")
        print(f"  ✅ 스레드 포스팅 완료! ID: {post_id}")
        return True
    else:
        print(f"  ❌ 발행 실패: {publish_resp.text}")
        return False


# ─── 4. 결과 저장 ─────────────────────────────────────────
def save_post(text: str):
    fname = f"thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  📄 저장: {fname}")


# ─── 메인 ─────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("🧵 쿠대 스레드 자동 포스팅 시작")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # 오늘 요일 주제
    weekday_num = datetime.now().weekday()
    topic, query = DAILY_TOPICS[weekday_num]
    weekday_str = ["월", "화", "수", "목", "금", "토", "일"][weekday_num]
    print(f"\n📅 오늘({weekday_str}요일) 주제: {topic}\n")

    # 1. Gemini 서치
    print("🔍 Gemini 아이템 서치 중...")
    search_result = search_items_with_gemini(topic, query)
    print("   서치 완료\n")

    # 2. Claude 글 작성
    print("✍️  Claude 스레드 글 작성 중...")
    post_text = generate_threads_post(topic, search_result)
    print(f"\n📝 작성된 글:\n{'-'*40}\n{post_text}\n{'-'*40}\n")

    # 3. 저장
    save_post(post_text)

    # 4. Threads 포스팅
    if THREADS_ACCESS_TOKEN and THREADS_USER_ID:
        print("🧵 Threads 포스팅 중...")
        post_to_threads(post_text)
    else:
        print("⚠️  THREADS_ACCESS_TOKEN 또는 THREADS_USER_ID 미설정")

    print("\n✅ 완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
