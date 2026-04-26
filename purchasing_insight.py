#!/usr/bin/env python3
"""
골든서퍼 인사이트 - 구매대행 뉴스레터
매주 월요일·목요일 09:00 자동 실행

메일 2통 발송:
1. 요약본 - 빠르게 검토용
2. 상세본 - 카페·블로그 복붙용
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
    "구매대행 최신 트렌드 아이템 2026 국내",
    "해외직구 인기상품 트렌드 2026 이번주",
    "일본 인기 상품 트렌드 2026 소싱 한국",
    "Japan trending products ecommerce 2026",
    "쿠팡 네이버 스마트스토어 구매대행 정책 2026",
    "해외 이커머스 배송 관세 정책 변경 2026",
    "국내 미출시 해외 인기 상품 아이템 2026",
    "Super Delivery Yodobashi trending items Korea 2026",
]


# ─── 1. Gemini 서치 ───────────────────────────────────────
def collect_news() -> str:
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


# ─── 2. Claude 글쓰기 ─────────────────────────────────────
def generate_content(news_text: str) -> tuple:
    client    = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today     = datetime.now().strftime("%Y년 %m월 %d일")
    weekday   = ["월", "화", "수", "목", "금", "토", "일"][datetime.now().weekday()]
    issue_num = datetime.now().strftime("%Y%m%d")

    # ── 상세본 (카페·블로그 복붙용) ──────────────────────
    detail_prompt = f"""
당신은 구매대행 전문 콘텐츠 에디터 '골든서퍼'입니다.
오늘은 {today}({weekday}요일)입니다.

아래 수집된 정보로 네이버 카페·블로그에 바로 복붙 가능한
완성형 HTML 콘텐츠를 작성하세요.

===== 수집 정보 =====
{news_text}
=====================

