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

    # 이미지 URL 서치 + 검증
    img_resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=(
            f"다음 구매대행 상품의 실제 접근 가능한 이미지 URL 3개를 찾아줘: {topic['search']}\n\n"
            f"조건:\n"
            f"1. 반드시 .jpg .png .webp 확장자로 끝나는 직접 이미지 URL만\n"
            f"2. 아마존 상품 이미지(images-amazon.com), 구글 이미지, 쇼핑몰 CDN URL 우선\n"
            f"3. 각 URL을 직접 접속해서 실제 이미지가 로드되는지 확인 후 제공\n"
            f"4. 접속 불가한 URL은 제외하고 검증된 것만 제공\n"
            f"5. URL이 너무 길면 원본 그대로 제공 (단축 금지)\n\n"
            f"형식:\n"
            f"URL1: https://... (검증완료)\n"
            f"URL2: https://... (검증완료)\n"
            f"URL3: https://... (검증완료)\n"
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

### 🎬 클링 3.0 프롬프트 (15초 단일 클립)

**[프롬프트 - 영어]**

[0-5s] (훅 장면: 강렬하고 시선을 잡는 상품 클로즈업. 카메라 무브·조명·분위기 구체적으로 작성)
[5-10s] (정보 장면: 상품 특징·마진율 텍스트 오버레이. 역동적 전환. 구체적으로 작성)
[10-15s] (CTA 장면: 라이프스타일 배치샷. 화면에 "쿠대 카페에서 더 알아보기" 텍스트 포함)
Consistent color grading throughout, smooth transitions, vertical 9:16 format for YouTube Shorts.

---

### 🖼️ 클링 레퍼런스 이미지
(Image-to-Video용 - 검증된 실제 URL만 사용)
- 메인 이미지: [이미지 URL 목록에서 검증된 URL 1순위]
- 대체 이미지: [검증된 URL 2순위]

---

### 🎙️ 나레이션 스크립트 (15초)

**나레이션 텍스트:**
[0-5s]: (훅 - 1~2문장. 강렬한 훅)
[5-10s]: (정보 - 2~3문장. 구체적 마진율·소싱처)
[10-15s]: (CTA - 1문장. 카페 방문·구독 유도)

**오디오 분위기:**
[전체 BGM 지시 - 에너지 넘치는 비트 or 트렌디한 팝 등]

---

### 📱 유튜브 메타데이터

**제목 A** (감정 자극. 40자 이내):
**제목 B** (정보성. 숫자 포함. 40자 이내):

**설명**:
(3~5줄. SEO 키워드 + 카페링크 cafe.naver.com/coudae 포함)

**해시태그**:
#구매대행 #해외직구 #소싱 #[주제관련태그] #쿠대 #유튜브쇼츠

---

### 💡 제작 팁
[이 영상 제작 시 주의사항 2가지]
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
