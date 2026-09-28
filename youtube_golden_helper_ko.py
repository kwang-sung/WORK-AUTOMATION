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
- 셀러·유통업자 관점 (2026-09-28 마스터 지시: 이 채널 시청자는 시니어와 자녀 = 구매자)
  · 소싱, 원가, 코스트, 마진, 도매, 셀러, 구매대행, 수입 단가 같은 말
  · 타오바오, 알리익스프레스, 1688, 아마존 원가 비교
  · "제가 소싱하면서", "저는 ~를 업으로" 같은 화자 1인칭 경험·직업 이야기
- 숫자를 한글로 풀어 쓰기 ("천오백칠십칠", "삼만 원") → 아라비아 숫자로 (1577-1000, 3만 원)
"""

ITEM_FRAMING = """
[화자 포지션]
- 화자는 '골든헬퍼' 진행자. 부모님 물건을 대신 꼼꼼히 비교해 주는 사람
- 시청자는 60대 이상 시니어와 부모님 물건을 고르는 자녀(구매자)
- 판단 근거는 공개된 정보: 국내 판매 가격대(쿠팡·네이버), 재질·크기·무게 같은 스펙, 표시·인증(식기처럼 입에 닿는 제품은 '식품용' 표시/도안, 전기제품은 KC. 인증 이름을 지어내지 않는다), 후기에 자주 나오는 불만과 반품 사유
- 사용 상황 중심: 손 떨림, 악력 약함, 한쪽 마비, 치매 초기처럼 누가 어떤 상황에서 쓰는지로 설명
- 1인칭 경험·직업 이야기를 하지 않는다. "직접 써봤다"도, "소싱한다"도 말하지 않는다
"""

# ─── 1. 아이템 Gemini 조사 ───────────────────────────────
def search_item_with_gemini(category: str) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                f"시니어용 '{category}' 카테고리를 '부모님 물건을 고르는 구매자' 입장에서 조사해줘.\n\n"
                f"1. 쿠팡·네이버쇼핑 대표 상품 5개 (상품명, 판매가, 리뷰 수, 평점)\n"
                f"2. 가격대 구간(예: 1만 원 미만 / 1~3만 원 / 3만 원 이상)과 구간별로 달라지는 재질·구조·크기·무게·인증\n"
                f"3. 후기에서 자주 나오는 불만과 반품 사유\n"
                f"4. 어떤 사용 상황(손 떨림, 악력 약함, 편마비 등)에 어떤 형태가 맞는지\n"
                f"5. 고를 때 확인할 체크포인트 3~5개\n"
                f"6. 의료기기 분류 가능성, 장기요양 복지용구 급여 대상 여부\n\n"f"가격은 확인된 수치만. 추정이면 추정이라고 표시할 것."
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
    """아이템편 대본 (2026-09-28 재작성).
    - 시청자: 60대 이상 시니어와 부모님 물건을 고르는 자녀(구매자). 셀러·소싱 관점 금지.
    - 씬을 따로따로 부르면 같은 문장이 씬마다 반복돼서(예: '제가 소싱하면서') 롱폼 전체를 한 번에 쓴다.
    - 금지 표현이 나오면 최대 2번 다시 쓰게 한다.
    """
    import re as _re
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    seller_words = _re.compile(
        r"소싱|원가|코스트|마진|도매|셀러|구매대행|수입 ?단가|타오바오|알리익스프레스|1688|"
        r"제가 |저는 |써보니|써봤|사용해 ?보니|치료|완치|효능|특효|명의|부작용 ?없|100%|기적|걱정 ?끝|끝이에요")

    def call(prompt: str, tokens: int = 1000) -> str:
        text = ""
        for attempt in range(3):
            extra = "" if attempt == 0 else (
                "\n\n[재작성] 직전 결과에 금지 표현이 있었습니다: "
                + ", ".join(sorted(set(seller_words.findall(text))))
                + ". 시니어·자녀 구매자 관점으로 다시 쓰고, 이 말들을 쓰지 마세요. 나머지 구성은 그대로.")
            # 9/28: 출력이 문장 중간에서 잘리는 문제(max_tokens 부족) → 넉넉히 주고, 잘렸으면 한 번 더 늘려 재시도
            for mult in (2, 3):
                resp = client.messages.create(
                    model="claude-sonnet-5",
                    max_tokens=min(tokens * mult, 20000),   # 2만 넘으면 SDK 가 스트리밍을 요구함
                    messages=[{"role": "user", "content": prompt + extra}]
                )
                text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
                if getattr(resp, "stop_reason", "") != "max_tokens":
                    break
                print(f"    [잘림] max_tokens {tokens * mult} 부족, 늘려서 재시도")
            if not seller_words.search(text):
                return text
            print(f"    [금지 표현 발견] 재작성 {attempt + 1}: " + ", ".join(sorted(set(seller_words.findall(text)))))
        return text

    common = f"""당신은 유튜브 채널 '골든헬퍼'의 대본 작가입니다.