## 구성
1. 헤더 배너 (골든서퍼 인사이트 #{issue_num} / {today} / {weekday}요일)
2. 이번 호 핵심 3줄 요약 박스
3. 국내 구매대행 트렌드 3개
   - 섹션 제목 / 아이콘 이모지
   - 상세 설명 6~8문장
   - 실전 적용 팁 3가지 (번호 목록)
   - 주의사항
4. 해외 소싱 추천 아이템 3~4개
   - 아이템명 + 이모지
   - 상세 설명 6~8문장
   - 소싱 방법 (구체적 사이트명 포함)
   - 예상 마진율
   - 주의사항
5. 플랫폼·정책 업데이트
6. 쿠대 프로그램 자연스러운 CTA
   ("이런 소싱 작업을 자동화하려면 쿠대 프로그램을 활용해보세요 →")
7. 골든서퍼 한마디 (🏄, 핵심 인사이트 3~4문장)
8. 푸터

## 디자인 (카페·블로그 복붙 최적화 - 인라인 CSS 필수)
### 절대 금지
- backdrop-filter, filter, blur, opacity 사용 금지
- 그라데이션 배경 금지 (단색만)
- 외부 폰트 로드 금지

### 전체
- max-width: 720px, margin: 0 auto
- font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', Arial, sans-serif
- background-color: #ffffff

### 헤더 배너
- background-color: #1a3a6b
- border-radius: 16px, padding: 40px 36px, text-align: center
- 브랜드명: font-size 30px, font-weight 900, color #ffffff
- 부제: font-size 14px, color #94a3b8, margin-top 8px
- 날짜 뱃지: background-color #e2b04a, color #1a1a2e, border-radius 20px, padding 6px 20px, font-size 13px, font-weight 700, display inline-block, margin-top 16px

### 핵심 요약 박스
- background-color: #fffbeb
- border-left: 5px solid #e2b04a
- border-radius: 8px, padding: 20px 24px, margin: 16px 0
- 제목: font-size 14px, font-weight 700, color #92400e, margin-bottom 12px
- 항목: font-size 14px, color #1e293b, line-height 1.8, padding-left 20px

### 섹션 제목
- font-size: 20px, font-weight: 900, color: #1e293b
- border-left: 5px solid #e2b04a, padding-left: 14px
- margin: 32px 0 16px

### 뉴스 카드
- background-color: #ffffff
- border: 1px solid #e2e8f0
- border-radius: 12px, padding: 24px, margin-bottom: 16px
- 국내트렌드: border-top 4px solid #3b82f6
- 해외소싱: border-top 4px solid #10b981
- 플랫폼: border-top 4px solid #f59e0b
- 카드 제목: font-size 17px, font-weight 800, color #0f172a, margin-bottom 12px
- 카드 본문: font-size 14px, color #334155, line-height 1.9

### 실전팁 박스
- background-color: #f0fdf4
- border-radius: 8px, padding: 16px 20px
- font-size: 13px, color: #166534, line-height: 1.8
- margin-top: 12px

### 마진 뱃지
- display: inline-block
- background-color: #dcfce7, color: #166534
- border-radius: 6px, padding: 4px 12px
- font-size: 13px, font-weight: 700

### 쿠대 CTA
- background-color: #4f46e5
- border-radius: 12px, padding: 24px, text-align: center, margin: 24px 0
- 제목: font-size 18px, font-weight 800, color #ffffff
- 설명: font-size 14px, color #c7d2fe, margin-top 8px

### 골든서퍼 한마디
- background-color: #1a3a6b
- border-radius: 12px, padding: 28px
- font-size: 15px, color: #ffffff, line-height: 1.9

### 푸터
- text-align: center, padding: 24px
- font-size: 12px, color: #94a3b8

이모지 풍부하게 사용. 순수 HTML만 반환. 코드블록·마크다운 없이.
"""

    # ── 요약본 (빠른 검토용) ─────────────────────────────
    summary_prompt = f"""
당신은 구매대행 전문 뉴스레터 에디터입니다.
오늘은 {today}({weekday}요일)입니다.

아래 수집된 정보로 1~2분 안에 읽히는
모바일 최적화 이메일 요약 뉴스레터를 작성하세요.

===== 수집 정보 =====
{news_text}
=====================

## 구성
1. 간결한 헤더 (골든서퍼 인사이트 / {today})
2. ⚡ 이번 호 핵심 3가지 (각 1~2문장, 불릿)
3. 🇰🇷 국내 트렌드 TOP 3 (각 2문장)
4. 🌏 해외 소싱 추천 TOP 3 (각 1문장 + 마진)
5. 📢 플랫폼 업데이트 1~2개 (각 1문장)
6. 🏄 골든서퍼 한마디 (1~2문장)
7. 푸터 "상세 내용은 별도 메일을 확인하세요"

## 디자인 (모바일 최적화 인라인 CSS)
- max-width: 600px, margin: 0 auto
- font-family: Arial, sans-serif
- 헤더: background-color #1a3a6b, color #ffffff, padding 20px, text-align center, border-radius 10px
- 날짜: color #e2b04a, font-weight 700, font-size 13px
- 섹션: background-color #f8fafc, border-left 4px solid #e2b04a, padding 14px 16px, margin-bottom 10px, border-radius 4px
- 섹션제목: font-size 14px, font-weight 800, color #1e293b, margin-bottom 8px
- 본문: font-size 13px, color #475569, line-height 1.7
- 마진뱃지: background-color #dcfce7, color #166534, border-radius 4px, padding 2px 8px, font-size 12px, font-weight 700
- 골든서퍼: background-color #1a3a6b, color #ffffff, padding 16px, border-radius 8px, font-size 13px
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
    msg.attach(MIMEText("골든서퍼 인사이트", "plain", "utf-8"))
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
    print("🏄 골든서퍼 인사이트 시작")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    print("\n📡 Gemini 뉴스 수집 중...")
    news_text = collect_news()
    print("   수집 완료\n")

    print("✍️  Claude 콘텐츠 작성 중...")
    detail_html, summary_html = generate_content(news_text)
    print("   작성 완료\n")

    save_preview(detail_html, "detail")
    save_preview(summary_html, "summary")

    today   = datetime.now().strftime("%Y년 %m월 %d일")
    weekday = ["월", "화", "수", "목", "금", "토", "일"][datetime.now().weekday()]

    # 요약본 발송
    print("📧 요약본 메일 발송 중...")
    send_email(
        summary_html,
        f"🏄 [요약] 골든서퍼 인사이트 | {today}({weekday})"
    )

    # 상세본 발송
    print("📧 상세본 메일 발송 중...")
    send_email(
        detail_html,
        f"📋 [카페·블로그용] 골든서퍼 인사이트 | {today}({weekday})"
    )

    print("\n✅ 완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
