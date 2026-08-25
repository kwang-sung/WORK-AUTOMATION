#!/usr/bin/env python3
"""
골든헬퍼 - 시니어 아이템 콘텐츠 자동 생성
매주 월·목 오후 3시 실행
롱폼(18씬) + 쇼츠(30초) 대본 동시 생성
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

BANNED = """
[절대 금지 - 위반 시 채널 리스크]
- 의학적 효능/치료/완화/예방 주장 ("혈액순환 개선", "통증 완화", "치매 예방" 등)
- 직접 사용 후기 표현 ("써보니", "한 달 사용해보니", "재질이 부드럽다")
- 의료기기 해당 가능 품목의 효과 단정
- 특정 질환명과 제품을 인과로 연결
"""

FRAMING = """
[화자 포지션 - 반드시 유지]
- 화자는 체험자가 아니라 해외 소싱을 업으로 하는 사람이다
- 판단 근거는 사용감이 아니라 유통/가격/데이터다
- "제가 소싱하면서 본 바로는" 류의 근거 표현을 판단 앞에 붙인다
- 안 써봤다는 사실을 숨기지 않는다. 그게 신뢰의 근거다
"""

def search_with_gemini(category: str) -> str:
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
        print(f"  ⚠️  Gemini 서치 실패: {e}")
        return ""

def generate_script(category: str, research: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def call(prompt: str, tokens: int = 1000) -> str:
        resp = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return next((b.text for b in resp.content if b.type == "text"), "").strip()

    base = f"""카테고리: {category}
화자 포지션: {FRAMING}
금지 사항: {BANNED}
조사자료: {research[:2000]}"""

    rules = """규칙:
- 제목, 소제목, 해시태그, 마크다운(#, ##, **) 절대 금지
- 순수 더빙 텍스트만
- 각 씬 정확히 200자 내외
- 씬과 씬 사이 빈 줄 하나만
더빙 텍스트만 출력."""

    style = "톤: 60대 이상과 그 자녀가 함께 들어도 이해되는 쉬운 말. 경어체. 담담하게. 호들갑 금지."

    print("    → 후킹 씬...")
    hooking = call(f"{base}\n{style}\n[후킹 씬 - 1개]\n{rules}\n가격 격차를 숫자로. 인트로 없이 바로.")

    print("    → 공감 씬...")
    empathy = call(f"{base}\n{style}\n[공감 씬 - 4개]\n{rules}\n부모님 물건 구매에서 겪는 고민과 어려움.", 2000)

    print("    → 정보 씬...")
    info = call(f"{base}\n{style}\n[정보 씬 - 9개]\n{rules}\n가격대별로 실제 뭐가 다른지. 구체적 숫자. 소싱처 명시.", 4500)

    print("    → 판단 씬...")
    judgment = call(f"{base}\n{style}\n[판단·추천 씬 - 3개]\n{rules}\n어느 가격대를 사야 하는지 근거와 함께. 소싱 관점.", 1500)

    print("    → 아웃트로 씬...")
    outro = call(f"{base}\n{style}\n[아웃트로 씬 - 1개]\n{rules}\n다음 영상 예고 + 구독 부탁.")

    print("    → 쇼츠 대본...")
    shorts = call(f"""{base}
{style}
[쇼츠 대본 - 총 30초 내외, 450자 내외]
{rules}

구성:
0-3초   후킹  : 가격 격차를 숫자로. 인트로 없이 바로
3-8초   문제  : 왜 이 가격 차이가 생기는지 궁금하게
8-20초  비교  : 가격대별로 실제 뭐가 다른지. 구체적 숫자
20-26초 판단  : 어느 가격대를 사야 하는지, 근거와 함께
26-30초 마무리: 다음 편 예고 + 구독

구간 사이는 빈 줄 하나. 순수 더빙 텍스트만.
""", 800)

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
(3줄. 마지막 줄 반드시 포함: "이 영상에는 쿠팡파트너스 활동을 통해 일정 수수료를 제공받을 수 있는 링크가 포함되어 있습니다.")
해시태그 5개

▶ 고정 댓글:
(제품 링크 자리 안내 + 대가성 문구)

▶ 화면 자막 지시 (구간별):

▶ AI 영상 프롬프트 지시:
(카메라 무빙-줌·팬·패럴랙스만 허용. 제품 회전·변형·사용 장면 생성 금지)

전 항목 빠짐없이 작성.""", 2000)

    full = f"""[후킹]
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

    total = len(full.replace(" ", "").replace("\n", ""))
    print(f"    → 총 글자수: {total}자")
    return full

def send_email(script: str, subject: str) -> bool:
    lines = script.split("\n")
    formatted = ""
    scene_count = 0
    colors = ["#ffffff", "#f8fafc"]
    for line in lines:
        if line.strip() == "":
            formatted += "<br>"
            scene_count += 1
        elif line.startswith("[") or line.startswith("━") or line.startswith("📋") or line.startswith("📱"):
            formatted += f'<div style="font-size:11px;font-weight:800;color:#E9A825;margin:16px 0 6px;">{line}</div>'
        else:
            bg = colors[scene_count % 2]
            formatted += f'<div style="background:{bg};border-left:3px solid #E9A825;padding:12px 16px;margin-bottom:2px;font-size:15px;color:#1e293b;line-height:1.9;border-radius:0 6px 6px 0;">{line}</div>'

    html = f"""
