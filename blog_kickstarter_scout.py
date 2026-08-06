#!/usr/bin/env python3
"""
상품 보는 남자 - 해외 신상 발굴 (킥스타터) 자동화
매주 월·목 오후 3시 실행
Gemini로 크라우드펀딩 신상 발굴 → Claude로 블로그 초안 작성 → 이메일 발송
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


def search_products_with_gemini() -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                "킥스타터(Kickstarter), 인디고고(Indiegogo), 프로덕트헌트(Product Hunt)에서 "
                "최근 2~4주 내 주목받는 신상 제품을 3~5개 발굴해줘.\n\n"
                "선정 기준:\n"
                "- 펀딩 달성률 300% 이상 OR 후원자 1,000명 이상\n"
                "- 배송 가능 단계 (캠페인 진행 중 OR 최근 완료)\n"
                "- 한국 시장 적용 가능성 (배송 가능, 국내 수요 예상)\n"
                "- 기존 제품과 명확한 차별화 포인트\n\n"
                "각 제품별 아래 항목을 빠짐없이 출력:\n"
                "1. 제품명 (영문 + 한글 번역)\n"
                "2. 캠페인 링크\n"
                "3. 가격 (캠페인가 / 예상 정가)\n"
                "4. 펀딩 현황 (달성률%, 후원자수)\n"
                "5. 핵심 차별화 포인트 2~3개\n"
                "6. 한국 시장 적용 가능성 및 이유\n"
                "7. 대표 이미지 URL (공식 캠페인 이미지만, 저작권 문제없는 것)\n"
                "8. 잠재 리스크 (배송 지연·특허·국내 경쟁 등)\n\n"
                "수치는 확인된 것만. 추정이면 (추정)으로 표시. "
                "확인 불가한 이미지 URL은 '확인불가'로 표시할 것."
            ),
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        return resp.text
    except Exception as e:
        print(f"  ⚠️  Gemini 서치 실패: {e}")
        return ""


def generate_blog_drafts(research: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today = datetime.now().strftime("%Y년 %m월 %d일")

    prompt = f"""당신은 '상품 보는 남자' 네이버 블로그 운영자입니다.
해외 소싱·구매대행 사업자 시각에서 크라우드펀딩 신상품을 소개하는 블로그 포스팅 초안을 작성하세요.

작성일: {today}

조사 자료:
{research}

===

제품마다 아래 형식으로 작성하세요. 제품 개수(3~5개)만큼 반복.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 [제품명 (한글)]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▶ 캠페인 링크: [URL]
▶ 이미지 URL: [URL 또는 확인불가]

▶ 제목 후보 A: (호기심·비교형, 30자 이내)
▶ 제목 후보 B: (키워드·정보형, 30자 이내)

▶ 본문:
(도입부 2~3문장 → 제품 소개 3~4문장 → 차별화 포인트 3~4문장 → 가격·소싱 관점 2~3문장 → 마무리 1~2문장)
총 600~800자. 조건:
- "써봤다" 표현 금지 — 소싱·유통 사업자 시각으로만
- 의료·건강 효능 주장 금지
- 구체적 수치(가격·달성률·후원자수) 반드시 포함
- 마무리 문단 앞에 반드시 아래 한 줄 삽입 (빈칸으로 둘 것):
  [마스터 코멘트 입력란]

▶ 해시태그: (5개)

───────────────────────────────

화자 포지션: 체험자 아닌 소싱 전문가. 판단 근거는 시장성·가격·수요 데이터.
"제가 소싱 관점에서 보면" 류의 표현을 자연스럽게 사용.
순수 텍스트만 출력. 마크다운(#, ##, **) 절대 금지."""

    resp = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )
    return resp.content[0].text.strip()


