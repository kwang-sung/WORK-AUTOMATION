#!/usr/bin/env python3
"""
상품 보는 남자 - 해외 신상 발굴 (킥스타터) 자동화
매주 월·목 오후 3시 실행
Gemini로 크라우드펀딩 신상 발굴 → Claude로 블로그 초안 작성 → 이메일 발송
"""

import os
import re
import json
import time
import base64
import smtplib
import urllib.parse
import requests
import anthropic
from google import genai
from google.genai import types
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ─── 발행 이력 관리 ──────────────────────────────────────────
def load_history() -> dict:
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return {"products": []}
    try:
        gh = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{HISTORY_FILE}", headers=gh)
        if r.status_code == 200:
            return json.loads(base64.b64decode(r.json()["content"]).decode("utf-8"))
    except Exception as e:
        print(f"  ⚠️  이력 로드 실패: {e}")
    return {"products": []}


def save_history(history: dict, new_products: list):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    history["products"]  = (history.get("products", []) + new_products)[-60:]
    history["last_sent"] = datetime.now().strftime("%Y-%m-%d")
    gh = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    content = base64.b64encode(json.dumps(history, ensure_ascii=False, indent=2).encode()).decode()
    for attempt in range(3):
        try:
            sha = None
            r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{HISTORY_FILE}", headers=gh)
            if r.status_code == 200:
                sha = r.json().get("sha")
            payload = {"message": f"킥스타터 이력 업데이트 {datetime.now().strftime('%Y%m%d')}", "content": content}
            if sha:
                payload["sha"] = sha
            pr = requests.put(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{HISTORY_FILE}", headers=gh, json=payload)
            if pr.status_code in (200, 201):
                print("  ✅ 이력 저장 완료")
                return
            elif pr.status_code == 409:
                print(f"  ⚠️  SHA 충돌, 재시도 ({attempt+1}/3)...")
                time.sleep(3)
            else:
                print(f"  ⚠️  이력 저장 실패 ({pr.status_code})")
                return
        except Exception as e:
            print(f"  ⚠️  이력 저장 오류 ({attempt+1}/3): {e}")
            time.sleep(3)
    print("  ❌ 이력 저장 3회 실패")


KS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}

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
GITHUB_REPO       = os.environ.get("GITHUB_REPO", "")
HISTORY_FILE      = "data/kickstarter_history.json"


def lookup_kickstarter(product_name: str) -> dict:
    """Kickstarter 검색 JSON API로 실제 URL과 이미지를 직접 조회."""
    q = urllib.parse.quote(product_name)
    try:
        r = requests.get(
            f"https://www.kickstarter.com/projects/search.json?term={q}",
            headers=KS_HEADERS, timeout=10
        )
        if r.status_code != 200:
            return {"url": "확인불가", "image": "확인불가"}
        projects = r.json().get("projects", [])
        if not projects:
            return {"url": "확인불가", "image": "확인불가"}
        p = projects[0]
        return {
            "url":   p.get("urls", {}).get("web", {}).get("project", "확인불가"),
            "image": p.get("photo", {}).get("full", "확인불가"),
        }
    except Exception as e:
        print(f"    ⚠️  KS 조회 실패 ({product_name}): {e}")
        return {"url": "확인불가", "image": "확인불가"}


def search_products_with_gemini(excluded: list) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    exclude_block = ""
    if excluded:
        names = "\n".join(f"- {p}" for p in excluded[-30:])
        exclude_block = f"\n\n이미 소개한 제품 (반드시 제외할 것):\n{names}"
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
                "2. 가격 (캠페인가 / 예상 정가)\n"
                "3. 펀딩 현황 (달성률%, 후원자수)\n"
                "4. 핵심 차별화 포인트 2~3개\n"
                "5. 한국 시장 적용 가능성 및 이유\n"
                "6. 잠재 리스크 (배송 지연·특허·국내 경쟁 등)\n\n"
                "수치는 확인된 것만. 추정이면 (추정)으로 표시.\n"
                "URL·이미지는 별도로 직접 조회하므로 출력 불필요."
                + exclude_block +
                "\n\n마지막에 반드시 아래 블록 추가 (킥스타터 제품 영문명만, JSON 배열):\n"
                "===PRODUCTS===\n"
                "[\"영문제품명1\", \"영문제품명2\"]\n"
                "===END==="
            ),
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        research = resp.text
    except Exception as e:
        print(f"  ⚠️  Gemini 서치 실패: {e}")
        return ""

    # 제품명 파싱 → Kickstarter API 직접 조회
    m = re.search(r"===PRODUCTS===\s*(\[.*?\])\s*===END===", research, re.DOTALL)
    if m:
        try:
            names = json.loads(m.group(1))
            lines = ["\n\n─── Kickstarter API 직접 조회 결과 (URL·이미지 최우선 사용) ───"]
            for name in names:
                info = lookup_kickstarter(name)
                short_url = info["url"][:70] if info["url"] != "확인불가" else "확인불가"
                print(f"    🔗 [{name}] {short_url}")
                lines.append(f"\n제품명: {name}")
                lines.append(f"  캠페인 URL: {info['url']}")
                lines.append(f"  대표 이미지: {info['image']}")
            research += "\n".join(lines)
        except Exception as e:
            print(f"  ⚠️  Kickstarter 조회 파싱 실패: {e}")

    return research