골든헬퍼는 60대 이상 시니어와, 부모님 물건을 대신 고르는 40~50대 자녀가 보는 채널입니다.
이번 편은 '{category}'를 **잘 고르는 법**을 알려 주는 아이템편입니다.

{ITEM_FRAMING}
{ITEM_BANNED}

[조사 자료] (확인된 수치만 쓰고, 자료에 없는 숫자는 만들지 않는다)
{research[:3500]}

[말투]
- 귀로 듣기 쉬운 짧은 문장. 한 문장 40자 안팎, 한 문단 2~4문장
- 경어체 '~합니다/~해요'를 섞는다. 어르신께는 '어르신', 자녀에게는 '자녀분' 또는 '부모님 물건 고르실 때'
- 설명만 늘어놓지 말고 문단마다 한 번쯤 질문을 던진다 ("그럼 무게는 얼마가 적당할까요?")
- 같은 표현을 두 번 쓰지 않는다. 특히 문단 첫머리를 매번 다르게 시작한다
- 숫자는 아라비아 숫자와 단위로 (3만 원, 40g, 2.5cm, 1577-1000)
- 겁주거나 충격 요법을 쓰지 않는다. 담담하고 친절하게"""

    rules = """[출력 규칙]
- 제목·소제목·해시태그·마크다운(#, **) 금지. 순수 더빙 텍스트만
- 문단과 문단 사이 빈 줄 하나"""

    print("    → 롱폼 대본(한 번에)...")
    body = call(f"""{common}

[롱폼 구성 — 총 16~18문단, 2,400~2,900자]
1. 후킹 1문단: 구매자가 놓치기 쉬운 사실 하나를 숫자로 (예: 비슷해 보이는데 가격이 3배 차이, 후기 불만 1위가 '무거워서'). 인트로·인사 없이 바로
2. 공감 2문단: 부모님 물건을 고를 때 막막한 이유 (비슷비슷한 상품, 후기만으로는 모름)
3. 고르는 기준 4문단: 체크포인트 3~4개를 하나씩 (예: 손잡이 굵기, 무게, 재질·인증, 세척). 각 기준마다 '왜 중요한지'와 '어떻게 확인하는지(상세페이지 어디를 보면 되는지)'
4. 가격대별 차이 4문단: 1만 원 미만 / 1~3만 원 / 3만 원 이상처럼 구간을 나눠 재질·구조·크기·무게·인증이 어떻게 달라지는지. 조사 자료의 실제 판매가 범위를 쓴다
5. 상황별 추천 3문단: 손 떨림이 심할 때, 악력이 약할 때, 선물로 드릴 때 등 누가 어떤 걸 고르면 되는지
6. 주의·반품 팁 1문단: 후기에 자주 나오는 불만과 사기 전에 확인할 것. 의료기기처럼 보이는 효과 광고는 조심하라는 안내
7. 복지용구 안내 1문단: 장기요양 복지용구 급여 대상이면 '본인부담 15%로 살 수 있는지 먼저 확인하세요'처럼 안내 (대상이 아니면 이 문단 생략)
8. 마무리 1문단: 오늘 기준 3가지를 한 줄로 다시 정리 + 영상 아래 상품 정보 안내 + 구독 부탁

{rules}""", 6000)

    print("    → 쇼츠 대본...")
    shorts = call(f"""{common}

[쇼츠 대본 — 30초 안팎, 380~450자, 5문단]
1. 0~3초: 구매자가 놓치기 쉬운 사실 하나를 숫자로. 인트로 없이 바로
2. 3~8초: 부모님 물건 고를 때 흔히 하는 실수
3. 8~20초: 고르는 기준 2~3개를 짧게 (숫자 포함)
4. 20~26초: 누가 어떤 걸 고르면 되는지 한 문장
5. 26~30초: "자세한 비교는 관련 영상에서, 상품은 영상 아래에서 확인하세요"
각 문단은 앞뒤 없이 혼자 들어도 이해되는 완결된 문장으로.

{rules}""", 1200)

    print("    → 메타데이터...")
    meta = call(f"""아래 조사 자료를 참고해서 **유튜브 메타데이터만** 작성하세요. 조사 자료를 이어 쓰거나 요약하지 마세요.
카테고리: {category}
<조사자료>{research[:1200]}</조사자료>
{ITEM_BANNED}
[유튜브 메타데이터 - 아래 형식 그대로 전부 출력]
▶ 영상 제목 A (고르는 법형, 숫자 포함, 40자 이내. 예: '그립 수저, 고를 때 이 3가지만 보세요'):
▶ 영상 제목 B (질문형, 40자 이내):
▶ 썸네일 문구
  메인: (8자 이내)
  서브: (12자 이내)
▶ 영상 설명란:
(첫 줄: "이 영상에는 유튜브 쇼핑 제휴 링크가 포함되어 있으며, 구매 시 채널이 일정 수수료를 받을 수 있습니다." 그다음 3줄 요약)
해시태그 5개
▶ 고정 댓글:
(오늘 기준 3가지 요약 + 상품은 영상 아래 '제품 보기'에서 확인 안내)
▶ 상품 태그 검색어:
(유튜브 쇼핑에서 검색할 일반명 1개. 예: '그립 수저')
▶ AI 영상 프롬프트 지시:
(카메라 무빙-줌·팬·패럴랙스만 허용. 문단마다 그 문단이 말하는 대상을 보여 주는 설명용 정물컷: 브랜드·로고·글자 없는 일반 사물. 사람이 사용하는 장면·효과 연출은 만들지 않는다)
전 항목 빠짐없이 작성.""", 2000)

    return f"""{body}

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
        # 9/28: 대본이 중간에 끊기던 문제(max_tokens 부족) 수정
        for mult in (2, 3):
            resp = client.messages.create(
                model="claude-sonnet-5",
                max_tokens=min(tokens * mult, 20000),   # 2만 넘으면 SDK 가 스트리밍을 요구함
                messages=[{"role": "user", "content": prompt}]
            )
            text = "\n".join(b.text for b in resp.content if b.type == "text").strip()
            if getattr(resp, "stop_reason", "") != "max_tokens":
                return text
            print(f"    [잘림] max_tokens {tokens * mult} 부족, 늘려서 재시도")
        return text

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
구체적인 숫자(금액·대상 인원·기한)로 바로 시작. 겁주는 말 금지. "여러분" 인트로 절대 금지.

[씬 2~3 - 공감] 2씬
모르는 사람이 많은 이유, 해당되는 상황 공감.

{scene_4_to_8}

[씬 9 - 주의사항·문의처] 1씬
놓치기 쉬운 함정 1가지 + 문의처(전화번호는 숫자로, 예: 국민건강보험공단 1577-1000).

[씬 10 - 아웃트로] 1씬
다음 편 예고 + 구독 요청.

규칙:
- 제목, 소제목, 마크다운(#, ##, **) 절대 금지
- 순수 더빙 텍스트만
- 각 씬 정확히 200자 내외
- 씬과 씬 사이 빈 줄 하나
- 경어체. 60대 이상도 이해하는 쉬운 말. 한 문장 40자 안팎으로 짧게.
- 기준 연도를 밝힌다(예: 2026년 기준). 조사 자료에 없는 금액·조건은 만들지 않는다.
- 효능·치료·완치 단정, "써보니" 체험담, 1인칭 경험 이야기 금지.
- 숫자는 아라비아 숫자로 (전화번호 1577-1000, 금액 136만 원, 비율 10%). 한글로 풀어 쓰지 않는다
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
