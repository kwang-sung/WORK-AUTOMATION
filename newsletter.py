#!/usr/bin/env python3
"""
골든서퍼 AI 위클리 - 매주 월요일 09:00 자동 실행

메일 3통 발송:
1. 요약본 - 빠르게 검토용
2. 카페용 - 친근한 톤 + 골든서퍼 총평
3. 블로그용 - SEO 최적화 + 골든서퍼 총평
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
    client    = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today     = datetime.now().strftime("%Y년 %m월 %d일")
    issue_num = datetime.now().strftime("%Y%m%d")

    # ── 요약본 ───────────────────────────────────────────
    summary_prompt = f"""
당신은 AI 트렌드 뉴스레터 에디터입니다. 오늘은 {today}입니다.
1~2분 안에 읽히는 모바일 최적화 요약 뉴스레터를 작성하세요.

===== 수집 정보 =====
{news_text}
=====================

## 구성
1. 헤더 (골든서퍼 AI 위클리 / {today})
2. ⚡ 이번 주 핵심 3가지 (각 1~2문장)
3. 🤖 TOP AI 뉴스 4개 (각 2문장)
4. 🛠️ 주목할 AI 도구 2개 (각 1문장)
5. 🛒 이커머스 AI 인사이트 2개 (각 1문장)
6. 🏄 골든서퍼 총평 (마치 골든서퍼가 직접 쓴 것처럼 3문장. "이번 주 AI 판도는..." 으로 시작)
7. 푸터 "상세 내용은 카페용·블로그용 메일을 확인하세요 📋"

## 디자인 (모바일 최적화 인라인 CSS)
- max-width 600px, margin 0 auto, font-family Arial sans-serif
- 헤더: background-color #0f172a, color #ffffff, padding 20px, text-align center, border-radius 10px
- 날짜: color #818cf8, font-weight 700, font-size 13px
- 섹션카드: background-color #f8fafc, border-left 4px solid #6366f1, padding 14px 16px, margin-bottom 10px, border-radius 0 8px 8px 0
- 섹션제목: font-size 14px, font-weight 800, color #1e293b, margin-bottom 8px
- 본문: font-size 13px, color #475569, line-height 1.7
- 골든서퍼총평: background-color #0f172a, color #ffffff, padding 20px, border-radius 10px, font-size 14px, line-height 1.8, margin-top 16px
- 총평제목: color #818cf8, font-weight 800, margin-bottom 10px, font-size 15px
- 푸터: text-align center, font-size 11px, color #94a3b8, padding 16px

이모지 적절히. 순수 HTML만 반환. 코드블록·마크다운 없이.
"""

    # ── 카페용 ───────────────────────────────────────────
    cafe_prompt = f"""
당신은 AI 트렌드를 구매대행 관점에서 전달하는 카페 운영자 골든서퍼입니다.
오늘은 {today}입니다. 카페 회원 18,000명에게 올릴 친근하고 실용적인 글을 작성하세요.

===== 수집 정보 =====
{news_text}
=====================

