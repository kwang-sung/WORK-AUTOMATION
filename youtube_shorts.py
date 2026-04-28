#!/usr/bin/env python3
"""
쿠대 유튜브 쇼츠 자동화
격일 실행 (매월 1,3,5,7,9,11,13,15,17,19,21,23,25,27,29일)

파이프라인:
1. Gemini → 아이템 서치 + 이미지 URL 수집
2. Claude → 클링 프롬프트 + 나레이션 + 유튜브 메타데이터 생성
3. Gmail → 완성된 패키지 메일 발송
"""

import os
import smtplib
import anthropic
from google import genai
from google.genai import types
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─── 설정 ─────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")
GMAIL_USER        = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PW      = os.environ.get("GMAIL_APP_PW", "")
RECIPIENT_EMAIL   = os.environ.get("RECIPIENT_EMAIL", "")

# ─── 7가지 주제 순환 ──────────────────────────────────────
TOPICS = [
    {
        "title": "마진 40% 이상 아이템",
        "search": "구매대행 마진 40% 이상 아이템 2026 최신 해외 소싱",
        "angle": "마진이 높은 이유와 소싱 방법 강조"
    },
    {
        "title": "일본 소싱 추천",
        "search": "일본 라쿠텐 야후재팬 슈퍼딜리버리 인기 구매대행 아이템 2026",
        "angle": "일본에서만 살 수 있는 희소성 강조"
    },
    {
        "title": "국내 미출시 희소 아이템",
        "search": "해외 인기 국내 미출시 구매대행 희소 아이템 2026",
        "angle": "국내에 없는 희소성과 선점 기회 강조"
    },
    {
        "title": "미국·유럽 소싱 추천",
        "search": "미국 유럽 아마존 이베이 구매대행 인기 아이템 2026",
        "angle": "고마진 프리미엄 상품 강조"
    },
    {
        "title": "지금 당장 팔 수 있는 아이템",
        "search": "구매대행 즉시 판매 가능 수요 높은 아이템 2026 쿠팡 네이버",
        "angle": "즉시 수익 가능한 실전성 강조"
    },
    {
        "title": "중국·알리 소싱 추천",
        "search": "알리익스프레스 타오바오 구매대행 마진 좋은 아이템 2026",
        "angle": "저렴한 소싱가 대비 높은 마진 강조"
    },
    {
        "title": "지금 시즌 타이밍 아이템",
        "search": f"2026년 {datetime.now().month}월 계절 트렌드 구매대행 타이밍 아이템",
        "angle": "지금 이 시즌에만 통하는 타이밍 강조"
    },
]


# ─── 1. Gemini 아이템 서치 + 이미지 URL ──────────────────
def search_with_gemini(topic: dict) -> dict:
    client = genai.Client(api_key=GEMINI_API_KEY)

    # 아이템 서치
    item_resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=(
            f"구매대행 전문가 입장에서 다음 주제로 지금 당장 팔 수 있는 아이템 3개를 찾아줘: {topic['search']}\n"
            f"각 아이템:\n"
            f"1. 상품명 (구체적으로)\n"
            f"2. 소싱 국가/플랫폼\n"
            f"3. 예상 마진율\n"
            f"4. 추천 이유 2문장\n"
            f"5. 상품 이미지 검색 키워드 (영어)\n"
            f"오늘 날짜 기준 최신 트렌드 반영"
        ),
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )

    # 이미지 URL 서치
    img_resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=(
            f"다음 주제의 구매대행 상품 이미지를 찾아서 실제 접근 가능한 이미지 URL 3개를 알려줘: {topic['search']}\n"
            f"반드시 직접 접근 가능한 .jpg .png .webp URL만 제공\n"
            f"형식: URL1: https://... URL2: https://... URL3: https://..."
        ),
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )

    return {
        "items": item_resp.text,
        "images": img_resp.text
    }


