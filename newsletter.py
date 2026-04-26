#!/usr/bin/env python3
"""
골든서퍼 AI 위클리 - 매주 월요일 09:00 자동 실행

메일 2통 발송:
1. 요약본 - 빠르게 검토용
2. 상세본 - 블로그 복붙용
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

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY    = os.environ.get("GEMINI_API_KEY", "")
GMAIL_USER        = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PW      = os.environ.get("GMAIL_APP_PW", "")
RECIPIENT_EMAIL   = os.environ.get("RECIPIENT_EMAIL", "")

SEARCH_QUERIES = [
    "latest AI news this week OpenAI Anthropic Google 2026",
    "new AI model release this week 2026",
    "AI ecommerce automation tools 2026",
    "AI 이번주 최신 뉴스 모델 출시 2026",
    "AI agent productivity business tools this week",
    "AI 구매대행 자동화 이커머스 2026",
]


# ─── 1. Gemini 서치 ───────────────────────────────────────
def collect_news() -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    collected = []
    for query in SEARCH_QUERIES:
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"다음 주제로 이번 주 최신 뉴스 5개를 찾아서 '제목 | 핵심내용 3문장' 형식으로 한국어 답변: {query}",
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            collected.append(f"[{query}]\n{resp.text}")
            print(f"    ✅ {query[:45]}...")
        except Exception as e:
            print(f"    ⚠️  실패: {e}")
    return "\n\n---\n\n".join(collected)


# ─── 2. Claude 글쓰기 ─────────────────────────────────────
def generate_content(news_text: str) -> tuple:
    client  = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today   = datetime.now().strftime("%Y년 %m월 %d일")
    issue_num = datetime.now().strftime("%Y%m%d")

    # ── 상세본 (블로그 복붙용) ───────────────────────────
    detail_prompt = f"""
당신은 AI 트렌드 전문 콘텐츠 에디터 '골든서퍼'입니다.
오늘은 {today}입니다.

아래 수집된 정보로 네이버 블로그에 바로 복붙 가능한
완성형 HTML 콘텐츠를 작성하세요.

===== 수집 정보 =====
{news_text}
=====================

