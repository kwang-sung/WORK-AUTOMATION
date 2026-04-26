#!/usr/bin/env python3
"""
AI 위클리 뉴스레터 - 매주 월요일 09:00 자동 발송
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
    "latest AI news this week OpenAI Anthropic Google 2026",
    "new AI model release this week 2026",
    "AI ecommerce automation tools 2026",
    "AI 이번주 최신 뉴스 모델 출시 2026",
    "AI agent productivity business tools this week",
    "AI 구매대행 자동화 이커머스 2026",
]


# ─── 1. Gemini로 뉴스 서치 ────────────────────────────────
def collect_news_with_gemini() -> str:
    """Gemini API + Google Search 그라운딩으로 최신 뉴스 수집"""
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.0-flash")

    collected = []
    for query in SEARCH_QUERIES:
        try:
            resp = model.generate_content(
                f"다음 주제로 이번 주 최신 뉴스 5개를 찾아서 "
                f"'제목 | 핵심내용 2문장 | URL' 형식으로 한국어로 답변해줘: {query}",
                tools="google_search_retrieval",
            )
            collected.append(f"[{query}]\n{resp.text}")
            print(f"    ✅ {query[:45]}...")
        except Exception as e:
            print(f"    ⚠️  실패: {e}")

    return "\n\n---\n\n".join(collected)


# ─── 2. Claude로 뉴스레터 HTML 생성 ──────────────────────
def generate_newsletter_html(news_text: str) -> str:
    """수집된 뉴스를 Claude가 받아서 뉴스레터 HTML 작성"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today  = datetime.now().strftime("%Y년 %m월 %d일")

    prompt = f"""
당신은 AI 트렌드 전문 뉴스레터 에디터입니다. 오늘은 {today}입니다.
수신자: 구매대행 사업자·AI 자동화 프로그램 '쿠대' 운영자·유튜브 크리에이터

아래 Gemini가 수집한 뉴스를 바탕으로 한국어 HTML 뉴스레터를 작성하세요.

===== 수집된 뉴스 =====
{news_text}
========================

## 뉴스레터 구성
1. 헤더 (브랜드명 "골든서퍼 AI 위클리", 날짜, 이번 주 핵심 한 줄)
2. 이번 주 TOP 뉴스 4~5개 (이모지 제목 / 3문장 요약 / 원문링크 / 비즈니스 시사점)
3. 주목할 신규 AI 모델·도구
4. 구매대행·이커머스 AI 실무 활용 인사이트
5. 쿠대 운영자 관점 한마디
6. 이번 주 한 줄 결론
7. 푸터

## 디자인 스펙 (이메일 호환 인라인 CSS)
- body 배경: #0f172a
- 컨텐츠: max-width 680px, margin 0 auto, font-family: -apple-system, Arial, sans-serif
- 카드: background #1e293b, border-radius 12px, padding 20px, margin-bottom 16px
- 강조색: #6366f1 / 텍스트: #cbd5e1 / 제목: #f8fafc / 링크: #818cf8
- TOP뉴스 카드: border-left 4px solid #6366f1
- 이모지 풍부하게 사용
- 푸터: "🤖 골든서퍼 AI 위클리 · Powered by Gemini + Claude · {today}"

순수 HTML만 반환. 코드블록·마크다운 없이.
"""

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.content[0].text


# ─── 3. Gmail 발송 ────────────────────────────────────────
def send_email(html: str, subject: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText("AI 위클리 브리핑 - HTML 뷰어에서 확인하세요.", "plain", "utf-8"))
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
    fname = f"newsletter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  📄 저장: {fname}")
    return fname


# ─── 메인 ─────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("🤖 AI 위클리 뉴스레터 시작")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # 1. Gemini로 서치
    print("\n📡 Gemini로 AI 뉴스 수집 중...")
    news_text = collect_news_with_gemini()
    print("   수집 완료\n")

    # 2. Claude로 HTML 생성
    print("✍️  Claude가 뉴스레터 작성 중...")
    html = generate_newsletter_html(news_text)
    print("   작성 완료\n")

    save_preview(html)

    # 3. 발송
    today   = datetime.now().strftime("%Y년 %m월 %d일")
    subject = f"🤖 골든서퍼 AI 위클리 | {today}"

    if GMAIL_USER and GMAIL_APP_PW and RECIPIENT_EMAIL:
        print("📧 이메일 발송 중...")
        send_email(html, subject)
    else:
        print("⚠️  .env 파일 이메일 설정 필요")

    print("\n✅ 완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
