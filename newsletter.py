#!/usr/bin/env python3
"""
AI 위클리 뉴스레터 - 매주 월요일 09:00 자동 발송
Gemini 서치 → Claude 글쓰기 → 블로그(AI 트렌드) 포스팅 → Gmail 발송
"""

import os
import smtplib
import anthropic
from google import genai
from google.genai import types
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from naver_poster import post_to_blog

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


def collect_news_with_gemini() -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    collected = []
    for query in SEARCH_QUERIES:
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"다음 주제로 이번 주 최신 뉴스 5개를 찾아서 '제목 | 핵심내용 2문장' 형식으로 한국어 답변: {query}",
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            collected.append(f"[{query}]\n{resp.text}")
            print(f"    ✅ {query[:45]}...")
        except Exception as e:
            print(f"    ⚠️  실패: {e}")
    return "\n\n---\n\n".join(collected)


def generate_newsletter_html(news_text: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today  = datetime.now().strftime("%Y년 %m월 %d일")

    prompt = f"""
당신은 AI 트렌드 전문 뉴스레터 에디터입니다. 오늘은 {today}입니다.
수신자: 구매대행 사업자·AI 자동화 프로그램 '쿠대' 운영자·유튜브 크리에이터

아래 Gemini가 수집한 뉴스로 한국어 HTML 뉴스레터를 작성하세요.

===== 수집된 뉴스 =====
{news_text}
========================

## 구성
1. 헤더 (브랜드명 "골든서퍼 AI 위클리", 날짜, 이번 주 핵심 한 줄)
2. 이번 주 TOP 뉴스 4~5개 (이모지 제목 / 4~5문장 요약 / 비즈니스 시사점)
3. 주목할 신규 AI 모델·도구 (상세 설명)
4. 구매대행·이커머스 AI 실무 활용 인사이트 (구체적 활용법)
5. 쿠대 운영자 관점 한마디
6. 이번 주 한 줄 결론
7. 푸터 "🤖 골든서퍼 AI 위클리 · Powered by Gemini + Claude · {today}"

## 디자인 (이메일 호환 인라인 CSS - 절대 준수)

### 핵심 규칙
- backdrop-filter, filter, opacity, blur 절대 사용 금지 (뿌옇게 보이는 원인)
- 모든 색상은 명시적 단색으로 (그라데이션 금지)
- 어두운 배경 위 텍스트는 반드시 밝은 색상 명시

### 전체 레이아웃
- body: background-color #0f172a, margin 0, padding 0
- wrapper: max-width 680px, margin 0 auto, padding 16px, font-family Arial sans-serif

### 헤더
- background-color: #1e3a5f (단색만)
- border-radius 16px, padding 36px, text-align center
- 브랜드명: font-size 28px, font-weight 900, color #ffffff (필수)
- 날짜: color #e2b04a, font-size 13px
- 핵심한줄: color #94a3b8, font-size 14px

### 뉴스 카드
- background-color: #1e293b (단색)
- border-radius 12px, padding 20px, margin-bottom 16px
- border-left: 4px solid #6366f1
- 카드 제목: color #f8fafc, font-size 16px, font-weight 800
- 카드 본문: color #cbd5e1, font-size 14px, line-height 1.8
- 비즈니스 시사점 박스: background-color #0f2744, border-radius 8px, padding 12px, color #93c5fd

### 섹션 제목
- color #f8fafc, font-size 18px, font-weight 800
- border-bottom: 2px solid #6366f1, padding-bottom 8px

### 쿠대 CTA
- background-color: #4f46e5 (단색)
- border-radius 12px, padding 20px, text-align center, color #ffffff

### 푸터
- background-color: #0f172a, color #475569, text-align center, padding 20px

순수 HTML만 반환. 코드블록·마크다운 없이.
"""
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.content[0].text


def send_email(html: str, subject: str, blog_url: str = "") -> bool:
    # 블로그 링크 삽입
    if blog_url:
        cta = f'<div style="text-align:center;margin:20px 0"><a href="{blog_url}" style="background:#6366f1;color:#fff;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:800">📖 블로그에서 전체 내용 보기</a></div>'
        html = html.replace("</body>", f"{cta}</body>")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText("AI 위클리 브리핑", "plain", "utf-8"))
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


def save_preview(html: str) -> str:
    fname = f"newsletter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  📄 저장: {fname}")
    return fname


def main():
    print("=" * 55)
    print("🤖 AI 위클리 뉴스레터 시작")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    # 1. Gemini 서치
    print("\n📡 Gemini로 AI 뉴스 수집 중...")
    news_text = collect_news_with_gemini()
    print("   수집 완료\n")

    # 2. Claude 작성
    print("✍️  Claude가 뉴스레터 작성 중...")
    html = generate_newsletter_html(news_text)
    print("   작성 완료\n")

    save_preview(html)

    today   = datetime.now().strftime("%Y년 %m월 %d일")
    title   = f"🤖 골든서퍼 AI 위클리 | {today} AI 트렌드 리포트"
    subject = f"🤖 골든서퍼 AI 위클리 | {today}"

    # 3. 블로그 포스팅 (AI 트렌드 카테고리)
    blog_url = ""
    print("📌 네이버 블로그 포스팅 중... (AI 트렌드)")
    try:
        blog_url = post_to_blog(title, html, "AI 트렌드")
    except Exception as e:
        print(f"  ❌ 블로그 실패: {e}")

    # 4. 메일 발송 (블로그 링크 포함)
    print("\n📧 이메일 발송 중...")
    if GMAIL_USER and GMAIL_APP_PW and RECIPIENT_EMAIL:
        send_email(html, subject, blog_url)
    else:
        print("⚠️  이메일 환경변수 미설정")

    print("\n✅ 완료!")
    print(f"   블로그: {blog_url}")
    print("=" * 55)


if __name__ == "__main__":
    main()