def send_email(drafts: str, research: str) -> bool:
    today = datetime.now().strftime("%Y년 %m월 %d일")
    weekday_str = ["월", "화", "수", "목", "금", "토", "일"][datetime.now().weekday()]

    lines = drafts.split("\n")
    formatted = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            formatted += "<br>"
        elif stripped.startswith("━"):
            formatted += '<div style="border-top:2px solid #e2e8f0;margin:20px 0 10px 0;"></div>'
        elif stripped.startswith("📦"):
            formatted += f'<div style="font-size:17px;font-weight:900;color:#1e293b;margin:8px 0 4px 0;">{stripped}</div>'
        elif stripped.startswith("▶ 제목 후보"):
            formatted += f'<div style="font-size:14px;font-weight:800;color:#0f4c81;background-color:#eff6ff;padding:8px 12px;border-radius:6px;margin:4px 0;">{stripped}</div>'
        elif "[마스터 코멘트 입력란]" in stripped:
            formatted += f'<div style="background-color:#fef9c3;border:2px dashed #ca8a04;border-radius:8px;padding:14px 16px;margin:10px 0;font-size:14px;color:#92400e;font-weight:700;">{stripped}<br><br><span style="color:#a16207;font-weight:400;font-size:13px;">(여기에 코멘트를 입력하고 이 줄은 삭제하세요)</span></div>'
        elif stripped.startswith("▶ 캠페인 링크:") or stripped.startswith("▶ 이미지 URL:"):
            parts = stripped.split(":", 1)
            label = parts[0] + ":"
            url = parts[1].strip() if len(parts) > 1 else ""
            if url.startswith("http"):
                formatted += f'<div style="font-size:13px;color:#475569;margin:3px 0;">{label} <a href="{url}" style="color:#0f4c81;word-break:break-all;">{url}</a></div>'
            else:
                formatted += f'<div style="font-size:13px;color:#475569;margin:3px 0;">{stripped}</div>'
        elif stripped.startswith("▶"):
            formatted += f'<div style="font-size:13px;font-weight:700;color:#334155;margin:6px 0 2px 0;">{stripped}</div>'
        elif stripped.startswith("───"):
            formatted += '<div style="border-top:1px solid #f1f5f9;margin:16px 0;"></div>'
        else:
            formatted += f'<div style="font-size:14px;color:#334155;line-height:1.9;margin:1px 0;">{stripped}</div>'

    research_preview = research[:2000].replace("<", "&lt;").replace(">", "&gt;")

    html = f"""
<div style="max-width:700px;margin:0 auto;font-family:'Apple SD Gothic Neo','Malgun Gothic',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:20px;">
  <tr><td style="background-color:#0f172a;border-radius:14px;padding:32px;text-align:center;">
    <div style="font-size:26px;font-weight:900;color:#ffffff;">상품 보는 남자</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:8px;">해외 신상 발굴 리포트 · Kickstarter / Indiegogo</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:4px;">{today} ({weekday_str})</div>
    <div style="display:inline-block;background-color:#f59e0b;color:#1a1a2e;border-radius:20px;padding:6px 20px;font-size:13px;font-weight:700;margin-top:12px;">🌐 해외 신상 발굴</div>
  </td></tr>
  </table>

  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:20px;">
  <tr><td style="background-color:#fef2f2;border-left:4px solid #ef4444;border-radius:0 8px 8px 0;padding:16px 20px;">
    <div style="font-size:13px;font-weight:800;color:#991b1b;margin-bottom:8px;">📋 발행 전 체크리스트</div>
    <div style="font-size:13px;color:#1e293b;line-height:1.9;">
      ☐ 제목 전체를 네이버에 검색 → 통합검색·블로그탭 노출 여부 확인<br>
      ☐ [마스터 코멘트 입력란] 직접 작성 후 삭제<br>
      ☐ 대표 이미지 직접 캡처해서 첨부<br>
      ☐ 캠페인 링크 정상 동작 확인
    </div>
  </td></tr>
  </table>

  <div>{formatted}</div>

  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-top:24px;">
  <tr><td style="background-color:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px 18px;">
    <div style="font-size:12px;font-weight:700;color:#64748b;margin-bottom:8px;">📊 Gemini 수집 원문 (참고용)</div>
    <div style="font-size:12px;color:#94a3b8;line-height:1.7;white-space:pre-wrap;">{research_preview}...</div>
  </td></tr>
  </table>

  <div style="text-align:center;padding:20px;font-size:12px;color:#94a3b8;">
    상품 보는 남자 | Powered by Gemini + Claude
  </div>
</div>"""

    subject = f"🌐 [신상발굴] 해외 크라우드펀딩 신상품 | {today}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText("상품 보는 남자 - 해외 신상 발굴 리포트", "plain", "utf-8"))
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
    print("🌐 상품 보는 남자 - 신상 발굴 시작")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    print("\n🔍 Gemini 신상 탐색 중...")
    research = search_products_with_gemini()
    if not research.strip():
        print("\n🚨 Gemini 검색 실패 — 발행 중단")
        raise SystemExit(1)
    print("   탐색 완료\n")

    print("✍️  Claude 블로그 초안 작성 중...")
    drafts = generate_blog_drafts(research)
    print("   완료\n")

    fname = f"kickstarter_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(drafts)
    print(f"  📄 저장: {fname}\n")

    print("📧 메일 발송 중...")
    send_email(drafts, research)

    print("\n✅ 완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
