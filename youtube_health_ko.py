#!/usr/bin/env python3
"""
시니어 건강 채널 - 한국어 대본 자동 생성
매주 월·목 오후 3시 실행
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

TOPICS = [
    {"category": "몸", "ko": "무릎이 시려서 잠 못 자는 밤, 혼자서 할 수 있는 것들"},
    {"category": "몸", "ko": "넘어질 것 같은 두려움, 집에서 혼자 고치는 방법"},
    {"category": "마음", "ko": "자식한테 전화하기 미안한 어르신께 드리는 말씀"},
    {"category": "마음", "ko": "혼자 밥 먹는 게 서러운 날을 위한 이야기"},
    {"category": "실용", "ko": "혼자 사는 70대가 꼭 알아야 할 것 5가지"},
    {"category": "실용", "ko": "병원에서 의사한테 꼭 물어봐야 할 것들"},
    {"category": "위로", "ko": "오래 살아서 미안하다고 하지 마세요"},
    {"category": "위로", "ko": "나이 드는 게 무서운 게 아닙니다"},
    {"category": "몸", "ko": "밥맛이 없어진 이유, 병원 가기 전에 먼저 확인하세요"},
    {"category": "마음", "ko": "친구들이 하나둘 떠나갈 때 마음을 지키는 방법"},
    {"category": "실용", "ko": "자식한테 폐 안 끼치고 혼자 건강하게 사는 법"},
    {"category": "위로", "ko": "당신이 살아온 것만으로 충분합니다"},
    {"category": "몸", "ko": "소변이 자꾸 마려운 70대, 창피한 게 아닙니다"},
    {"category": "마음", "ko": "내가 짐이 되는 것 같아서 무서운 밤"},
    {"category": "실용", "ko": "겨울 새벽 화장실 가다 쓰러지는 이유와 예방법"},
    {"category": "위로", "ko": "지금 이 나이가 가장 솔직한 나이입니다"},
]

KO_STYLE = """
## 한국어 대본 톤 (필수 준수)
- 따뜻하고 친근한 경어체 (~하세요, ~하셨나요, ~하시죠)
- 전문용어 절대 금지 → 쉬운 말로
- 오래된 동네 친구가 이야기하듯 편안하게
- 뻔한 상투어 금지
- 시청자 감정을 먼저 인정하고 공감
- 자식 걱정·효도 문화 반영
- 직접적이고 실용적인 조언
- 각 씬은 정확히 200자 내외
- 씬과 씬 사이는 빈 줄 하나로 구분
- 제목, 소제목, 해시태그, 마크다운(#, ##, **) 절대 금지
- 순수 더빙 텍스트만
"""

def search_with_gemini(topic: dict) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                f"70대 이상 시니어를 위한 다음 주제로 최신 정보를 조사해줘: {topic['ko']}\n\n"
                f"1. 관련 최신 의학·심리 연구나 통계\n"
                f"2. 전문가 조언\n"
                f"3. 실제 시니어들이 경험하는 구체적 상황\n"
                f"4. 집에서 혼자 할 수 있는 실질적 방법 9가지 이상\n"
            ),
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        return resp.text
    except Exception as e:
        print(f"  ⚠️  Gemini 서치 실패: {e}")
        return ""

def generate_script(topic: dict, research: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def call(prompt: str, tokens: int = 1000) -> str:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text.strip()

    base = f"""주제: {topic['ko']}
카테고리: {topic['category']}
스타일: {KO_STYLE}
조사자료: {research[:2000]}"""

    rules = """규칙:
- 제목, 소제목, 해시태그, 마크다운(#, ##, **) 절대 금지
- 순수 더빙 텍스트만
- 각 씬 정확히 200자 내외
- 씬과 씬 사이 빈 줄 하나만
더빙 텍스트만 출력."""

    print("    → 후킹 씬...")
    hooking = call(f"{base}\n[후킹 씬 - 1개]\n{rules}\n인트로 없이 바로 감정으로 시작.")

    print("    → 공감 씬...")
    empathy = call(f"{base}\n[공감 씬 - 4개]\n{rules}", 2000)

    print("    → 정보 씬...")
    info = call(f"{base}\n[정보·해결 씬 - 9개]\n{rules}\n집에서 혼자 할 수 있는 방법 9가지.", 4500)

    print("    → 위로 씬...")
    comfort = call(f"{base}\n[위로·마무리 씬 - 3개]\n{rules}", 1500)

    print("    → 아웃트로 씬...")
    outro = call(f"{base}\n[아웃트로 씬 - 1개]\n{rules}\n다음 영상 예고 + 구독 부탁.")

    print("    → 메타데이터...")
    meta = call(f"""주제: {topic['ko']}
카테고리: {topic['category']}

[유튜브 메타데이터 - 아래 형식 그대로 전부 출력]

▶ 영상 제목 A (감정 자극. 40자 이내):
▶ 영상 제목 B (정보성. 숫자 포함. 40자 이내):

▶ 썸네일 문구 A
  메인: (10자 이내)
  서브: (15자 이내)

▶ 썸네일 문구 B
  메인: (10자 이내)
  서브: (15자 이내)

▶ 영상 설명란:
(4~5줄. 공감 + 내용 + 채널소개 + 해시태그 5개)

5개 항목 전부 빠짐없이 작성하세요.""", 2000)

    full = f"""[후킹]
{hooking}

[공감]
{empathy}

[정보·해결]
{info}

[위로]
{comfort}

[아웃트로]
{outro}

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
        elif line.startswith("[") or line.startswith("━") or line.startswith("📋"):
            formatted += f'<div style="font-size:11px;font-weight:800;color:#1a3a6b;margin:16px 0 6px;">{line}</div>'
        else:
            bg = colors[scene_count % 2]
            formatted += f'<div style="background:{bg};border-left:3px solid #e2b04a;padding:12px 16px;margin-bottom:2px;font-size:15px;color:#1e293b;line-height:1.9;border-radius:0 6px 6px 0;">{line}</div>'

    html = f"""
<div style="max-width:700px;margin:0 auto;font-family:'Apple SD Gothic Neo','Malgun Gothic',Arial,sans-serif;">
  <div style="background-color:#1a3a6b;border-radius:14px;padding:32px;text-align:center;margin-bottom:20px;">
    <div style="font-size:26px;font-weight:900;color:#ffffff;">🎙️ 시니어 건강 채널 대본</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:8px;">{datetime.now().strftime('%Y년 %m월 %d일')}</div>
    <div style="display:inline-block;background-color:#e2b04a;color:#1a1a2e;border-radius:20px;padding:6px 20px;font-size:13px;font-weight:700;margin-top:12px;">🇰🇷 한국어 대본</div>
  </div>
  <div style="background-color:#fffbeb;border-left:4px solid #e2b04a;border-radius:0 8px 8px 0;padding:16px 20px;margin-bottom:20px;">
    <div style="font-size:13px;font-weight:800;color:#92400e;margin-bottom:8px;">📌 제작 가이드</div>
    <div style="font-size:13px;color:#1e293b;line-height:1.8;">
      ✅ 씬마다 이미지 1장 배치<br>
      ✅ 따뜻하고 친근한 톤으로<br>
      ✅ 천천히 또박또박<br>
      ✅ 빈 줄 = 씬 전환
    </div>
  </div>
  <div>{formatted}</div>
  <div style="text-align:center;padding:20px;font-size:12px;color:#94a3b8;">
    🎙️ 시니어 건강 채널 | Powered by Gemini + Claude
  </div>
</div>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText("시니어 건강 채널 대본", "plain", "utf-8"))
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
    print("🎙️ 시니어 건강 채널 한국어 대본 생성")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    week_num    = datetime.now().isocalendar()[1]
    weekday     = datetime.now().weekday()
    slot        = (week_num * 2 + (0 if weekday == 0 else 1)) % len(TOPICS)
    topic       = TOPICS[slot]
    today       = datetime.now().strftime("%Y년 %m월 %d일")
    weekday_str = "월요일" if weekday == 0 else "목요일"

    print(f"\n📅 오늘({weekday_str}) 주제: {topic['ko']}\n")

    print("🔍 Gemini 자료 조사 중...")
    research = search_with_gemini(topic)
    print("   조사 완료\n")

    print("✍️  한국어 대본 작성 중...")
    script = generate_script(topic, research)
    print("   완료\n")

    fname = f"health_ko_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"  📄 저장: {fname}\n")

    print("📧 메일 발송 중...")
    send_email(script, f"🎙️ [한국어 대본] {topic['ko']} | {today}")

    print("\n✅ 완료!")
    print("=" * 55)

if __name__ == "__main__":
    main()