def generate_blog_drafts(research: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today = datetime.now().strftime("%Y년 %m월 %d일")

    prompt = f"""당신은 '상품 보는 남자' 네이버 블로그 운영자입니다.
해외 소싱 사업자 시각에서 크라우드펀딩 신상품을 소개하는 블로그 포스팅 초안을 작성하세요.

작성일: {today}

조사 자료:
{research}

===

⚠️ URL·이미지 사용 원칙:
조사 자료 하단 "Kickstarter API 직접 조회 결과" 섹션에 있는 캠페인 URL·대표 이미지를 최우선으로 사용하세요.
해당 값이 "확인불가"인 경우에만 Gemini 수집 데이터를 참고하세요.

제품마다 아래 형식으로 작성하세요. 제품 개수(3~5개)만큼 반복.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 [제품명 (한글)]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▶ 캠페인 링크: [URL]
▶ 이미지 URL: [URL 또는 확인불가]

▶ 제목 후보 A (검색형 — 키워드+정보형, 40자 이내):
▶ 제목 후보 B (홈피드형 — 호기심·질문형, 40자 이내):
▶ 제목 활용 안내: 발행 시 위 두 개 중 하나를 메인 제목으로, 나머지는 부제·소제목으로 활용 가능

▶ 본문 (총 1,800~2,200자):

[도입부]
문제 제기 또는 현상 포착으로 시작. 2~3문장. 결론(이 제품이 어떤 사람에게 맞는지)을 도입부 마지막에 한 줄로 예고.

[어떤 물건인가]
브랜드명·제품명·핵심 기능. 기술 구조나 작동 방식까지 포함. 3~5문장.

[누구에게 맞는 물건인가]
맞는 사용자 유형 2~3가지 + 맞지 않는 경우도 솔직히 명시. 각 유형별 이유 포함.

[스펙 요약]
무게·배터리·인증·색상/사이즈 등 핵심 수치. 항목별로 나열.

[가격과 진행 상황]
캠페인가, 정식 예정가, 펀딩 달성률, 현재 참여 가능 여부, 배송 예정 시기.
반드시 포함: 크라우드펀딩은 선주문이지 확정 구매가 아닙니다. 배송 지연·스펙 변경 가능성이 있습니다.

[솔직히 아쉬운 점]
실제 리뷰·알려진 한계점 1~2가지를 솔직하게. 정보가 없으면 "현재까지 알려진 주요 리스크: OO" 형태로.

[마스터 코멘트 입력란]

[마무리]
아래 문구를 그대로 삽입:
이 글은 해외 크라우드펀딩 플랫폼에서 발견한 신제품을 소개하는 정보성 포스팅입니다. 국내 정식 판매처가 없어 구매 링크는 제공하지 않으며, 관심 있으신 분은 제품명으로 직접 검색해 캠페인 페이지에서 최신 진행 상황을 확인하시길 권합니다.

▶ 해시태그: (7개)

───────────────────────────────

조건:
- 화자 포지션: 체험자 아닌 소싱 전문가. 판단 근거는 시장성·가격·수요 데이터
- "써봤다", "써보니" 표현 절대 금지
- 의료·건강 효능 주장 금지
- 구체적 수치(가격·달성률·후원자수·배송 예정일) 반드시 포함
- 마크다운(#, ##, **) 절대 금지
- 순수 텍스트로만 출력"""

    resp = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=16000,
        messages=[{"role": "user", "content": prompt}]
    )
    return next(b.text for b in resp.content if b.type == "text").strip()


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

    print("\n📂 발행 이력 로드 중...")
    history  = load_history()
    excluded = history.get("products", [])
    print(f"   이전 제품 {len(excluded)}개 제외 예정\n")

    print("🔍 Gemini 신상 탐색 중...")
    research = search_products_with_gemini(excluded)
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

    # 이번 회차 제품명 파싱 → 이력 저장
    m = re.search(r"===PRODUCTS===\s*(\[.*?\])\s*===END===", research, re.DOTALL)
    if m:
        try:
            new_products = json.loads(m.group(1))
            print(f"\n📂 이력 저장 중... ({new_products})")
            save_history(history, new_products)
        except Exception as e:
            print(f"  ⚠️  이력 저장 파싱 실패: {e}")

    print("\n✅ 완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
