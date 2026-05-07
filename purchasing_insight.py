#!/usr/bin/env python3
"""
쿠대 마스터 인사이트 - 구매대행 뉴스레터
매주 월요일·목요일 09:30 자동 실행

메일 2통 발송:
1. 카페용 - 친근한 톤 + 쿠대 마스터 총평
2. 블로그용 - SEO 최적화 + 쿠대 마스터 총평

중복방지: 이전 발행 이력과 비교하여 중복 제거
팩트검증: 작성된 글의 수치 Gemini로 재검증 후 자동 수정
"""

import os
import json
import base64
import smtplib
import requests
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
GITHUB_TOKEN      = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO       = os.environ.get("GITHUB_REPOSITORY", "")
HISTORY_FILE      = "data/insight_history.json"

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

CAFE_SNS_BANNER = """<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-top:24px;border-top:2px solid #e2e8f0;">
<tr><td style="padding:16px 0 8px 0;"><p style="font-size:14px;font-weight:800;color:#1e293b;margin:0;">🔗 쿠대 공식채널</p></td></tr>
<tr><td style="padding:6px 0;border-bottom:1px solid #f1f5f9;">💬 카톡단체방 &nbsp;<a href="https://open.kakao.com/o/gKWnrBDg" style="color:#e2b04a;font-weight:700;text-decoration:none;">바로가기 →</a></td></tr>
<tr><td style="padding:6px 0;border-bottom:1px solid #f1f5f9;">🧵 스레드 &nbsp;<a href="https://www.threads.com/@coudae_official" style="color:#e2b04a;font-weight:700;text-decoration:none;">바로가기 →</a></td></tr>
<tr><td style="padding:6px 0;border-bottom:1px solid #f1f5f9;">▶ 유튜브 &nbsp;<a href="https://www.youtube.com/@coudae" style="color:#e2b04a;font-weight:700;text-decoration:none;">바로가기 →</a></td></tr>
<tr><td style="padding:6px 0;">📝 블로그 &nbsp;<a href="https://blog.naver.com/gngsun" style="color:#e2b04a;font-weight:700;text-decoration:none;">바로가기 →</a></td></tr>
</table>"""

BLOG_SNS_BANNER = """<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-top:24px;border-top:2px solid #e2e8f0;">
<tr><td style="padding:16px 0 8px 0;"><p style="font-size:14px;font-weight:800;color:#1e293b;margin:0;">🔗 쿠대 공식채널</p></td></tr>
<tr><td style="padding:6px 0;border-bottom:1px solid #f1f5f9;">💬 카톡단체방 &nbsp;<a href="https://open.kakao.com/o/gKWnrBDg" style="color:#e2b04a;font-weight:700;text-decoration:none;">바로가기 →</a></td></tr>
<tr><td style="padding:6px 0;border-bottom:1px solid #f1f5f9;">🧵 스레드 &nbsp;<a href="https://www.threads.com/@coudae_official" style="color:#e2b04a;font-weight:700;text-decoration:none;">바로가기 →</a></td></tr>
<tr><td style="padding:6px 0;border-bottom:1px solid #f1f5f9;">▶ 유튜브 &nbsp;<a href="https://www.youtube.com/@coudae" style="color:#e2b04a;font-weight:700;text-decoration:none;">바로가기 →</a></td></tr>
<tr><td style="padding:6px 0;">☕ 카페 &nbsp;<a href="https://cafe.naver.com/coudae" style="color:#e2b04a;font-weight:700;text-decoration:none;">바로가기 →</a></td></tr>
</table>"""


# ─── 0. 발행 이력 관리 ────────────────────────────────────
def load_history() -> dict:
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return {"items": [], "topics": []}
    try:
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        resp = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{HISTORY_FILE}", headers=headers)
        if resp.status_code == 200:
            content = base64.b64decode(resp.json()["content"]).decode("utf-8")
            return json.loads(content)
    except Exception as e:
        print(f"  ⚠️  이력 로드 실패: {e}")
    return {"items": [], "topics": []}


