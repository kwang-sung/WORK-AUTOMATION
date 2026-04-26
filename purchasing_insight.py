#!/usr/bin/env python3
"""
골든서퍼 인사이트 - 구매대행 뉴스레터
매주 월요일·목요일 09:00 자동 실행

파이프라인:
1. Gemini → 뉴스 수집
2. Claude → 상세본(카페·블로그용) + 요약본(메일용) 작성
3. Playwright → 네이버 카페 자동 게시
4. Playwright → 네이버 블로그 자동 포스팅
5. Gmail → 요약본 + 카페링크 발송
"""

import os
import json
import time
import smtplib
import anthropic
from google import genai
from google.genai import types
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from playwright.sync_api import sync_playwright

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
NAVER_COOKIES     = os.environ.get("NAVER_COOKIES", "")

CAFE_ID       = "30518405"
MENU_ID       = "370"
WRITE_URL     = f"https://cafe.naver.com/f-e/cafes/{CAFE_ID}/menus/{MENU_ID}/articles/write"
BLOG_WRITE_URL = "https://blog.naver.com/gngsun/postwrite"

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

def collect_news_with_gemini() -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    collected = []
    for query in SEARCH_QUERIES:
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"다음 주제로 이번 주 최신 정보 5개를 찾아서 '제목 | 핵심내용 3문장' 형식으로 한국어 답변: {query}",
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            collected.append(f"[{query}]\n{resp.text}")
            print(f"    ✅ {query[:45]}...")
        except Exception as e:
            print(f"    ⚠️  실패: {e}")
    return "\n\n---\n\n".join(collected)

