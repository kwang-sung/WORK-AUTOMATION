#!/usr/bin/env python3
"""
쿠대 마스터 인사이트 - 구매대행 뉴스레터
매주 월요일·목요일 09:30 자동 실행

메일 1통 발송 (카페용):
- 친근한 톤 + 쿠대 마스터 총평

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

# 월요일 — 시장 조망 / 소싱 발굴
SEARCH_QUERIES_MON = [
    # (레이어,             검색 쿼리)
    # 전술: 뭘 팔까
    ("전술|소싱아이템",    "지금 잘 팔리는 트렌드 소싱 아이템 구매대행 추천 2026"),
    ("전술|소싱아이템",    "국내 미출시 해외 인기 상품 아이템 소싱 기회 2026"),
    ("전술|소싱아이템",    "일본 해외 소싱 추천 아이템 트렌드 2026"),
    # 전술: 어디서 팔까 / 마진이 남나
    ("전술|플랫폼마진",    "쿠팡 네이버 스마트스토어 수수료 정책 노출 알고리즘 변경 2026"),
    # 전략: 방향 잡기
    ("전략|플랫폼방향",    "이커머스 플랫폼 경쟁 전략 쿠팡 네이버 11번가 알리 쉬인 2026"),
    ("전략|소싱환경",      "글로벌 소싱 환경 변화 미국 일본 중국 직구 역직구 2026"),
    ("전략|소비트렌드",    "소비자 트렌드 변화 1인가구 시니어 반려동물 이커머스 2026"),
    # 리스크: 변화 있을 때만
    ("리스크|규정변경",    "관세 통관 직구 규정 변경 이커머스 셀러 2026"),
]

# 목요일 — 실전 운영 / 수익 최적화
SEARCH_QUERIES_THU = [
    # 운영: 어떻게 팔까
    ("운영|상품최적화",    "쿠팡 스마트스토어 상세페이지 상품등록 키워드 최적화 노출 팁 2026"),
    ("운영|가격전략",      "구매대행 이커머스 가격 전략 마진 수수료 경쟁력 설정 2026"),
    ("운영|플랫폼알고리즘","쿠팡 네이버 스마트스토어 알고리즘 변화 셀러 노출 순위 2026"),
    # 수익: 마진 극대화
    ("수익|마진최적화",    "구매대행 마진 극대화 원가 절감 환율 소싱비용 전략 2026"),
    ("수익|묶음전략",      "이커머스 묶음판매 세트상품 객단가 높이기 구매대행 전략 2026"),
    # 선점: 다음 시즌 준비
    ("선점|시즌이벤트",    "2026년 8월 9월 시즌 이벤트 이커머스 선점 아이템 소싱 추천"),
    # 운영 효율화
    ("운영|CS효율화",      "구매대행 셀러 CS 반품 교환 클레임 대응 운영 효율화 2026"),
]

CAFE_SNS_BANNER = """<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-top:24px;border-top:2px solid #e2e8f0;">
<tr><td style="padding:16px 0 8px 0;"><p style="font-size:14px;font-weight:800;color:#1e293b;margin:0;">ALL8. 쿠대 공식채널</p></td></tr>
<tr><td style="padding:6px 0;border-bottom:1px solid #f1f5f9;">📩 ALL8 대량/반자동 무료체험 &nbsp;<a href="https://all8.io/" style="color:#e2b04a;font-weight:700;text-decoration:none;">바로가기 →</a></td></tr>
<tr><td style="padding:6px 0;border-bottom:1px solid #f1f5f9;">🔗 쿠대 반자동 무료체험 &nbsp;<a href="https://www.coudae.io/" style="color:#e2b04a;font-weight:700;text-decoration:none;">바로가기 →</a></td></tr>
<tr><td style="padding:6px 0;border-bottom:1px solid #f1f5f9;line-height:1.8;">🎁 단체방 입장하면 무료로 드려요!<br>🧮 마진 계산기 + 🌐 글로벌 소싱 레이다 v5<br>👉 &nbsp;<a href="https://open.kakao.com/o/gKWnrBDg" style="color:#e2b04a;font-weight:700;text-decoration:none;">단톡 무료교육 듣기 →</a></td></tr>
<tr><td style="padding:6px 0;border-bottom:1px solid #f1f5f9;">📍 스레드 &nbsp;<a href="https://www.threads.com/@goldensurfer_kr" style="color:#e2b04a;font-weight:700;text-decoration:none;">바로가기 →</a></td></tr>
<tr><td style="padding:6px 0;border-bottom:1px solid #f1f5f9;">📸 인스타 &nbsp;<a href="https://www.instagram.com/goldensurfer_kr/" style="color:#e2b04a;font-weight:700;text-decoration:none;">바로가기 →</a></td></tr>
<tr><td style="padding:6px 0;">📝 블로그 &nbsp;<a href="https://blog.naver.com/gngsun" style="color:#e2b04a;font-weight:700;text-decoration:none;">바로가기 →</a></td></tr>
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
    history["items"]  = (history.get("items",  []) + new_items)[-40:]
    history["topics"] = (history.get("topics", []) + new_topics)[-40:]
    history["last_sent"] = datetime.now().strftime('%Y-%m-%d')
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    content = base64.b64encode(json.dumps(history, ensure_ascii=False, indent=2).encode()).decode()
    for attempt in range(3):
        try:
            sha = None
            resp = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{HISTORY_FILE}", headers=headers)
            if resp.status_code == 200:
                sha = resp.json().get("sha")
            payload = {"message": f"인사이트 이력 업데이트 {datetime.now().strftime('%Y%m%d')}", "content": content}
            if sha:
                payload["sha"] = sha
            put_resp = requests.put(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{HISTORY_FILE}", headers=headers, json=payload)
            if put_resp.status_code in (200, 201):
                print("  ✅ 발행 이력 저장 완료")
                return
            elif put_resp.status_code == 409:
                print(f"  ⚠️  SHA 충돌, 재시도 중 ({attempt+1}/3)...")
                time.sleep(3)
            else:
                print(f"  ⚠️  이력 저장 실패 ({put_resp.status_code}): {put_resp.text[:200]}")
                return
        except Exception as e:
            print(f"  ⚠️  이력 저장 오류 ({attempt+1}/3): {e}")
            time.sleep(3)
    print("  ❌ 이력 저장 3회 모두 실패 — last_sent 미기록")


# ─── 1. Gemini 서치 ───────────────────────────────────────
def collect_news(queries: list) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    collected = []
    for layer, query in queries:
        try:
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"다음 주제로 이번 주 최신 정보 5개를 찾아서 '제목 | 핵심내용 3문장' 형식으로 한국어 답변: {query}",
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            collected.append(f"[{layer}]\n{resp.text}")
            print(f"    ✅ [{layer}] {query[:40]}...")
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
        model="claude-sonnet-5", max_tokens=8000,
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
def generate_content(news_text: str, is_thursday: bool = False) -> tuple:
    client    = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today     = datetime.now().strftime("%Y년 %m월 %d일")
    weekday   = ["월", "화", "수", "목", "금", "토", "일"][datetime.now().weekday()]
    issue_num = datetime.now().strftime("%Y%m%d")

    CTA_CAFE = """<div style="background-color:#fffbeb;border:1px solid #fcd34d;border-left:4px solid #e2b04a;border-radius:0 12px 12px 0;padding:18px 22px;display:flex;align-items:center;justify-content:space-between;gap:16px;margin:24px 0 8px 0;">
  <div style="flex:1;">
    <div style="display:inline-block;background-color:#e2b04a;color:#1a1a2e;border-radius:4px;padding:2px 8px;font-size:10px;font-weight:800;margin-bottom:6px;">FREE</div>
    <div style="font-size:15px;font-weight:800;color:#1e293b;">쿠대 프로그램 — 지금 무료로 시작하세요</div>
    <div style="font-size:12px;color:#64748b;margin-top:3px;">구매대행 자동화의 시작 · 누적회원 15,900명</div>
  </div>
  <div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end;">
    <a href="https://www.coudae.io/" style="background-color:#e2b04a;color:#1a1a2e;border-radius:8px;padding:10px 18px;font-size:13px;font-weight:800;white-space:nowrap;text-decoration:none;display:inline-block;">무료 시작 →</a>
  </div>
</div>
<div style="background-color:#ffffff;border:1px solid #16a34a;border-left:5px solid #16a34a;border-radius:0 12px 12px 0;padding:18px 22px;display:flex;align-items:center;justify-content:space-between;gap:16px;margin:0 0 24px 0;">
  <div style="flex:1;">
    <div style="display:inline-block;background-color:#16a34a;color:#ffffff;border-radius:4px;padding:2px 8px;font-size:10px;font-weight:800;margin-bottom:6px;">FREE</div>
    <div style="font-size:15px;font-weight:800;color:#0f172a;">ALL8 — 구매대행 통합 솔루션 무료체험</div>
    <div style="font-size:12px;color:#166534;margin-top:3px;">소싱·판매·정산 한 번에 관리</div>
  </div>
  <div style="flex-shrink:0;">
    <a href="https://all8.io/" style="background-color:#16a34a;color:#ffffff;border-radius:8px;padding:10px 18px;font-size:13px;font-weight:800;white-space:nowrap;text-decoration:none;display:inline-block;">무료체험 →</a>
  </div>
</div>"""

    CAFE_REVIEW_TABLE = """<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-top:24px;">
<tr><td style="background-color:#1a3a6b;padding:28px;border-radius:14px;">
<p style="font-size:16px;font-weight:800;color:#e2b04a;margin:0 0 14px 0;">🏄 쿠대 마스터 총평</p>
<p style="font-size:14px;color:#e2e8f0;line-height:1.9;margin:0;">[총평내용]</p>
</td></tr></table>"""

    # ── 카페용 ───────────────────────────────────────────
    cafe_prompt = f"""
당신은 구매대행 카페 '쿠대' 운영자 쿠대 마스터입니다.
오늘은 {today}({weekday}요일)입니다.
재고 없이 국내위탁·해외위탁으로 판매하는 셀러들에게 실전 도움이 되는 글을 작성하세요.

수집 정보의 각 섹션은 레이어로 분류되어 있습니다:
- [전술|소싱아이템]: 지금 당장 뭘 팔까
- [전술|플랫폼마진]: 어디서 팔까 / 마진이 남나
- [전략|*]: 다음 달·분기 방향 잡기
- [리스크|규정변경]: 놓치면 손해 보는 규정 변화

===== 수집 정보 =====
{news_text}
=====================

## 구성
1. 헤더 배너 (쿠대 마스터 인사이트 #{issue_num} / {today})
2. 이번 호 핵심 요약 박스 (3가지 — 전술·전략·리스크 각 1개씩)
3. 📌 이번 주 소싱 기회 — "뭘 팔까?" [전술|소싱아이템]
   - 트렌딩 아이템 3~4개
   - 아이템별: 왜 지금 팔리는지 3~4문장, 소싱처 (구체적 사이트명), 예상 마진율, 주의사항
   - 실전 소싱 팁 박스
4. 🛒 플랫폼 & 마진 체크 — "어디서 팔까? 마진이 남나?" [전술|플랫폼마진]
   - 플랫폼 정책·수수료·노출 변화 핵심만
   - 셀러 입장 실전 적용법 3가지
5. 쿠대 활용 TIP - 아래 HTML을 그대로 삽입:
{CTA_CAFE}
6. 🔭 전략 시그널 — "다음 달·분기를 준비한다" [전략|*]
   - 플랫폼 세력 변화: 어디에 힘을 실어야 하는가
   - 글로벌 소싱 환경: 미국·일본·중국 소싱 유불리 변화
   - 소비자 구조 변화: 어떤 카테고리가 커지는가
   - 각 항목별 셀러 액션 포인트 1줄씩
7. ⚠️ 리스크 알림 [리스크|규정변경]
   - 이번 주 관세·통관·규정 변화가 있으면: 핵심 내용 + 셀러 주의사항
   - 이번 주 주요 변경 없으면: "이번 주 규정 변경 없음 ✅" 한 줄로 표시
8. 🏄 쿠대 마스터 총평 - 반드시 아래 table HTML을 그대로 복사하고 [총평내용] 텍스트만 교체할 것. div 사용 절대 금지:
{CAFE_REVIEW_TABLE}
"안녕하세요, 쿠대 마스터입니다." 로 시작 — 전술(당장 팔 것)과 전략(방향) 두 가지를 연결하는 인사이트 4~5문장, "다음에도 알찬 정보로 찾아오겠습니다 🏄" 로 마무리
9. 하단 SNS 배너 - 아래 HTML을 그대로 삽입:
{CAFE_SNS_BANNER}
10. 푸터

## 디자인 (카페 복붙 최적화 인라인 CSS - 절대 준수)
- backdrop-filter, filter, blur, opacity, 그라데이션 배경 절대 금지
- 외부 폰트 로드 금지
- 배경색 있는 모든 요소(헤더·요약박스·카드·팁박스 등) div 금지 → <table width="100%" style="border-collapse:collapse"><tr><td style="background-color:...;padding:...;border-radius:..."> 구조 필수 (div background-color는 네이버에서 텍스트 형광색으로 변환됨)
- display:flex / display:grid 절대 금지 → 네이버에서 레이아웃 붕괴. table 또는 inline-block 사용
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
- 소싱아이템: border-top 4px solid #10b981
- 플랫폼마진: border-top 4px solid #f59e0b
- 전략: border-top 4px solid #3b82f6
- 리스크: border-top 4px solid #ef4444
- 카드제목: font-size 16px, font-weight 800, color #0f172a, margin-bottom 10px
- 카드본문: font-size 14px, color #334155, line-height 1.9

### 실전팁박스
- background-color #f0fdf4, border-radius 8px, padding 14px 18px, margin-top 10px
- font-size 13px, color #166534, line-height 1.8

### 액션포인트박스 (전략 섹션용)
- background-color #eff6ff, border-radius 8px, padding 14px 18px, margin-top 10px
- font-size 13px, color #1e40af, line-height 1.8

### 마진뱃지
- display inline-block, background-color #dcfce7, color #166534
- border-radius 6px, padding 3px 10px, font-size 12px, font-weight 700, margin-left 8px

### 푸터
- text-align center, padding 20px, font-size 12px, color #94a3b8

이모지 풍부하게. 순수 HTML만 반환. 코드블록·마크다운 없이.
"""

    # ── 목요일 실전 운영 프롬프트 ────────────────────────────
    thu_cafe_prompt = f"""
당신은 구매대행 카페 '쿠대' 운영자 쿠대 마스터입니다.
오늘은 {today}({weekday}요일)입니다. 목요일 — 주간 운영 점검일.
이번 주 월요일에 소싱 아이템을 발굴한 셀러들이 "어떻게 팔까"를 고민하는 시점입니다.
실전 운영에 바로 적용 가능한 정보를 제공하세요.

수집 정보의 각 섹션은 레이어로 분류되어 있습니다:
- [운영|상품최적화]: 상세페이지·키워드 최적화로 노출 높이기
- [운영|가격전략]: 가격 전략·수수료 관리·경쟁력 유지
- [운영|플랫폼알고리즘]: 쿠팡/스마트스토어 알고리즘 변화·대응
- [수익|마진최적화]: 마진 극대화·원가 절감·환율 활용
- [수익|묶음전략]: 묶음·세트 구성으로 객단가 높이기
- [선점|시즌이벤트]: 2~3주 후 시즌·이벤트 선점 아이템
- [운영|CS효율화]: CS·반품·클레임 대응 효율화

===== 수집 정보 =====
{news_text}
=====================

## 구성 (목요일 실전 운영 에디션)
1. 헤더 배너 (목요일 실전 운영 에디션 #{issue_num} / {today})
2. 이번 주 핵심 운영 포인트 요약 박스 (3가지 — 운영·마진·선점 각 1개씩)
3. ⚙️ 이번 주 운영 핵심 팁 3가지 [운영|상품최적화, 운영|가격전략, 운영|CS효율화]
   - 팁 1. 상세페이지 & 키워드 최적화 → 노출 높이는 실전 방법
   - 팁 2. 가격 경쟁력 & 마진 유지 전략
   - 팁 3. CS·반품 효율화로 운영 시간 줄이기
   - 각 팁: 배경 2~3문장 + 실전 액션 2가지
4. 💰 마진 극대화 전략 [수익|마진최적화, 수익|묶음전략]
   - 수수료 절감 포인트 (플랫폼별 수수료 비교)
   - 묶음·세트 구성으로 객단가 올리기 (사례 포함)
   - 환율 타이밍 활용법 (이번 주 환율 동향)
5. 쿠대 활용 TIP - 아래 HTML을 그대로 삽입:
{CTA_CAFE}
6. 📦 플랫폼 노출 올리기 [운영|플랫폼알고리즘]
   - 이번 주 쿠팡/스마트스토어 알고리즘 변화 핵심
   - 노출 순위 올리는 실전 액션 3가지 (지금 당장 할 수 있는 것)
7. 📅 2주 후 선점 아이템 [선점|시즌이벤트]
   - 2~3주 후 다가오는 시즌·이벤트 2~3가지
   - 각 시즌별: 어떤 아이템 / 지금 준비해야 하는 이유 / 소싱 타이밍
8. 🏄 쿠대 마스터 총평 - 반드시 아래 table HTML을 그대로 복사하고 [총평내용] 텍스트만 교체할 것. div 사용 절대 금지:
{CAFE_REVIEW_TABLE}
"안녕하세요, 쿠대 마스터입니다." 로 시작 — 이번 주 운영 핵심을 한 줄로 압축, 지금 당장 할 수 있는 행동 1가지 제안, "다음 월요일 소싱 인사이트로 찾아오겠습니다 🏄" 로 마무리
9. 하단 SNS 배너 - 아래 HTML을 그대로 삽입:
{CAFE_SNS_BANNER}
10. 푸터

## 디자인 (카페 복붙 최적화 인라인 CSS - 절대 준수)
- backdrop-filter, filter, blur, opacity, 그라데이션 배경 절대 금지
- 외부 폰트 로드 금지
- 배경색 있는 모든 요소(헤더·요약박스·카드·팁박스 등) div 금지 → <table width="100%" style="border-collapse:collapse"><tr><td style="background-color:...;padding:...;border-radius:..."> 구조 필수 (div background-color는 네이버에서 텍스트 형광색으로 변환됨)
- display:flex / display:grid 절대 금지 → 네이버에서 레이아웃 붕괴. table 또는 inline-block 사용
- max-width 720px, margin 0 auto
- font-family 'Apple SD Gothic Neo', 'Malgun Gothic', Arial, sans-serif
- background-color #ffffff

### 헤더 (목요일 고유 배색)
- background-color #0f172a, border-radius 16px, padding 40px 36px, text-align center
- 브랜드명: font-size 28px, font-weight 900, color #ffffff
- 부제: font-size 13px, color #94a3b8, margin-top 8px
- 날짜뱃지: background-color #10b981, color #ffffff, border-radius 20px, padding 6px 20px, font-size 13px, font-weight 700, display inline-block, margin-top 14px

### 핵심요약박스
- background-color #f0fdf4, border-left 5px solid #10b981, border-radius 8px, padding 20px 24px, margin 16px 0
- 제목: font-size 13px, font-weight 700, color #166534, margin-bottom 10px
- 항목: font-size 14px, color #1e293b, line-height 1.8

### 섹션제목
- font-size 20px, font-weight 900, color #1e293b
- border-left 5px solid #10b981, padding-left 14px, margin 28px 0 14px

### 뉴스카드
- background-color #ffffff, border 1px solid #e2e8f0, border-radius 12px, padding 22px, margin-bottom 14px
- 운영팁: border-top 4px solid #10b981
- 마진: border-top 4px solid #f59e0b
- 선점: border-top 4px solid #6366f1
- 카드제목: font-size 16px, font-weight 800, color #0f172a, margin-bottom 10px
- 카드본문: font-size 14px, color #334155, line-height 1.9

### 실전액션박스
- background-color #f0fdf4, border-radius 8px, padding 14px 18px, margin-top 10px
- font-size 13px, color #166534, line-height 1.8

### 마진박스
- background-color #fffbeb, border-radius 8px, padding 14px 18px, margin-top 10px
- font-size 13px, color #92400e, line-height 1.8

### 선점박스
- background-color #eef2ff, border-radius 8px, padding 14px 18px, margin-top 10px
- font-size 13px, color #3730a3, line-height 1.8

### 푸터
- text-align center, padding 20px, font-size 12px, color #94a3b8

이모지 풍부하게. 순수 HTML만 반환. 코드블록·마크다운 없이.
"""

    active_cafe_prompt = thu_cafe_prompt if is_thursday else cafe_prompt
    edition_label = "목요일 실전 운영" if is_thursday else "월요일 소싱"

    print(f"  ✍️  [{edition_label}] 카페용 작성 중...")
    with client.messages.stream(
        model="claude-sonnet-5", max_tokens=32000,
        messages=[{"role": "user", "content": active_cafe_prompt}]
    ) as stream:
        cafe_html = stream.get_final_text()
    return cafe_html


# ─── 4. 팩트 검증 및 자동 수정 ───────────────────────────
def verify_and_fix(html: str, label: str) -> str:
    print(f"  🔍 {label} 팩트 검증 중...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    extract_resp = client.messages.create(
        model="claude-sonnet-5", max_tokens=800,
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

    with client.messages.stream(
        model="claude-sonnet-5", max_tokens=32000,
        messages=[{"role": "user", "content": f"""
아래 HTML에서 팩트 검증 결과 "수정필요" 항목만 올바른 수치로 수정하세요.
HTML 구조·디자인 절대 변경 금지. 수치 텍스트만 수정.
팩트 검증 결과:\n{verification}
원본 HTML:\n{html}
수정된 HTML만 반환. 코드블록 없이.
"""}]
    ) as stream:
        fix_resp_text = stream.get_final_text()
    print(f"  ✅ {label} 팩트 수정 완료")
    return fix_resp_text.strip()


# ─── 5. 이력 키워드 추출 ──────────────────────────────────
def extract_history_items(news_text: str) -> tuple:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model="claude-sonnet-5", max_tokens=500,
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

    today_key = datetime.now().strftime('%Y-%m-%d')
    if history.get("last_sent") == today_key:
        print(f"\n⚠️  오늘({today_key}) 이미 발행 완료 — 중복 실행 차단")
        print("=" * 55)
        return

    weekday_num  = datetime.now().weekday()  # 0=월 3=목
    is_thursday  = weekday_num == 3
    active_queries = SEARCH_QUERIES_THU if is_thursday else SEARCH_QUERIES_MON
    edition_label  = "목요일 실전 운영 에디션" if is_thursday else "월요일 소싱 조망 에디션"
    print(f"\n📅 오늘 에디션: {edition_label}")

    print("\n📡 Gemini 뉴스 수집 중...")
    news_text = collect_news(active_queries)
    print("   수집 완료")

    if not news_text.strip():
        print("\n🚨 Gemini 검색 전체 실패 — 크레딧 소진 또는 API 오류")
        print("   발행을 중단합니다. Gemini 크레딧을 충전해주세요.")
        print("=" * 55)
        raise SystemExit(1)

    print("\n🔄 중복 제거 중...")
    news_text = remove_duplicates(news_text, history)

    new_items, new_topics = extract_history_items(news_text)

    print("\n✍️  Claude 콘텐츠 작성 중...")
    cafe_html = generate_content(news_text, is_thursday)
    print("   작성 완료")

    print("\n🔍 팩트 검증 중...")
    cafe_html = verify_and_fix(cafe_html, "카페용")

    save_preview(cafe_html, "insight_cafe")

    today   = datetime.now().strftime("%Y년 %m월 %d일")
    weekday = ["월", "화", "수", "목", "금", "토", "일"][datetime.now().weekday()]
    tag     = "실전 운영" if is_thursday else "소싱 조망"

    print("\n📧 메일 발송 중...")
    send_email(cafe_html, f"☕ [카페용] 쿠대 마스터 인사이트 | {today}({weekday}) — {tag}")

    print("\n💾 발행 이력 저장 중...")
    save_history(history, new_items, new_topics)

    print("\n✅ 완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
