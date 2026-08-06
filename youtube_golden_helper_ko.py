#!/usr/bin/env python3
"""
골든헬퍼 - 통합 콘텐츠 자동 생성
매주 월·목 오후 3시 실행

섹션 1: 시니어 아이템 대본 (롱폼 18씬 + 쇼츠 + 메타데이터)
섹션 2: 시니어 복지 정보 (조사 보고서 + 10씬 대본 2,000자)
→ 이메일 1통으로 발송
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

# ── 아이템 카테고리 12개 ──────────────────────────────────
CATEGORIES = [
    "손·팔 재활 운동기구 (손가락 운동기, 재활 장갑)",
    "화장실·욕실 케어용품 (이동식 좌변기, 안전손잡이, 미끄럼방지)",
    "발 건강용품 (지압 슬리퍼, 실내화, 부종 완화 양말)",
    "거동 보조기구 (보행차, 지팡이, 실버카 액세서리)",
    "침실·수면 보조 (경사 베개, 욕창 방지 방석, 기립 보조)",
    "관절 보호대 (무릎, 허리, 손목)",
    "온열·찜질 기구",
    "주방·식사 보조도구 (그립 수저, 미끄럼방지 식기)",
    "낙상 방지용품 (문턱 경사로, 야간 센서등)",
    "청력·시력 보조 (돋보기, 확대경, 큰 글씨 제품)",
    "실내 운동기구 (앉아서 하는 페달, 밴드)",
    "위생·간병 소모품",
]

# ── 복지 정보 — 월요일: 정부 보조금·혜택 16개 ───────────
TOPICS_MON = [
    "노인장기요양보험 등급 신청 방법과 혜택 총정리",
    "기초연금 수급 조건과 신청 방법 (2026년 최신)",
    "65세 틀니·임플란트 건강보험 급여 적용 받는 방법",
    "보청기 국가 지원 134만원 받는 방법",
    "치매 치료 관리비 지원 신청법",
    "복지용구 급여 — 휠체어·전동침대 무료로 받는 방법",
    "에너지 바우처 (난방비 지원) 신청 방법",
    "통신요금 감면 — 매달 1만원 이상 아끼는 방법",
    "노인 건강검진 무료 항목 총정리",
    "치매안심센터 무료 서비스 이용법",
    "노인일자리사업 신청 방법 (월 30~60만원)",
    "독거노인 응급안전알림 서비스 신청법",
    "주거급여 — 집 수리비 국가에서 받는 방법",
    "장기요양 재가서비스 종류 (방문요양·방문목욕·방문간호 차이)",
    "긴급복지지원제도 — 갑자기 어려워졌을 때 받는 지원",
    "노인 의료비 본인부담상한제 활용법",
]

# ── 복지 정보 — 목요일: 시니어 생활정보·선택 가이드 16개 ──
TOPICS_THU = [
    "휠체어 올바르게 고르는 방법 — 수동·전동·경량 비교",
    "보청기 브랜드 비교 — 100만원 vs 300만원 실제 차이",
    "낙상 예방 — 집안 위험 동선 점검법",
    "노인 건강기능식품 사기 구별하는 방법",
    "고혈압 약 먹을 때 절대 먹으면 안 되는 음식",
    "시니어 스마트폰 큰 글씨·편의 설정 방법",
    "키오스크 무서워하지 않는 방법",
    "의료비 영수증 항목 읽는 법 — 과잉청구 확인",
    "시니어에게 꼭 필요한 영양소 vs 돈 낭비 영양제",
    "보행차 vs 지팡이 — 어떤 상황에 무엇을 써야 하나",
    "노인 수면 — 수면제 대신 할 수 있는 것들",
    "관절에 좋은 집에서 하는 운동 5가지",
    "시니어 병원 선택법 — 동네 병원 vs 대학병원",
    "약 여러 개 먹을 때 위험한 조합 주의사항",
    "노인 우울증 자가 체크와 도움받는 방법",
    "치매 초기 증상 구별법 — 건망증과의 차이",
]

ITEM_BANNED = """
[절대 금지]
- 의학적 효능/치료/완화/예방 주장 ("혈액순환 개선", "통증 완화" 등)
- 직접 사용 후기 표현 ("써보니", "한 달 사용해보니")
- 의료기기 해당 가능 품목의 효과 단정
"""

ITEM_FRAMING = """
[화자 포지션]
- 화자는 해외 소싱을 업으로 하는 사람
- 판단 근거는 유통/가격/데이터
- "제가 소싱하면서 본 바로는" 류 표현 필수
- 안 써봤다는 사실을 숨기지 않는다
"""


# ─── 1. 아이템 Gemini 조사 ───────────────────────────────
def search_item_with_gemini(category: str) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                f"시니어용 '{category}' 카테고리의 대표 상품을 쿠팡 기준으로 조사해줘.\n\n"
                f"1. 쿠팡 판매 중인 대표 상품 5개 (상품명, 판매가, 리뷰 수, 평점)\n"
                f"2. 카테고리 내 국내 최저가와 최고가\n"
                f"3. 알리익스프레스/타오바오/아마존 유사 스펙 가격대\n"
                f"4. 최근 검색량·수요 추이\n"
                f"5. 소비자 불만·반품 사유\n"
                f"6. 의료기기 분류 가능성\n\n"
                f"가격은 확인된 수치만. 추정이면 추정이라고 표시할 것."
            ),
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        return resp.text
    except Exception as e:
        print(f"  ⚠️  아이템 Gemini 서치 실패: {e}")
        return ""


# ─── 2. 복지 정보 Gemini 조사 ────────────────────────────
def search_welfare_with_gemini(topic: str, is_monday: bool) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    if is_monday:
        contents = (
            f"'{topic}' 주제로 시니어를 위한 정부 복지 혜택 정보를 2026년 최신 기준으로 조사해줘.\n\n"
            f"1. 정책명 및 운영 주체 (부처·기관명)\n"
            f"2. 지원 금액 또는 혜택 내용 (구체적 수치)\n"
            f"3. 신청 자격 (나이·소득·조건)\n"
            f"4. 신청 방법 (신청처·필요 서류·절차 단계별)\n"
            f"5. 신청 기간 또는 상시 신청 여부\n"
            f"6. 자주 하는 실수 또는 주의사항\n"
            f"7. 2025~2026년 변경된 내용 (있으면 명시)\n\n"
            f"수치는 확인된 것만. 추정이면 (추정)으로 표시."
        )
    else:
        contents = (
            f"'{topic}' 주제로 시니어를 위한 실용적인 생활 정보를 조사해줘.\n\n"
            f"1. 핵심 내용 요약\n"
            f"2. 시니어가 알아야 할 구체적 수치나 기준\n"
            f"3. 올바른 선택 또는 행동 방법 (단계별)\n"
            f"4. 흔한 실수 또는 잘못된 상식\n"
            f"5. 비용 또는 지원 여부 (있을 경우)\n"
            f"6. 전문가 권고사항 (출처·기관명 포함)\n\n"
            f"수치는 확인된 것만. 추정이면 (추정)으로 표시."
        )
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        return resp.text
    except Exception as e:
        print(f"  ⚠️  복지 Gemini 서치 실패: {e}")
        return ""


# ─── 3. 아이템 대본 생성 (롱폼 18씬 + 쇼츠 + 메타) ───────
def generate_item_script(category: str, research: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def call(prompt: str, tokens: int = 1000) -> str:
        resp = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text.strip()

    base = f"""카테고리: {category}