## 구성
1. 헤더 배너 (골든서퍼 AI 위클리 #{issue_num} / {today})
2. 이번 주 핵심 요약 박스 (3가지)
3. 🤖 주요 AI 뉴스 4~5개
   - 친근한 말투로 설명 5~6문장
   - 구매대행·이커머스 관점 시사점
4. 🛠️ 주목할 AI 도구 2~3개
   - 실무 활용법 구체적으로
5. 💡 이커머스·구매대행 AI 활용 팁 3가지
6. 🤖 쿠대 활용 TIP
   - 콘텐츠 중간(뉴스 2번째 카드 뒤)에 아래 HTML을 그대로 삽입:
   <div style="background-color:#fffbeb;border:1px solid #fcd34d;border-left:4px solid #e2b04a;border-radius:0 12px 12px 0;padding:18px 22px;display:flex;align-items:center;justify-content:space-between;gap:16px;margin:24px 0;">
  <div style="flex:1;">
    <div style="display:inline-block;background-color:#e2b04a;color:#1a1a2e;border-radius:4px;padding:2px 8px;font-size:10px;font-weight:800;margin-bottom:6px;">FREE</div>
    <div style="font-size:15px;font-weight:800;color:#1e293b;">쿠대 프로그램 — 지금 무료로 시작하세요</div>
    <div style="font-size:12px;color:#64748b;margin-top:3px;">구매대행 자동화의 시작 · 누적회원 15,900명</div>
  </div>
  <div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end;">
    <a href="https://admin.coudae.kr/#/login" style="background-color:#e2b04a;color:#1a1a2e;border-radius:8px;padding:10px 18px;font-size:13px;font-weight:800;white-space:nowrap;text-decoration:none;display:inline-block;">무료 시작 →</a>
    <div style="display:flex;align-items:center;gap:5px;font-size:11px;color:#94a3b8;white-space:nowrap;">
      <div style="width:14px;height:14px;background-color:#cbd5e1;border-radius:50% 50% 50% 0;display:inline-block;"></div>
      좌측 하단 말풍선으로 문의하세요
    </div>
  </div>
</div>
7. 🏄 골든서퍼 총평
   - "안녕하세요, 골든서퍼입니다." 로 시작
   - 이번 주 AI 트렌드 전체를 아우르는 인사이트 4~5문장
   - 구매대행 사업자 관점에서 실질적 조언
   - "다음 주에도 알찬 정보로 찾아오겠습니다 🏄" 로 마무리
8. 하단 SNS 배너 - 아래 HTML을 그대로 삽입:
   <div style="margin:24px 0;">
  <div style="font-size:13px;font-weight:800;color:#1e293b;margin-bottom:12px;">🔗 쿠대 공식 채널</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
    <a href="https://www.youtube.com/@coudae" style="background-color:#0f172a;border-radius:12px;padding:14px 16px;display:flex;align-items:center;gap:10px;border:1px solid #1e293b;text-decoration:none;">
      <div style="width:34px;height:34px;background-color:#cc0000;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;font-weight:800;flex-shrink:0;">▶</div>
      <div>
        <div style="font-size:13px;font-weight:800;color:#ffffff;">쿠대 유튜브</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">구매대행 실전 노하우</div>
      </div>
      <div style="margin-left:auto;color:#e2b04a;font-weight:800;">→</div>
    </a>
    <a href="https://cafe.naver.com/coudae" style="background-color:#0f172a;border-radius:12px;padding:14px 16px;display:flex;align-items:center;gap:10px;border:1px solid #1e293b;text-decoration:none;">
      <div style="width:34px;height:34px;background-color:#03c75a;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;font-weight:800;flex-shrink:0;">N</div>
      <div>
        <div style="font-size:13px;font-weight:800;color:#ffffff;">쿠대 네이버 카페</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">회원 18,000명 커뮤니티</div>
      </div>
      <div style="margin-left:auto;color:#e2b04a;font-weight:800;">→</div>
    </a>
    <a href="https://open.kakao.com/o/gKWnrBDg" style="background-color:#0f172a;border-radius:12px;padding:14px 16px;display:flex;align-items:center;gap:10px;border:1px solid #1e293b;text-decoration:none;">
      <div style="width:34px;height:34px;background-color:#fee500;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#3c1e1e;font-size:14px;font-weight:800;flex-shrink:0;">💬</div>
      <div>
        <div style="font-size:13px;font-weight:800;color:#ffffff;">쿠대 단톡방</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">실시간 소싱 정보 공유</div>
      </div>
      <div style="margin-left:auto;color:#e2b04a;font-weight:800;">→</div>
    </a>
    <a href="https://www.threads.com/@coudae_official" style="background-color:#0f172a;border-radius:12px;padding:14px 16px;display:flex;align-items:center;gap:10px;border:1px solid #1e293b;text-decoration:none;">
      <div style="width:34px;height:34px;background-color:#ffffff;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#000;font-size:14px;font-weight:800;flex-shrink:0;">@</div>
      <div>
        <div style="font-size:13px;font-weight:800;color:#ffffff;">쿠대 스레드</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">일상 인사이트 팔로우</div>
      </div>
      <div style="margin-left:auto;color:#e2b04a;font-weight:800;">→</div>
    </a>
  </div>
</div>
9. 푸터

## 디자인 (카페 복붙 최적화 인라인 CSS)
- backdrop-filter, filter, blur, opacity, 그라데이션 배경 절대 금지
- 외부 폰트 로드 금지
- max-width 720px, margin 0 auto
- font-family 'Apple SD Gothic Neo', 'Malgun Gothic', Arial, sans-serif
- background-color #ffffff

### 헤더
- background-color #0f172a, border-radius 16px, padding 40px 36px, text-align center
- 브랜드명: font-size 28px, font-weight 900, color #ffffff
- 강조단어: color #818cf8
- 날짜뱃지: background-color #6366f1, color #ffffff, border-radius 20px, padding 6px 20px, font-size 13px, font-weight 700, display inline-block, margin-top 14px

### 핵심요약박스
- background-color #f0f4ff, border-left 5px solid #6366f1, border-radius 8px, padding 20px 24px, margin 16px 0
- 제목: font-size 13px, font-weight 700, color #3730a3, margin-bottom 10px
- 항목: font-size 14px, color #1e293b, line-height 1.8

### 섹션제목
- font-size 20px, font-weight 900, color #1e293b
- border-left 5px solid #6366f1, padding-left 14px, margin 28px 0 14px

### 뉴스카드
- background-color #ffffff, border 1px solid #e2e8f0, border-radius 12px, padding 22px, margin-bottom 14px
- border-left 4px solid #6366f1
- 카드제목: font-size 16px, font-weight 800, color #0f172a, margin-bottom 10px
- 카드본문: font-size 14px, color #334155, line-height 1.9

### 시사점박스
- background-color #f0f4ff, border-radius 8px, padding 12px 16px, margin-top 10px
- font-size 13px, color #3730a3, line-height 1.8

### 쿠대CTA
- background-color #4f46e5, border-radius 12px, padding 22px, text-align center, margin 24px 0
- 제목: font-size 17px, font-weight 800, color #ffffff
- 설명: font-size 13px, color #c7d2fe, margin-top 8px

### 골든서퍼총평
- background-color #0f172a, border-radius 14px, padding 28px, margin-top 24px
- 제목: font-size 16px, font-weight 800, color #818cf8, margin-bottom 14px
- 본문: font-size 14px, color #e2e8f0, line-height 1.9

### 푸터
- text-align center, padding 20px, font-size 12px, color #94a3b8

이모지 풍부하게. 순수 HTML만 반환. 코드블록·마크다운 없이.
"""

    # ── 블로그용 ─────────────────────────────────────────
    blog_prompt = f"""
당신은 AI 트렌드 전문 블로그 에디터 골든서퍼입니다.
오늘은 {today}입니다. 네이버 블로그 SEO에 최적화된 전문 콘텐츠를 작성하세요.

===== 수집 정보 =====
{news_text}
=====================

## 구성
1. 헤더 배너 (골든서퍼 AI 위클리 #{issue_num} / {today})
2. 목차 박스
3. 서론 (AI 트렌드 관련 검색 키워드 포함, 3~4문장)
4. 🤖 주요 AI 뉴스 4~5개
   - SEO 키워드 포함 제목
   - 전문적 설명 7~8문장
   - 데이터·수치 적극 활용
   - 구매대행·이커머스 비즈니스 시사점
5. 🛠️ 주목할 AI 모델·도구 2~3개
   - 상세 스펙과 특징
   - 실무 활용 방법 구체적으로
6. 💼 구매대행·이커머스 AI 실무 전략
   - 구체적 활용 사례 4~5가지
   - 섹션 중간에 아래 HTML을 그대로 삽입:
   <div style="background-color:#0f172a;border-radius:14px;padding:24px 28px;display:flex;align-items:center;justify-content:space-between;gap:16px;border:1px solid #334155;margin:24px 0;">
  <div style="width:44px;height:44px;background-color:#6366f1;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;">🤖</div>
  <div style="flex:1;">
    <div style="font-size:16px;font-weight:800;color:#ffffff;">쿠대 — 구매대행 자동화 프로그램</div>
    <div style="font-size:12px;color:#94a3b8;margin-top:4px;">상품 등록·가격 모니터링·주문 관리 자동화 · 누적회원 15,900명</div>
  </div>
  <div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end;">
    <a href="https://admin.coudae.kr/#/login" style="background-color:#6366f1;color:#ffffff;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:800;white-space:nowrap;text-decoration:none;display:inline-block;">무료로 시작하기 →</a>
    <div style="display:flex;align-items:center;gap:5px;font-size:11px;color:#64748b;white-space:nowrap;">
      <div style="width:14px;height:14px;background-color:#475569;border-radius:50% 50% 50% 0;display:inline-block;flex-shrink:0;"></div>
      좌측 하단 말풍선으로 문의하세요
    </div>
  </div>
</div>
7. 🏄 골든서퍼 총평
   - "안녕하세요, AI·구매대행 전문가 골든서퍼입니다." 로 시작
   - 이번 주 AI 트렌드 전문가 분석 5~6문장
   - 구체적 실행 제안 포함
   - "다음 포스팅에서도 실전 인사이트로 찾아오겠습니다." 로 마무리
8. 하단 SNS 배너 - 아래 HTML을 그대로 삽입:
   <div style="margin:24px 0;">
  <div style="font-size:13px;font-weight:800;color:#1e293b;margin-bottom:12px;">🔗 쿠대 공식 채널</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
    <a href="https://www.youtube.com/@coudae" style="background-color:#0f172a;border-radius:12px;padding:14px 16px;display:flex;align-items:center;gap:10px;border:1px solid #1e293b;text-decoration:none;">
      <div style="width:34px;height:34px;background-color:#cc0000;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;font-weight:800;flex-shrink:0;">▶</div>
      <div>
        <div style="font-size:13px;font-weight:800;color:#ffffff;">쿠대 유튜브</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">구매대행 실전 노하우</div>
      </div>
      <div style="margin-left:auto;color:#e2b04a;font-weight:800;">→</div>
    </a>
    <a href="https://cafe.naver.com/coudae" style="background-color:#0f172a;border-radius:12px;padding:14px 16px;display:flex;align-items:center;gap:10px;border:1px solid #1e293b;text-decoration:none;">
      <div style="width:34px;height:34px;background-color:#03c75a;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;font-weight:800;flex-shrink:0;">N</div>
      <div>
        <div style="font-size:13px;font-weight:800;color:#ffffff;">쿠대 네이버 카페</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">회원 18,000명 커뮤니티</div>
      </div>
      <div style="margin-left:auto;color:#e2b04a;font-weight:800;">→</div>
    </a>
    <a href="https://open.kakao.com/o/gKWnrBDg" style="background-color:#0f172a;border-radius:12px;padding:14px 16px;display:flex;align-items:center;gap:10px;border:1px solid #1e293b;text-decoration:none;">
      <div style="width:34px;height:34px;background-color:#fee500;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#3c1e1e;font-size:14px;font-weight:800;flex-shrink:0;">💬</div>
      <div>
        <div style="font-size:13px;font-weight:800;color:#ffffff;">쿠대 단톡방</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">실시간 소싱 정보 공유</div>
      </div>
      <div style="margin-left:auto;color:#e2b04a;font-weight:800;">→</div>
    </a>
    <a href="https://www.threads.com/@coudae_official" style="background-color:#0f172a;border-radius:12px;padding:14px 16px;display:flex;align-items:center;gap:10px;border:1px solid #1e293b;text-decoration:none;">
      <div style="width:34px;height:34px;background-color:#ffffff;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#000;font-size:14px;font-weight:800;flex-shrink:0;">@</div>
      <div>
        <div style="font-size:13px;font-weight:800;color:#ffffff;">쿠대 스레드</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">일상 인사이트 팔로우</div>
      </div>
      <div style="margin-left:auto;color:#e2b04a;font-weight:800;">→</div>
    </a>
  </div>
</div>
9. 태그 (#AI트렌드 #구매대행 #이커머스자동화 등 10개)
9. 푸터

## 디자인 (블로그 최적화 인라인 CSS)
- backdrop-filter, filter, blur, opacity, 그라데이션 배경 절대 금지
- 외부 폰트 로드 금지
- max-width 720px, margin 0 auto
- font-family 'Apple SD Gothic Neo', 'Malgun Gothic', Arial, sans-serif
- background-color #ffffff

### 헤더
- background-color #0f172a, border-radius 16px, padding 40px 36px, text-align center
- 브랜드명: font-size 28px, font-weight 900, color #ffffff
- 날짜뱃지: background-color #6366f1, color #ffffff, border-radius 20px, padding 6px 20px, font-size 13px, font-weight 700, display inline-block, margin-top 14px

### 목차박스
- background-color #f8fafc, border 1px solid #e2e8f0, border-radius 10px, padding 20px 24px, margin 16px 0
- 제목: font-size 15px, font-weight 800, color #1e293b, margin-bottom 12px
- 항목: font-size 14px, color #475569, line-height 2.0, padding-left 16px

### 섹션제목
- font-size 22px, font-weight 900, color #0f172a
- border-bottom 3px solid #6366f1, padding-bottom 10px, margin 32px 0 16px

### 뉴스카드
- background-color #ffffff, border 1px solid #e2e8f0, border-radius 12px, padding 24px, margin-bottom 16px
- border-left 5px solid #6366f1
- 카드제목: font-size 18px, font-weight 800, color #0f172a, margin-bottom 12px
- 카드본문: font-size 14px, color #334155, line-height 2.0

### 시사점박스
- background-color #f0f4ff, border-radius 8px, padding 14px 18px, margin-top 12px
- font-size 13px, color #3730a3, line-height 1.8

### 골든서퍼총평
- background-color #0f172a, border-radius 14px, padding 30px, margin-top 28px
- 제목: font-size 17px, font-weight 800, color #818cf8, margin-bottom 16px
- 본문: font-size 15px, color #e2e8f0, line-height 2.0

### 태그영역
- margin-top 20px, padding 16px
- 태그: display inline-block, background-color #f1f5f9, color #475569, border-radius 20px, padding 4px 12px, font-size 12px, margin 4px

### 푸터
- text-align center, padding 20px, font-size 12px, color #94a3b8
- "🤖 골든서퍼 AI 위클리 | Powered by Gemini + Claude | {today}"

이모지 풍부하게. 순수 HTML만 반환. 코드블록·마크다운 없이.
"""

    print("  ✍️  요약본 작성 중...")
    summary_resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=3000,
        messages=[{"role": "user", "content": summary_prompt}]
    )

    print("  ✍️  카페용 작성 중...")
    cafe_resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=16000,
        messages=[{"role": "user", "content": cafe_prompt}]
    )

    print("  ✍️  블로그용 작성 중...")
    blog_resp = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=16000,
        messages=[{"role": "user", "content": blog_prompt}]
    )

    return (
        summary_resp.content[0].text,
        cafe_resp.content[0].text,
        blog_resp.content[0].text
    )


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
    summary_html, cafe_html, blog_html = generate_content(news_text)
    print("   작성 완료\n")

    save_preview(summary_html, "ai_summary")
    save_preview(cafe_html,    "ai_cafe")
    save_preview(blog_html,    "ai_blog")

    today = datetime.now().strftime("%Y년 %m월 %d일")

    print("📧 메일 발송 중...")
    send_email(summary_html, f"🤖 [요약] 골든서퍼 AI 위클리 | {today}")
    send_email(cafe_html,    f"☕ [카페용] 골든서퍼 AI 위클리 | {today}")
    send_email(blog_html,    f"📝 [블로그용] 골든서퍼 AI 위클리 | {today}")

    print("\n✅ 완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