def generate_content(news_text: str) -> tuple:
    client    = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today     = datetime.now().strftime("%Y년 %m월 %d일")
    weekday   = ["월", "화", "수", "목", "금", "토", "일"][datetime.now().weekday()]
    issue_num = datetime.now().strftime("%Y%m%d")

    detail_prompt = f"""
당신은 구매대행 전문 콘텐츠 에디터 '골든서퍼'입니다. 오늘은 {today}({weekday}요일)입니다.
아래 수집된 정보로 네이버 카페·블로그에 올릴 심도 있는 HTML 콘텐츠를 작성하세요.

===== 수집 정보 =====
{news_text}
=====================

## 구성
1. 헤더 배너 (골든서퍼 인사이트 #{issue_num} / {today})
2. 이번 호 핵심 3줄 요약 박스
3. 국내 구매대행 트렌드 3개 (제목 / 상세설명 6~8문장 / 실전팁 3가지 / 주의사항)
4. 해외 소싱 추천 아이템 3~4개 (제목 / 상세설명 6~8문장 / 소싱방법 / 예상마진 / 주의사항)
5. 플랫폼·정책 업데이트 상세
6. 쿠대 프로그램 자연스러운 언급 ("소싱 리서치와 상품 등록 자동화는 쿠대 프로그램을 활용해보세요")
7. 골든서퍼 한마디 (🏄, 핵심 인사이트 3~4문장)
8. 푸터 "골든서퍼 인사이트 | {today} | Powered by Gemini + Claude"

## 디자인 (카페 복붙 최적화 인라인 CSS)
- max-width 720px, font-family Noto Sans KR Arial sans-serif
- 헤더: linear-gradient(135deg,#1a1a2e,#16213e,#0f3460), border-radius 16px, padding 40px, text-align center
- 날짜뱃지: background #e2b04a, color #1a1a2e, border-radius 20px, padding 6px 18px
- 요약박스: background #fef9ec, border-left 5px solid #e2b04a, border-radius 8px, padding 20px
- 카드: background #ffffff, border-radius 12px, box-shadow 0 2px 8px rgba(0,0,0,0.08), padding 24px, margin-bottom 16px
- 국내카드 border-top: 4px solid #3b82f6
- 해외카드 border-top: 4px solid #10b981
- 플랫폼카드 border-top: 4px solid #f59e0b
- 실전팁: background #f0fdf4, border-radius 8px, padding 14px, color #166534
- 쿠대CTA: background linear-gradient(135deg,#6366f1,#8b5cf6), color #fff, border-radius 12px, padding 20px, text-align center
- 골든서퍼한마디: linear-gradient(135deg,#1a1a2e,#0f3460), color #fff, border-radius 12px, padding 28px
- 이모지 풍부하게

순수 HTML만 반환. 코드블록·마크다운 없이.
"""

    summary_prompt = f"""
당신은 구매대행 전문 뉴스레터 에디터입니다. 오늘은 {today}({weekday}요일)입니다.
아래 수집된 정보로 1~2분 안에 읽히는 이메일용 요약 뉴스레터를 작성하세요.

===== 수집 정보 =====
{news_text}
=====================

## 구성
1. 헤더 (골든서퍼 인사이트 / {today})
2. 이번 호 핵심 3가지 (각 1~2문장)
3. 주요 트렌드 3개 (각 2~3문장)
4. 추천 소싱 아이템 3개 (각 1~2문장 + 예상마진)
5. CTA 버튼 "📌 카페에서 전체 내용 보기" (href={{CAFE_URL}})
6. 골든서퍼 한마디 (1~2문장)
7. 푸터

## 디자인 (이메일 호환 인라인 CSS)
- max-width 600px, font-family Arial sans-serif
- 헤더: background #1a1a2e, color #fff, padding 24px, border-radius 12px, text-align center
- 날짜: color #e2b04a, font-weight 700
- 항목: background #f8fafc, border-left 4px solid #e2b04a, padding 14px, margin-bottom 10px, border-radius 4px
- CTA: background #e2b04a, color #1a1a2e, padding 14px 28px, border-radius 8px, font-weight 800, text-decoration none, display inline-block
- 골든서퍼한마디: background #1a1a2e, color #fff, padding 16px, border-radius 8px
- 이모지 적절히

순수 HTML만 반환. 코드블록·마크다운 없이.
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
        max_tokens=2000,
        messages=[{"role": "user", "content": summary_prompt}]
    )

    return detail_resp.content[0].text, summary_resp.content[0].text

def load_cookies() -> list:
    if NAVER_COOKIES:
        return json.loads(NAVER_COOKIES)
    if os.path.exists("naver_cookies.json"):
        with open("naver_cookies.json", "r", encoding="utf-8") as f:
            return json.load(f)
    raise Exception("NAVER_COOKIES 환경변수가 없습니다!")

def post_to_naver(url: str, title: str, html_content: str, label: str) -> str:
    cookies = load_cookies()
    posted_url = ""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        context.add_cookies(cookies)
        page = context.new_page()
        print(f"  🌐 {label} 글쓰기 이동 중...")
        page.goto(url, wait_until="networkidle", timeout=30000)
        time.sleep(3)
        try:
            page.locator("input[placeholder*='제목']").first.fill(title)
            time.sleep(1)
            print(f"  ✅ {label} 제목 입력 완료")
        except Exception as e:
            print(f"  ⚠️  제목 실패: {e}")
        try:
            page.evaluate(f"""
                const iframes = document.querySelectorAll('iframe');
                for (const iframe of iframes) {{
                    try {{
                        const doc = iframe.contentDocument || iframe.contentWindow.document;
                        const body = doc.querySelector('[contenteditable="true"]');
                        if (body) {{
                            body.innerHTML = {json.dumps(html_content)};
                            body.dispatchEvent(new Event('input', {{bubbles: true}}));
                            break;
                        }}
                    }} catch(e) {{}}
                }}
            """)
            time.sleep(2)
            print(f"  ✅ {label} 본문 입력 완료")
        except Exception as e:
            print(f"  ⚠️  본문 실패: {e}")
        try:
            for btn_text in ["등록", "발행", "완료", "올리기"]:
                btn = page.locator(f"button:has-text('{btn_text}')").first
                if btn.is_visible():
                    btn.click()
                    time.sleep(3)
                    break
            posted_url = page.url
            print(f"  ✅ {label} 완료 → {posted_url}")
        except Exception as e:
            print(f"  ⚠️  등록 실패: {e}")
        browser.close()
    return posted_url

def send_email(html: str, subject: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText("골든서퍼 인사이트", "plain", "utf-8"))
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

def main():
    print("=" * 55)
    print("🏄 골든서퍼 인사이트 전체 파이프라인 시작")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    print("\n📡 Gemini 뉴스 수집 중...")
    news_text = collect_news_with_gemini()
    print("   수집 완료\n")

    print("✍️  Claude 콘텐츠 작성 중...")
    detail_html, summary_html = generate_content(news_text)
    print("   작성 완료\n")

    today   = datetime.now().strftime("%Y년 %m월 %d일")
    weekday = ["월", "화", "수", "목", "금", "토", "일"][datetime.now().weekday()]
    title   = f"🏄 골든서퍼 인사이트 | {today}({weekday}) 구매대행 트렌드 리포트"

    # 카페 게시
    cafe_url = ""
    print("📌 네이버 카페 게시 중...")
    try:
        cafe_url = post_to_naver(WRITE_URL, title, detail_html, "카페")
    except Exception as e:
        print(f"  ❌ 카페 실패: {e}")

    # 블로그 포스팅
    print("\n📌 네이버 블로그 포스팅 중...")
    try:
        post_to_naver(BLOG_WRITE_URL, title, detail_html, "블로그")
    except Exception as e:
        print(f"  ❌ 블로그 실패: {e}")

    # 카페 링크 삽입
    summary_html = summary_html.replace(
        "{CAFE_URL}",
        cafe_url if cafe_url else "https://cafe.naver.com/coudae"
    )

    # 메일 발송
    print("\n📧 이메일 발송 중...")
    subject = f"🏄 골든서퍼 인사이트 | {today}({weekday}) - 카페 새글 알림"
    if GMAIL_USER and GMAIL_APP_PW and RECIPIENT_EMAIL:
        send_email(summary_html, subject)

    print("\n✅ 전체 파이프라인 완료!")
    print(f"   카페: {cafe_url}")
    print("=" * 55)

if __name__ == "__main__":
    main()