## 구성
1. 헤더 배너 (골든서퍼 AI 위클리 #{issue_num} / {today})
2. 이번 주 핵심 3줄 요약 박스
3. TOP AI 뉴스 4~5개
   - 뉴스 제목 + 이모지
   - 상세 설명 5~7문장
   - 비즈니스 시사점 (구매대행·이커머스 관점)
4. 주목할 신규 AI 모델·도구
   - 모델명 + 특징 상세
   - 실무 활용 방법
5. 구매대행·이커머스 AI 실무 인사이트
   - 구체적 활용 사례
   - 실전 적용 팁
6. 쿠대 운영자 관점 한마디
7. 이번 주 결론
8. 푸터

## 디자인 (블로그 복붙 최적화 - 인라인 CSS 필수)
### 절대 금지
- backdrop-filter, filter, blur, opacity 사용 금지
- 그라데이션 배경 금지 (단색만)
- 외부 폰트 로드 금지

### 전체
- max-width: 720px, margin: 0 auto
- font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', Arial, sans-serif
- background-color: #ffffff

### 헤더 배너
- background-color: #0f172a
- border-radius: 16px, padding: 40px 36px, text-align: center
- 브랜드명: font-size 30px, font-weight 900, color #ffffff
- 강조: color #6366f1
- 날짜 뱃지: background-color #6366f1, color #ffffff, border-radius 20px, padding 6px 20px, font-size 13px, font-weight 700, display inline-block, margin-top 16px

### 핵심 요약 박스
- background-color: #f0f4ff
- border-left: 5px solid #6366f1
- border-radius: 8px, padding: 20px 24px, margin: 16px 0
- 제목: font-size 14px, font-weight 700, color #3730a3
- 항목: font-size 14px, color #1e293b, line-height 1.8

### 섹션 제목
- font-size: 20px, font-weight: 900, color: #1e293b
- border-left: 5px solid #6366f1, padding-left: 14px
- margin: 32px 0 16px

### 뉴스 카드
- background-color: #ffffff
- border: 1px solid #e2e8f0
- border-radius: 12px, padding: 24px, margin-bottom: 16px
- border-left: 4px solid #6366f1
- 카드 제목: font-size 17px, font-weight 800, color #0f172a, margin-bottom 12px
- 카드 본문: font-size 14px, color #334155, line-height 1.9

### 비즈니스 시사점 박스
- background-color: #f0f4ff
- border-radius: 8px, padding: 14px 18px, margin-top 12px
- font-size: 13px, color: #3730a3, line-height: 1.8

### 쿠대 한마디
- background-color: #0f172a
- border-radius: 12px, padding: 24px
- font-size: 15px, color: #e2e8f0, line-height: 1.9

### 푸터
- text-align: center, padding: 24px
- font-size: 12px, color: #94a3b8
- "🤖 골든서퍼 AI 위클리 | Powered by Gemini + Claude | {today}"

이모지 풍부하게. 순수 HTML만 반환. 코드블록·마크다운 없이.
"""

    # ── 요약본 (빠른 검토용) ─────────────────────────────
    summary_prompt = f"""
당신은 AI 트렌드 전문 뉴스레터 에디터입니다.
오늘은 {today}입니다.

아래 수집된 정보로 1~2분 안에 읽히는
모바일 최적화 이메일 요약 뉴스레터를 작성하세요.

===== 수집 정보 =====
{news_text}
=====================

## 구성
1. 간결한 헤더 (골든서퍼 AI 위클리 / {today})
2. ⚡ 이번 주 핵심 3가지 (각 1~2문장)
3. 🤖 TOP AI 뉴스 4개 (각 2문장)
4. 🛠️ 주목할 AI 도구 2개 (각 1문장)
5. 🛒 이커머스 AI 인사이트 2개 (각 1문장)
6. 💡 이번 주 결론 (1문장)
7. 푸터 "상세 내용은 별도 메일을 확인하세요"

## 디자인 (모바일 최적화 인라인 CSS)
- max-width: 600px, margin: 0 auto
- font-family: Arial, sans-serif
- 헤더: background-color #0f172a, color #ffffff, padding 20px, text-align center, border-radius 10px
- 날짜: color #818cf8, font-weight 700, font-size 13px
- 섹션: background-color #f8fafc, border-left 4px solid #6366f1, padding 14px 16px, margin-bottom 10px, border-radius 4px
- 섹션제목: font-size 14px, font-weight 800, color #1e293b, margin-bottom 8px
- 본문: font-size 13px, color #475569, line-height 1.7
- 결론박스: background-color #0f172a, color #ffffff, padding 16px, border-radius 8px, font-size 14px, font-weight 700
- 푸터: text-align center, font-size 11px, color #94a3b8, padding 16px

이모지 적절히. 순수 HTML만 반환. 코드블록·마크다운 없이.
"""

    print("  ✍️  상세본 작성 중...")
    detail_resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=6000,
        messages=[{"role": "user", "content": detail_prompt}]
    )

    print("  ✍️  요약본 작성 중...")
    summary_resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2500,
        messages=[{"role": "user", "content": summary_prompt}]
    )

    return detail_resp.content[0].text, summary_resp.content[0].text


# ─── 3. 메일 발송 ─────────────────────────────────────────
def send_email(html: str, subject: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText("골든서퍼 AI 위클리", "plain", "utf-8"))
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
def save_preview(html: str, prefix: str) -> str:
    fname = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  📄 저장: {fname}")
    return fname


# ─── 메인 ─────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("🤖 골든서퍼 AI 위클리 시작")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    print("\n📡 Gemini 뉴스 수집 중...")
    news_text = collect_news()
    print("   수집 완료\n")

    print("✍️  Claude 콘텐츠 작성 중...")
    detail_html, summary_html = generate_content(news_text)
    print("   작성 완료\n")

    save_preview(detail_html, "ai_detail")
    save_preview(summary_html, "ai_summary")

    today = datetime.now().strftime("%Y년 %m월 %d일")

    # 요약본 발송
    print("📧 요약본 메일 발송 중...")
    send_email(
        summary_html,
        f"🤖 [요약] 골든서퍼 AI 위클리 | {today}"
    )

    # 상세본 발송
    print("📧 상세본 메일 발송 중...")
    send_email(
        detail_html,
        f"📋 [블로그용] 골든서퍼 AI 위클리 | {today}"
    )

    print("\n✅ 완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