def save_history(history: dict, new_items: list, new_topics: list):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    try:
        history["items"]  = (history.get("items",  []) + new_items)[-40:]
        history["topics"] = (history.get("topics", []) + new_topics)[-40:]
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        content = base64.b64encode(json.dumps(history, ensure_ascii=False, indent=2).encode()).decode()
        sha = None
        resp = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{HISTORY_FILE}", headers=headers)
        if resp.status_code == 200:
            sha = resp.json().get("sha")
        payload = {"message": f"인사이트 이력 업데이트 {datetime.now().strftime('%Y%m%d')}", "content": content}
        if sha:
            payload["sha"] = sha
        requests.put(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{HISTORY_FILE}", headers=headers, json=payload)
        print("  ✅ 발행 이력 저장 완료")
    except Exception as e:
        print(f"  ⚠️  이력 저장 실패: {e}")


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


# ─── 2. 중복 제거 ─────────────────────────────────────────
def remove_duplicates(news_text: str, history: dict) -> str:
    if not history.get("items") and not history.get("topics"):
        print("  ℹ️  이력 없음 - 중복 체크 스킵")
        return news_text
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prev_items  = "\n".join(history.get("items",  [])[-20:])
    prev_topics = "\n".join(history.get("topics", [])[-20:])
    resp = client.messages.create(
        model="claude-sonnet-4-5", max_tokens=8000,
        messages=[{"role": "user", "content": f"""
아래 [수집된 뉴스]에서 [이전 발행 이력]과 중복되는 뉴스/토픽을 제거해주세요.

[이전 발행 이력 - 아이템/뉴스]
{prev_items}

[이전 발행 이력 - 토픽]
{prev_topics}

[수집된 뉴스]
{news_text}

규칙:
- 동일하거나 매우 유사한 뉴스/토픽 제거
- 완전히 새로운 내용만 남기기
- 중복 제거 후에도 최소 5개 이상 뉴스 유지
- 중복 제거된 뉴스 텍스트만 반환 (설명 없이)
"""}]
    )
    print("  ✅ 중복 제거 완료")
    return resp.content[0].text.strip()


# ─── 3. Claude 글쓰기 ─────────────────────────────────────
def generate_content(news_text: str) -> tuple:
    client    = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today     = datetime.now().strftime("%Y년 %m월 %d일")
    weekday   = ["월", "화", "수", "목", "금", "토", "일"][datetime.now().weekday()]
    issue_num = datetime.now().strftime("%Y%m%d")

    CTA_CAFE = """<div style="background-color:#fffbeb;border:1px solid #fcd34d;border-left:4px solid #e2b04a;border-radius:0 12px 12px 0;padding:18px 22px;display:flex;align-items:center;justify-content:space-between;gap:16px;margin:24px 0;">
  <div style="flex:1;">
    <div style="display:inline-block;background-color:#e2b04a;color:#1a1a2e;border-radius:4px;padding:2px 8px;font-size:10px;font-weight:800;margin-bottom:6px;">FREE</div>
    <div style="font-size:15px;font-weight:800;color:#1e293b;">쿠대 프로그램 — 지금 무료로 시작하세요</div>
    <div style="font-size:12px;color:#64748b;margin-top:3px;">구매대행 자동화의 시작 · 누적회원 300명</div>
  </div>
  <div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end;">
    <a href="https://admin.coudae.kr/#/login" style="background-color:#e2b04a;color:#1a1a2e;border-radius:8px;padding:10px 18px;font-size:13px;font-weight:800;white-space:nowrap;text-decoration:none;display:inline-block;">무료 시작 →</a>
  </div>
</div>"""

    CTA_BLOG = """<div style="background-color:#1a3a6b;border-radius:14px;padding:24px 28px;display:flex;align-items:center;justify-content:space-between;gap:16px;border:1px solid #2d5a9e;margin:24px 0;">
  <div style="width:44px;height:44px;background-color:#e2b04a;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;">🏄</div>
  <div style="flex:1;">
    <div style="font-size:16px;font-weight:800;color:#ffffff;">쿠대 — 구매대행 자동화 프로그램</div>
    <div style="font-size:12px;color:#94a3b8;margin-top:4px;">상품 등록·가격 모니터링·주문 관리 자동화 · 누적회원 300명</div>
  </div>
  <div style="flex-shrink:0;margin-left:auto;">
    <a href="https://admin.coudae.kr/#/login" style="background-color:#e2b04a;color:#1a1a2e;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:800;white-space:nowrap;text-decoration:none;display:inline-block;">무료로 시작하기 →</a>
  </div>
</div>"""

    CAFE_REVIEW_TABLE = """<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-top:24px;">
<tr><td style="background-color:#1a3a6b;padding:28px;border-radius:14px;">
<p style="font-size:16px;font-weight:800;color:#e2b04a;margin:0 0 14px 0;">🏄 쿠대 마스터 총평</p>
<p style="font-size:14px;color:#e2e8f0;line-height:1.9;margin:0;">[총평내용]</p>
</td></tr></table>"""

    BLOG_REVIEW_TABLE = """<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-top:24px;">
<tr><td style="background-color:#1a3a6b;padding:28px;border-radius:14px;">
<p style="font-size:16px;font-weight:800;color:#e2b04a;margin:0 0 14px 0;">🏄 쿠대 마스터 총평</p>
<p style="font-size:14px;color:#e2e8f0;line-height:1.9;margin:0;">[총평내용]</p>
</td></tr></table>"""

    # ── 카페용 ───────────────────────────────────────────
    cafe_prompt = f"""
당신은 구매대행 카페 '쿠대' 운영자 쿠대 마스터입니다.
오늘은 {today}({weekday}요일)입니다.
카페 회원들에게 올릴 친근하고 실전적인 글을 작성하세요.

===== 수집 정보 =====
{news_text}
=====================

## 구성
1. 헤더 배너 (쿠대 마스터 인사이트 #{issue_num} / {today})
2. 이번 호 핵심 요약 박스 (3가지)
3. 🇰🇷 국내 구매대행 트렌드 3개
   - 친근한 말투로 설명 5~6문장
   - 실전 적용 팁 3가지
   - 주의사항 1~2가지
4. 🌏 해외 소싱 추천 아이템 3~4개
   - 아이템 설명 5~6문장
   - 소싱 방법 (구체적 사이트명)
   - 예상 마진율
   - 주의사항
5. 📢 플랫폼·정책 업데이트
6. 🤖 쿠대 활용 TIP - 트렌드 2번째 카드 뒤에 아래 HTML을 그대로 삽입:
{CTA_CAFE}
7. 🏄 쿠대 마스터 총평 - 반드시 아래 table HTML을 그대로 복사하고 [총평내용] 텍스트만 교체할 것. div 사용 절대 금지:
{CAFE_REVIEW_TABLE}
"안녕하세요, 쿠대 마스터입니다." 로 시작하는 이번 주 전체를 아우르는 인사이트 4~5문장, "다음에도 알찬 정보로 찾아오겠습니다 🏄" 로 마무리
8. 하단 SNS 배너 - 아래 HTML을 그대로 삽입:
{CAFE_SNS_BANNER}
9. 푸터

## 디자인 (카페 복붙 최적화 인라인 CSS - 절대 준수)
- backdrop-filter, filter, blur, opacity, 그라데이션 배경 절대 금지
- 외부 폰트 로드 금지
- max-width 720px, margin 0 auto
- font-family 'Apple SD Gothic Neo', 'Malgun Gothic', Arial, sans-serif
- background-color #ffffff

### 헤더
- background-color #1a3a6b, border-radius 16px, padding 40px 36px, text-align center
- 브랜드명: font-size 28px, font-weight 900, color #ffffff
- 부제: font-size 13px, color #94a3b8, margin-top 8px
- 날짜뱃지: background-color #e2b04a, color #1a1a2e, border-radius 20px, padding 6px 20px, font-size 13px, font-weight 700, display inline-block, margin-top 14px

### 핵심요약박스
- background-color #fffbeb, border-left 5px solid #e2b04a, border-radius 8px, padding 20px 24px, margin 16px 0
- 제목: font-size 13px, font-weight 700, color #92400e, margin-bottom 10px
- 항목: font-size 14px, color #1e293b, line-height 1.8

### 섹션제목
- font-size 20px, font-weight 900, color #1e293b
- border-left 5px solid #e2b04a, padding-left 14px, margin 28px 0 14px

### 뉴스카드
- background-color #ffffff, border 1px solid #e2e8f0, border-radius 12px, padding 22px, margin-bottom 14px
- 국내: border-top 4px solid #3b82f6
- 해외: border-top 4px solid #10b981
- 플랫폼: border-top 4px solid #f59e0b
- 카드제목: font-size 16px, font-weight 800, color #0f172a, margin-bottom 10px
- 카드본문: font-size 14px, color #334155, line-height 1.9

### 실전팁박스
- background-color #f0fdf4, border-radius 8px, padding 14px 18px, margin-top 10px
- font-size 13px, color #166534, line-height 1.8

### 마진뱃지
- display inline-block, background-color #dcfce7, color #166534
- border-radius 6px, padding 3px 10px, font-size 12px, font-weight 700, margin-left 8px

### 푸터
- text-align center, padding 20px, font-size 12px, color #94a3b8

이모지 풍부하게. 순수 HTML만 반환. 코드블록·마크다운 없이.
"""

    # ── 블로그용 ─────────────────────────────────────────
    blog_prompt = f"""
당신은 구매대행 전문 블로그 에디터 쿠대 마스터입니다.
오늘은 {today}({weekday}요일)입니다.
네이버 블로그 SEO에 최적화된 전문 콘텐츠를 작성하세요.

===== 수집 정보 =====
{news_text}
=====================

## 구성
1. 헤더 배너 (쿠대 마스터 인사이트 #{issue_num} / {today})
2. 목차 박스 (이 글에서 다루는 내용)
3. 서론 (검색 키워드 포함, 2~3문장)
4. 🇰🇷 국내 구매대행 트렌드 3개
   - SEO 키워드 포함 제목
   - 전문적 설명 7~8문장
   - 데이터·수치 적극 활용
   - 실전 전략 4~5가지
5. 🌏 해외 소싱 추천 아이템 3~4개
   - SEO 키워드 포함 제목
   - 상세 설명 7~8문장
   - 소싱 채널 (구체적 사이트명·검색어)
   - 예상 마진율 + 근거
   - 리스크 관리
6. 📢 플랫폼·정책 업데이트 (상세) - 중간에 아래 HTML 삽입:
{CTA_BLOG}
7. 🏄 쿠대 마스터 총평 - 반드시 아래 table HTML을 그대로 복사하고 [총평내용] 텍스트만 교체할 것. div 사용 절대 금지:
{BLOG_REVIEW_TABLE}
"안녕하세요, 구매대행 전문가 쿠대 마스터입니다." 로 시작하는 전문가 시각 분석 5~6문장과 구체적 실행 제안, "다음 포스팅에서도 실전 인사이트로 찾아오겠습니다." 로 마무리
8. 태그 (SEO 키워드 10개, #구매대행 #해외직구 등)
9. 하단 SNS 배너 - 아래 HTML을 그대로 삽입:
{BLOG_SNS_BANNER}
10. 푸터

## 디자인 (블로그 최적화 인라인 CSS - 절대 준수)
- backdrop-filter, filter, blur, opacity, 그라데이션 배경 절대 금지
- 외부 폰트 로드 금지
- max-width 720px, margin 0 auto
- font-family 'Apple SD Gothic Neo', 'Malgun Gothic', Arial, sans-serif
- background-color #ffffff

### 헤더
- background-color #1a3a6b, border-radius 16px, padding 40px 36px, text-align center
- 브랜드명: font-size 28px, font-weight 900, color #ffffff
- 날짜뱃지: background-color #e2b04a, color #1a1a2e, border-radius 20px, padding 6px 20px, font-size 13px, font-weight 700, display inline-block, margin-top 14px

### 목차박스
- background-color #f8fafc, border 1px solid #e2e8f0, border-radius 10px, padding 20px 24px, margin 16px 0
- 제목: font-size 15px, font-weight 800, color #1e293b, margin-bottom 12px
- 항목: font-size 14px, color #475569, line-height 2.0, padding-left 16px

### 섹션제목
- font-size 22px, font-weight 900, color #0f172a
- border-bottom 3px solid #e2b04a, padding-bottom 10px, margin 32px 0 16px

### 뉴스카드
- background-color #ffffff, border 1px solid #e2e8f0, border-radius 12px, padding 24px, margin-bottom 16px
- 국내: border-left 5px solid #3b82f6
- 해외: border-left 5px solid #10b981
- 플랫폼: border-left 5px solid #f59e0b
- 카드제목: font-size 18px, font-weight 800, color #0f172a, margin-bottom 12px
- 카드본문: font-size 14px, color #334155, line-height 2.0

### 전략박스
- background-color #f0f9ff, border-radius 8px, padding 16px 20px, margin-top 12px
- font-size 13px, color #0369a1, line-height 1.8

### 마진뱃지
- display inline-block, background-color #dcfce7, color #166534
- border-radius 6px, padding 3px 12px, font-size 13px, font-weight 700

### 태그영역
- margin-top 20px, padding 16px
- 태그: display inline-block, background-color #f1f5f9, color #475569, border-radius 20px, padding 4px 12px, font-size 12px, margin 4px

### 푸터
- text-align center, padding 20px, font-size 12px, color #94a3b8

이모지 풍부하게. 순수 HTML만 반환. 코드블록·마크다운 없이.
"""

    print("  ✍️  카페용 작성 중...")
    cafe_resp = client.messages.create(
        model="claude-sonnet-4-5", max_tokens=16000,
        messages=[{"role": "user", "content": cafe_prompt}]
    )
    print("  ✍️  블로그용 작성 중...")
    blog_resp = client.messages.create(
        model="claude-sonnet-4-5", max_tokens=16000,
        messages=[{"role": "user", "content": blog_prompt}]
    )
    return cafe_resp.content[0].text, blog_resp.content[0].text


# ─── 4. 팩트 검증 및 자동 수정 ───────────────────────────
def verify_and_fix(html: str, label: str) -> str:
    print(f"  🔍 {label} 팩트 검증 중...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    extract_resp = client.messages.create(
        model="claude-sonnet-4-5", max_tokens=800,
        messages=[{"role": "user", "content": f"""
아래 HTML에서 검증이 필요한 수치/통계/정책 정보를 추출하세요.
형식: "항목명 | 수치내용" 한 줄씩. 없으면 "없음" 반환.
HTML: {html[:3000]}
"""}]
    )
    claims = extract_resp.content[0].text.strip()
    if claims == "없음" or not claims:
        print(f"  ✅ {label} 검증할 수치 없음")
        return html

    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        verify_resp = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"다음 구매대행 뉴스 수치/정책 정보가 정확한지 검증하세요.\n검증항목:\n{claims}\n형식: '항목명 | 원래수치 | 수정수치 | 판정(정확/수정필요)'",
            config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
        )
        verification = verify_resp.text or ""
    except Exception as e:
        print(f"  ⚠️  팩트 검증 실패: {e}")
        return html

    if not verification or "수정필요" not in verification:
        print(f"  ✅ {label} 팩트 검증 통과")
        return html

    fix_resp = client.messages.create(
        model="claude-sonnet-4-5", max_tokens=16000,
        messages=[{"role": "user", "content": f"""
아래 HTML에서 팩트 검증 결과 "수정필요" 항목만 올바른 수치로 수정하세요.
HTML 구조·디자인 절대 변경 금지. 수치 텍스트만 수정.
팩트 검증 결과:\n{verification}
원본 HTML:\n{html}
수정된 HTML만 반환. 코드블록 없이.
"""}]
    )
    print(f"  ✅ {label} 팩트 수정 완료")
    return fix_resp.content[0].text.strip()