# ─── 2. Claude 콘텐츠 생성 ────────────────────────────────
def generate_content(topic: dict, search_data: dict) -> dict:
    client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today   = datetime.now().strftime("%Y년 %m월 %d일")
    month   = datetime.now().month

    prompt = f"""
당신은 구매대행 전문 유튜브 쇼츠 제작자입니다.
오늘은 {today}입니다.

아래 서치 정보를 바탕으로 유튜브 쇼츠 제작 패키지를 만들어주세요.

===== 서치 정보 =====
[아이템 정보]
{search_data['items']}

[이미지 URL]
{search_data['images']}
=====================

오늘 주제: {topic['title']}
강조 포인트: {topic['angle']}

## 출력 형식 (정확히 이 형식으로)

### 📋 오늘의 주제
{topic['title']}

---

### 🎬 클링 3.0 프롬프트 (15초)

**[Shot 1 - 0~5초] 훅**
(강렬한 첫 장면 - 시청자가 멈추게 만드는 장면)
프롬프트: [영어로 작성. 구체적인 카메라 무브·조명·분위기 포함. 상품이 주인공]
나레이션: [한국어 1~2문장. "이 아이템 모르면 손해입니다" 같은 강렬한 훅]
오디오 지시: [배경음악 분위기 + 나레이션 톤]

**[Shot 2 - 5~10초] 핵심 정보**
(소싱 정보·마진·특징 전달)
프롬프트: [영어로 작성. 상품 클로즈업·텍스트 오버레이 포함]
나레이션: [한국어 2~3문장. 구체적 마진율·소싱처 포함]
오디오 지시: [정보 전달용 깔끔한 톤]

**[Shot 3 - 10~15초] CTA**
(행동 유도)
프롬프트: [영어로 작성. 화면에 텍스트 "쿠대 카페에서 더 알아보기" 포함]
나레이션: [한국어 1~2문장. 카페 방문·구독 유도]
오디오 지시: [마무리 음악 + 밝은 톤]

---

### 🖼️ 추천 이미지 URL
(클링 Image-to-Video에 사용할 이미지)
- Shot 1용: [URL 또는 검색 키워드]
- Shot 2용: [URL 또는 검색 키워드]
- Shot 3용: [URL 또는 검색 키워드]

---

### 🎙️ 전체 나레이션 스크립트
(GPT TTS 또는 클링 오디오용 - 15초 분량)
[전체 나레이션을 하나로 연결해서 작성]

---

### 📱 유튜브 쇼츠 메타데이터

**제목**: [클릭하고 싶은 제목. 숫자·이모지 포함. 50자 이내]

**설명**:
[3~5줄. SEO 키워드 포함. 카페 링크: cafe.naver.com/coudae]

**해시태그**:
#구매대행 #해외직구 #소싱 #[주제관련태그] #쿠대 #유튜브쇼츠

---

### 💡 제작 팁
[이 영상 제작 시 주의사항 2~3가지]
"""

    resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )

    return resp.content[0].text


# ─── 3. 메일 발송 ─────────────────────────────────────────
def send_email(content: str, topic_title: str, today: str) -> bool:
    html = f"""
<div style="max-width:700px;margin:0 auto;font-family:'Apple SD Gothic Neo','Malgun Gothic',Arial,sans-serif;">

  <!-- 헤더 -->
  <div style="background-color:#0f172a;border-radius:14px;padding:32px;text-align:center;margin-bottom:20px;">
    <div style="font-size:28px;font-weight:900;color:#ffffff;">🎬 쿠대 쇼츠 제작 패키지</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:8px;">{today}</div>
    <div style="display:inline-block;background-color:#6366f1;color:#ffffff;border-radius:20px;padding:6px 20px;font-size:13px;font-weight:700;margin-top:12px;">{topic_title}</div>
  </div>

  <!-- 안내 -->
  <div style="background-color:#fffbeb;border-left:4px solid #e2b04a;border-radius:0 8px 8px 0;padding:16px 20px;margin-bottom:20px;">
    <div style="font-size:13px;font-weight:800;color:#92400e;margin-bottom:8px;">📌 오늘 할 일 (10분)</div>
    <div style="font-size:13px;color:#1e293b;line-height:1.8;">
      1️⃣ 클링 프롬프트 복붙 → 영상 3개 생성 (각 5초)<br>
      2️⃣ 나레이션 스크립트 → 클링 오디오 또는 GPT TTS<br>
      3️⃣ 영상 합치기 → 15초 완성<br>
      4️⃣ 유튜브 쇼츠 업로드
    </div>
  </div>

  <!-- 본문 -->
  <div style="background-color:#f8fafc;border-radius:12px;padding:24px;white-space:pre-wrap;font-size:14px;color:#1e293b;line-height:1.9;">
{content}
  </div>

  <!-- 푸터 -->
  <div style="text-align:center;padding:20px;font-size:12px;color:#94a3b8;margin-top:16px;">
    🎬 쿠대 쇼츠 자동화 | Powered by Gemini + Claude | {today}
  </div>

</div>
"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🎬 [{topic_title}] 쿠대 쇼츠 제작 패키지 | {today}"
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText("쿠대 쇼츠 제작 패키지", "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PW)
            server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())
        print(f"  ✅ 메일 발송 완료 → {RECIPIENT_EMAIL}")
        return True
    except Exception as e:
        print(f"  ❌ 메일 발송 실패: {e}")
        return False


# ─── 메인 ─────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("🎬 쿠대 유튜브 쇼츠 패키지 생성 시작")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # 오늘 날짜 기준 주제 선택 (7개 순환)
    day_of_year = datetime.now().timetuple().tm_yday
    topic_index = (day_of_year // 2) % 7
    topic = TOPICS[topic_index]
    today = datetime.now().strftime("%Y년 %m월 %d일")

    print(f"\n📅 오늘 주제: {topic['title']} (인덱스: {topic_index})\n")

    # 1. Gemini 서치
    print("🔍 Gemini 아이템 서치 중...")
    search_data = search_with_gemini(topic)
    print("   서치 완료\n")

    # 2. Claude 콘텐츠 생성
    print("✍️  Claude 쇼츠 패키지 생성 중...")
    content = generate_content(topic, search_data)
    print("   생성 완료\n")

    # 3. 저장
    fname = f"shorts_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  📄 저장: {fname}\n")

    # 4. 메일 발송
    print("📧 메일 발송 중...")
    send_email(content, topic['title'], today)

    print("\n✅ 완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