<div style="max-width:700px;margin:0 auto;font-family:'Apple SD Gothic Neo','Malgun Gothic',Arial,sans-serif;">
  <div style="background-color:#1F1F22;border-radius:14px;padding:32px;text-align:center;margin-bottom:20px;">
    <div style="font-size:26px;font-weight:900;color:#ffffff;">골든헬퍼</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:8px;">부모님 물건, 어디서 얼마에 사야 할까요</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:4px;">{datetime.now().strftime('%Y년 %m월 %d일')}</div>
    <div style="display:inline-block;background-color:#E9A825;color:#1a1a2e;border-radius:20px;padding:6px 20px;font-size:13px;font-weight:700;margin-top:12px;">🇰🇷 아이템 대본</div>
  </div>
  <div style="background-color:#fffbeb;border-left:4px solid #E9A825;border-radius:0 8px 8px 0;padding:16px 20px;margin-bottom:20px;">
    <div style="font-size:13px;font-weight:800;color:#92400e;margin-bottom:8px;">📌 제작 가이드</div>
    <div style="font-size:13px;color:#1e293b;line-height:1.8;">
      ✅ 효능·치료 표현 금지<br>
      ✅ "써보니" 표현 금지<br>
      ✅ 판단 근거는 유통·가격 데이터<br>
      ✅ 대가성 문구 필수<br>
      ✅ AI 영상은 카메라 무빙만
    </div>
  </div>
  <div>{formatted}</div>
  <div style="text-align:center;padding:20px;font-size:12px;color:#94a3b8;">
    골든헬퍼 | Powered by Gemini + Claude
  </div>
</div>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText("골든헬퍼 아이템 대본", "plain", "utf-8"))
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

def main():
    print("=" * 55)
    print("골든헬퍼 아이템 콘텐츠 생성")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    week_num    = datetime.now().isocalendar()[1]
    weekday     = datetime.now().weekday()
    slot        = (week_num * 2 + (0 if weekday == 0 else 1)) % len(CATEGORIES)
    category    = CATEGORIES[slot]
    today       = datetime.now().strftime("%Y년 %m월 %d일")
    weekday_str = "월요일" if weekday == 0 else "목요일"

    print(f"\n📅 오늘({weekday_str}) 카테고리: {category}\n")

    print("🔍 Gemini 자료 조사 중...")
    research = search_with_gemini(category)
    print("   조사 완료\n")

    print("✍️  대본 작성 중...")
    script = generate_script(category, research)
    print("   완료\n")

    fname = f"item_ko_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"  📄 저장: {fname}\n")

    print("📧 메일 발송 중...")
    send_email(script, f"🛒 [아이템 대본] {category} | {today}")

    print("\n✅ 완료!")
    print("=" * 55)

if __name__ == "__main__":
    main()