# ─── 5. 이력 키워드 추출 ──────────────────────────────────
def extract_history_items(news_text: str) -> tuple:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model="claude-sonnet-4-5", max_tokens=500,
        messages=[{"role": "user", "content": f"""
아래 구매대행 뉴스에서 핵심 항목과 토픽을 추출하세요.
[아이템] 상품명/트렌드명 목록 (최대 10개, 쉼표 구분)
[토픽] 주요 키워드 (최대 10개, 쉼표 구분)
뉴스: {news_text[:2000]}
"""}]
    )
    text = resp.content[0].text
    items, topics = [], []
    for line in text.split("\n"):
        line = line.strip()
        if "[아이템]" in line:
            items  = [x.strip() for x in line.replace("[아이템]", "").split(",") if x.strip()]
        elif "[토픽]" in line:
            topics = [x.strip() for x in line.replace("[토픽]", "").split(",") if x.strip()]
    return items, topics


# ─── 6. 메일 발송 ─────────────────────────────────────────
def send_email(html: str, subject: str) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText("쿠대 마스터 인사이트", "plain", "utf-8"))
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


# ─── 7. HTML 저장 ─────────────────────────────────────────
def save_preview(html: str, prefix: str):
    fname = f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  📄 저장: {fname}")


# ─── 메인 ─────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("🏄 쿠대 마스터 인사이트 시작")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    print("\n📂 발행 이력 로드 중...")
    history = load_history()
    print(f"   이전 항목 {len(history.get('items',[]))}개 / 토픽 {len(history.get('topics',[]))}개")

    print("\n📡 Gemini 뉴스 수집 중...")
    news_text = collect_news()
    print("   수집 완료")

    print("\n🔄 중복 제거 중...")
    news_text = remove_duplicates(news_text, history)

    new_items, new_topics = extract_history_items(news_text)

    print("\n✍️  Claude 콘텐츠 작성 중...")
    cafe_html, blog_html = generate_content(news_text)
    print("   작성 완료")

    print("\n🔍 팩트 검증 중...")
    cafe_html = verify_and_fix(cafe_html, "카페용")
    blog_html = verify_and_fix(blog_html, "블로그용")

    save_preview(cafe_html, "insight_cafe")
    save_preview(blog_html, "insight_blog")

    today   = datetime.now().strftime("%Y년 %m월 %d일")
    weekday = ["월", "화", "수", "목", "금", "토", "일"][datetime.now().weekday()]

    print("\n📧 메일 발송 중...")
    send_email(cafe_html, f"☕ [카페용] 쿠대 마스터 인사이트 | {today}({weekday})")
    send_email(blog_html, f"📝 [블로그용] 쿠대 마스터 인사이트 | {today}({weekday})")

    print("\n💾 발행 이력 저장 중...")
    save_history(history, new_items, new_topics)

    print("\n✅ 완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
