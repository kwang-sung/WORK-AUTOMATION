#!/usr/bin/env python3
"""
골든서퍼 인사이트 - 구매대행 뉴스레터
매주 월요일·목요일 09:00 자동 발송
Gemini API로 서치 → Claude API로 글쓰기
"""

import os
import smtplib
import anthropic
import google.generativeai as genai
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

# ─── 서치 쿼리 ────────────────────────────────────────────
SEARCH_QUERIES = [
    "구매대행 최신 트렌드 아이템 2026 국내",
    "해외직구 인기상품 트렌드 2026 이번주",
    "일본 인기 상품 트렌드 2026 소싱 한국",
    "Japan trending products ecommerce 2026",
    "쿠팡 네이버 스마트스토어 구매대행 정책 2026",
    "해외 이커머스 배송 관세 정책 변경 2026",
    "국내 미출시 해외 인기 상품 아이템 2026",
    "Super Delivery Yodobashi trending items Korea 2026",
]


# ─── 1. Gemini로 뉴스 서치 ────────────────────────────────
def collect_news_with_gemini() -> str:
    """Gemini API + Google Search 그라운딩으로 구매대행 뉴스 수집"""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    collected = []
    for query in SEARCH_QUERIES:
        try:
            resp = model.generate_content(
                f"다음 주제로 이번 주 최신 정보 4~5개를 찾아서 "
                f"'제목 | 핵심내용 2문장 | URL' 형식으로 한국어로 답변해줘: {query}",
                tools="google_search_retrieval",
            )
            collected.append(f"[{query}]\n{resp.text}")
            print(f"    ✅ {query[:45]}...")
        except Exception as e:
            print(f"    ⚠️  실패: {e}")

    return "\n\n---\n\n".join(collected)


# ─── 2. Claude로 뉴스레터 HTML 생성 ──────────────────────
def build_newsletter_html(news_text: str) -> str:
    """Gemini가 수집한 자료를 Claude가 받아서 뉴스레터 HTML 작성"""
    client    = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today     = datetime.now().strftime("%Y년 %m월 %d일")
    weekday   = ["월", "화", "수", "목", "금", "토", "일"][datetime.now().weekday()]
    issue_num = datetime.now().strftime("%Y%m%d")

    prompt = f"""
당신은 구매대행 전문 뉴스레터 에디터 '골든서퍼'입니다.
오늘은 {today}({weekday}요일)입니다.

아래 Gemini가 수집한 구매대행·이커머스 정보를 바탕으로
네이버 카페 '골든서퍼 인사이트' 코너에 바로 복붙 가능한
HTML 뉴스레터를 작성해주세요.

===== Gemini 수집 정보 =====
{news_text}
============================

## 뉴스레터 구성 (필수)

### [SECTION 1] 헤더 배너
- 브랜드명: 골든서퍼 인사이트
- 부제: 구매대행 실전 트렌드 리포트
- 날짜 + 호수(#{issue_num})
- 한 줄 이번 호 핵심 메시지

### [SECTION 2] 이번 호 핵심 3줄 요약 박스

### [SECTION 3] 국내 구매대행 트렌드 (2~3개)
- 각 항목: 이모지+제목 / 내용 3~4문장 / 실전 적용 팁 / 출처링크

### [SECTION 4] 해외 소싱 트렌드 & 추천 아이템 (2~3개)
- 일본·해외 인기 상품, 틈새 아이템 위주
- 각 항목: 이모지+제목 / 상품 설명 / 소싱 포인트 / 예상 마진 힌트 / 출처링크

### [SECTION 5] 플랫폼·정책 업데이트
- 쿠팡·네이버·11번가 정책, 관세·배송 변경사항

### [SECTION 6] 골든서퍼 한마디
- 핵심 인사이트를 골든서퍼 관점으로 2~3문장 (🏄 이모지로 시작)

### [SECTION 7] 푸터
- "골든서퍼 인사이트 | {today} | Powered by Gemini + Claude"

## 디자인 스펙 (카페 복붙 최적화 인라인 CSS)
- 전체 max-width: 720px, margin: 0 auto, font-family: 'Noto Sans KR', Arial, sans-serif
- 헤더: background linear-gradient(135deg, #1a1a2e, #16213e, #0f3460), border-radius 16px, padding 36px, text-align center
- 제목: font-size 28px, font-weight 900, color #ffffff
- 날짜 뱃지: background #e2b04a, color #1a1a2e, border-radius 20px, padding 4px 16px
- 핵심요약 박스: background #fef9ec, border-left 5px solid #e2b04a, border-radius 8px, padding 20px
- 섹션 제목: font-size 18px, font-weight 800, border-bottom 3px solid #e2b04a
- 뉴스 카드: background #ffffff, border-radius 12px, padding 20px, box-shadow 0 2px 8px rgba(0,0,0,0.08)
  border-top 4px solid (국내:#3b82f6 / 해외:#10b981 / 플랫폼:#f59e0b)
- 실전팁 박스: background #f0fdf4, border-radius 8px, padding 12px, color #166534
- 골든서퍼 한마디: background linear-gradient(135deg, #1a1a2e, #0f3460), color #ffffff, border-radius 12px, padding 24px
- 링크: color #3b82f6, font-weight 600
- 이모지 풍부하게 사용

순수 HTML만 반환. 코드블록·마크다운 없이.
"""

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=5000,
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.content[0].text


# ─── 3. Gmail 발송 ────────────────────────────────────────
def send_email(html: str, subject: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText("골든서퍼 인사이트 - HTML 뷰어에서 확인하세요.", "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PW)
            server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())
        print(f"  ✅ 발송 완료 → {RECIPIENT_EMAIL}")
        return True
    except Exception as e:
        print(f"  ❌ 발송 실패: {e}")
        return False


# ─── 4. HTML 저장 ─────────────────────────────────────────
def save_preview(html: str) -> str:
    fname = f"insight_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  📄 저장: {fname}")
    return fname


# ─── 메인 ─────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("🏄 골든서퍼 인사이트 뉴스레터 시작")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # 1. Gemini로 서치
    print("\n📡 Gemini로 구매대행 뉴스 수집 중... (8개 쿼리)")
    news_text = collect_news_with_gemini()
    print("   수집 완료\n")

    # 2. Claude로 HTML 생성
    print("✍️  Claude가 뉴스레터 작성 중...")
    html = build_newsletter_html(news_text)
    print("   작성 완료\n")

    save_preview(html)

    # 3. 발송
    today   = datetime.now().strftime("%Y년 %m월 %d일")
    weekday = ["월", "화", "수", "목", "금", "토", "일"][datetime.now().weekday()]
    subject = f"🏄 골든서퍼 인사이트 | {today}({weekday}) 구매대행 트렌드 리포트"

    if GMAIL_USER and GMAIL_APP_PW and RECIPIENT_EMAIL:
        print("📧 이메일 발송 중...")
        send_email(html, subject)
    else:
        print("⚠️  .env 파일 이메일 설정 필요")

    print("\n✅ 완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