화자 포지션: {ITEM_FRAMING}
금지 사항: {ITEM_BANNED}
조사자료: {research[:2000]}"""

    rules = """규칙:
- 제목, 소제목, 해시태그, 마크다운(#, ##, **) 절대 금지
- 순수 더빙 텍스트만
- 각 씬 정확히 200자 내외
- 씬과 씬 사이 빈 줄 하나만
더빙 텍스트만 출력."""

    style = "톤: 60대 이상과 그 자녀가 함께 들어도 이해되는 쉬운 말. 경어체. 담담하게."

    print("    → 후킹 씬...")
    hooking  = call(f"{base}\n{style}\n[후킹 씬 - 1개]\n{rules}\n가격 격차를 숫자로. 인트로 없이 바로.")
    print("    → 공감 씬...")
    empathy  = call(f"{base}\n{style}\n[공감 씬 - 4개]\n{rules}\n부모님 물건 구매에서 겪는 고민과 어려움.", 2000)
    print("    → 정보 씬...")
    info     = call(f"{base}\n{style}\n[정보 씬 - 9개]\n{rules}\n가격대별로 실제 뭐가 다른지. 구체적 숫자. 소싱처 명시.", 4500)
    print("    → 판단 씬...")
    judgment = call(f"{base}\n{style}\n[판단·추천 씬 - 3개]\n{rules}\n어느 가격대를 사야 하는지 근거와 함께.", 1500)
    print("    → 아웃트로 씬...")
    outro    = call(f"{base}\n{style}\n[아웃트로 씬 - 1개]\n{rules}\n다음 영상 예고 + 구독 부탁.")
    print("    → 쇼츠 대본...")
    shorts   = call(f"""{base}
{style}
[쇼츠 대본 - 총 30초 내외, 450자 내외]
{rules}
구성:
0-3초   후킹  : 가격 격차를 숫자로. 인트로 없이 바로
3-8초   문제  : 왜 이 가격 차이가 생기는지 궁금하게
8-20초  비교  : 가격대별로 실제 뭐가 다른지. 구체적 숫자
20-26초 판단  : 어느 가격대를 사야 하는지, 근거와 함께
26-30초 마무리: 다음 편 예고 + 구독
구간 사이는 빈 줄 하나. 순수 더빙 텍스트만.""", 800)
    print("    → 메타데이터...")
    meta = call(f"""카테고리: {category}
조사자료: {research[:1000]}
[유튜브 메타데이터 - 아래 형식 그대로 전부 출력]
▶ 영상 제목 A (가격 충격형, 숫자 포함, 40자 이내):
▶ 영상 제목 B (질문형, 40자 이내):
▶ 썸네일 문구
  메인: (8자 이내)
  서브: (12자 이내)
▶ 영상 설명란:
(3줄. 마지막 줄 반드시: "이 영상에는 쿠팡파트너스 활동을 통해 일정 수수료를 제공받을 수 있는 링크가 포함되어 있습니다.")
해시태그 5개
▶ 고정 댓글:
(제품 링크 자리 안내 + 대가성 문구)
▶ AI 영상 프롬프트 지시:
(카메라 무빙-줌·팬·패럴랙스만 허용. 제품 회전·변형·사용 장면 생성 금지)
전 항목 빠짐없이 작성.""", 2000)

    return f"""[후킹]
{hooking}

[공감]
{empathy}

[정보]
{info}

[판단·추천]
{judgment}

[아웃트로]
{outro}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📱 쇼츠 대본 (30초)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{shorts}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 유튜브 메타데이터
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{meta}"""


# ─── 4. 복지 정보 생성 (보고서 + 10씬 2,000자 대본) ────────
def generate_welfare_content(topic: str, research: str, is_monday: bool) -> tuple:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def call(prompt: str, tokens: int = 2000) -> str:
        resp = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text.strip()

    # ── 보고서 ───────────────────────────────────────────
    print("    → 복지 보고서 작성...")
    if is_monday:
        report_prompt = f"""아래 조사 자료를 바탕으로 시니어를 위한 정부 복지 혜택 보고서를 작성하세요.

주제: {topic}
조사 자료: {research[:2500]}

형식 (아래 그대로):
▶ 핵심 한 줄 요약:
▶ 지원 금액 / 혜택 내용:
▶ 신청 자격 (나이·소득·조건):
▶ 신청 방법:
  1단계.
  2단계.
  3단계.
▶ 신청처:
▶ 필요 서류:
▶ 주의사항:
▶ 2026년 변경사항: (없으면 "변경 없음")

확인된 수치만. 추정이면 (추정) 표시. 형식 그대로 출력."""
    else:
        report_prompt = f"""아래 조사 자료를 바탕으로 시니어를 위한 생활 정보 보고서를 작성하세요.

주제: {topic}
조사 자료: {research[:2500]}

형식 (아래 그대로):
▶ 핵심 한 줄 요약:
▶ 알아야 할 핵심 수치·기준:
▶ 올바른 선택·행동 방법:
  1.
  2.
  3.
▶ 흔한 실수 / 잘못된 상식:
▶ 비용 또는 지원 여부:
▶ 전문가 권고 (출처 포함):

확인된 수치만. 추정이면 (추정) 표시. 형식 그대로 출력."""

    report = call(report_prompt, 1500)

    # ── 10씬 대본 (2,000자) ──────────────────────────────
    print("    → 복지 대본 10씬 작성...")
    if is_monday:
        scene_4_to_8 = """[씬 4~6 - 핵심 정보] 3씬
혜택 내용, 지원 금액, 신청 자격을 구체적 수치와 함께 설명.

[씬 7~8 - 신청 방법] 2씬
어디서, 어떻게, 뭘 준비해야 하는지 단계별로."""
    else:
        scene_4_to_8 = """[씬 4~6 - 핵심 정보] 3씬
올바른 선택 기준, 구체적 수치, 전문가 권고 내용.

[씬 7~8 - 실전 방법] 2씬
단계별 행동 요령, 흔한 실수 주의사항."""

    script_prompt = f"""당신은 '골든헬퍼' 유튜브 채널 대본 작가입니다.
시니어(60대 이상)와 그 가족을 시청자로, 아래 주제를 유튜브 대본으로 작성하세요.

주제: {topic}
조사 자료: {research[:2000]}

[씬 구성 — 총 10씬, 각 씬 정확히 200자, 합계 약 2,000자]

[씬 1 - 후킹] 1씬
숫자나 충격적 사실로 바로 시작. "여러분" 인트로 절대 금지.

[씬 2~3 - 공감] 2씬
모르는 사람이 많은 이유, 해당되는 상황 공감.

{scene_4_to_8}

[씬 9 - 주의사항] 1씬
놓치기 쉬운 함정 1가지.

[씬 10 - 아웃트로] 1씬
다음 편 예고 + 구독 요청.

규칙:
- 제목, 소제목, 마크다운(#, ##, **) 절대 금지
- 순수 더빙 텍스트만
- 각 씬 정확히 200자 내외
- 씬과 씬 사이 빈 줄 하나
- 경어체. 60대 이상도 이해하는 쉬운 말.
더빙 텍스트만 출력."""

    script = call(script_prompt, 4000)
    return report, script


# ─── 5. 이메일 발송 ──────────────────────────────────────
def send_email(
    category: str, item_script: str,
    topic: str, welfare_report: str, welfare_script: str,
    is_monday: bool
) -> bool:
    today        = datetime.now().strftime("%Y년 %m월 %d일")
    weekday_str  = "월요일" if is_monday else "목요일"
    welfare_label = "정부 복지 혜택" if is_monday else "시니어 생활정보"

    def render_script(text: str, accent: str) -> str:
        lines = text.split("\n")
        out = ""
        scene_count = 0
        colors = ["#ffffff", "#f8fafc"]
        for line in lines:
            if line.strip() == "":
                out += "<br>"
                scene_count += 1
            elif (line.startswith("[") or line.startswith("━") or
                  line.startswith("📋") or line.startswith("📱")):
                out += f'<div style="font-size:11px;font-weight:800;color:{accent};margin:16px 0 6px 0;">{line}</div>'
            else:
                bg = colors[scene_count % 2]
                out += (f'<div style="background:{bg};border-left:3px solid {accent};'
                        f'padding:12px 16px;margin-bottom:2px;font-size:15px;'
                        f'color:#1e293b;line-height:1.9;border-radius:0 6px 6px 0;">{line}</div>')
        return out

    def render_report(text: str) -> str:
        out = ""
        for line in text.split("\n"):
            s = line.strip()
            if not s:
                out += "<br>"
            elif s.startswith("▶"):
                out += f'<div style="font-size:13px;font-weight:800;color:#065f46;margin:10px 0 3px 0;">{s}</div>'
            elif s and s[0].isdigit():
                out += f'<div style="font-size:13px;color:#1e293b;padding-left:16px;line-height:1.9;">{s}</div>'
            else:
                out += f'<div style="font-size:13px;color:#334155;line-height:1.9;padding-left:4px;">{s}</div>'
        return out

    item_html    = render_script(item_script, "#E9A825")
    welfare_html = render_script(welfare_script, "#10b981")
    report_html  = render_report(welfare_report)

    category_short = category.split("(")[0].strip()

    html = f"""
<div style="max-width:700px;margin:0 auto;font-family:'Apple SD Gothic Neo','Malgun Gothic',Arial,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:20px;">
  <tr><td style="background-color:#1F1F22;border-radius:14px;padding:32px;text-align:center;">
    <div style="font-size:26px;font-weight:900;color:#ffffff;">🏅 골든헬퍼</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:8px;">시니어를 위한 아이템 & 복지 정보</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:4px;">{today} ({weekday_str})</div>
  </td></tr>
  </table>

  <!-- ══ 섹션 1: 아이템 대본 ══ -->
  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:8px;">
  <tr><td style="background-color:#E9A825;border-radius:10px 10px 0 0;padding:14px 20px;">
    <div style="font-size:15px;font-weight:900;color:#1a1a2e;">📦 이번 주 아이템 대본</div>
    <div style="font-size:12px;color:#1a1a2e;margin-top:3px;opacity:0.75;">{category}</div>
  </td></tr>
  </table>

  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:16px;">
  <tr><td style="background-color:#fffbeb;border-left:4px solid #E9A825;border-radius:0 8px 8px 0;padding:14px 20px;">
    <div style="font-size:12px;font-weight:800;color:#92400e;margin-bottom:6px;">📌 제작 가이드</div>
    <div style="font-size:12px;color:#1e293b;line-height:1.8;">
      ✅ 효능·치료 표현 금지 &nbsp;|&nbsp; ✅ "써보니" 표현 금지<br>
      ✅ 판단 근거는 유통·가격 데이터 &nbsp;|&nbsp; ✅ 대가성 문구 필수 &nbsp;|&nbsp; ✅ AI 영상은 카메라 무빙만
    </div>
  </td></tr>
  </table>

  <div style="margin-bottom:32px;">{item_html}</div>

  <!-- ══ 구분선 ══ -->
  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin:0 0 24px 0;">
  <tr><td style="border-top:3px dashed #e2e8f0;"></td></tr>
  </table>

  <!-- ══ 섹션 2: 복지 정보 ══ -->
  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:8px;">
  <tr><td style="background-color:#10b981;border-radius:10px 10px 0 0;padding:14px 20px;">
    <div style="font-size:15px;font-weight:900;color:#ffffff;">📋 이번 주 {welfare_label}</div>
    <div style="font-size:12px;color:#ffffff;margin-top:3px;opacity:0.85;">{topic}</div>
  </td></tr>
  </table>

  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:16px;">
  <tr><td style="background-color:#f0fdf4;border:1px solid #bbf7d0;border-radius:0 0 10px 10px;padding:20px 22px;">
    <div style="font-size:13px;font-weight:900;color:#065f46;margin-bottom:12px;">📊 조사 보고서</div>
    {report_html}
  </td></tr>
  </table>

  <div style="margin-bottom:20px;">{welfare_html}</div>

  <div style="text-align:center;padding:20px;font-size:12px;color:#94a3b8;">
    골든헬퍼 | Powered by Gemini + Claude
  </div>
</div>"""

    subject = f"🏅 골든헬퍼 | {category_short} + {topic.split('—')[0].strip()} | {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText("골든헬퍼 아이템 & 복지 정보", "plain", "utf-8"))
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


# ─── 메인 ────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("🏅 골든헬퍼 통합 콘텐츠 생성")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    week_num    = datetime.now().isocalendar()[1]
    weekday     = datetime.now().weekday()
    is_monday   = (weekday == 0)
    weekday_str = "월요일" if is_monday else "목요일"

    slot_item    = (week_num * 2 + (0 if is_monday else 1)) % len(CATEGORIES)
    category     = CATEGORIES[slot_item]
    topics       = TOPICS_MON if is_monday else TOPICS_THU
    slot_welfare = week_num % len(topics)
    topic        = topics[slot_welfare]

    print(f"\n📅 {weekday_str}")
    print(f"   📦 아이템: {category}")
    print(f"   📋 복지:   {topic}\n")

    print("🔍 [1/2] 아이템 Gemini 조사 중...")
    item_research = search_item_with_gemini(category)
    print("   완료\n")

    print("🔍 [2/2] 복지 정보 Gemini 조사 중...")
    welfare_research = search_welfare_with_gemini(topic, is_monday)
    print("   완료\n")

    print("✍️  [1/2] 아이템 대본 작성 중...")
    item_script = generate_item_script(category, item_research)
    print("   완료\n")

    print("✍️  [2/2] 복지 정보 작성 중...")
    welfare_report, welfare_script = generate_welfare_content(topic, welfare_research, is_monday)
    print("   완료\n")

    fname = f"golden_helper_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(f"=== 📦 아이템: {category} ===\n\n{item_script}\n\n")
        f.write(f"=== 📋 복지 정보: {topic} ===\n\n")
        f.write(f"[보고서]\n{welfare_report}\n\n[대본]\n{welfare_script}")
    print(f"  📄 저장: {fname}\n")

    print("📧 메일 발송 중...")
    send_email(category, item_script, topic, welfare_report, welfare_script, is_monday)

    print("\n✅ 완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
