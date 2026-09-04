#!/usr/bin/env python3
"""
상품 보는 남자 - 해외 신상 발굴 (킥스타터) 자동화 v2
매주 월·목 오후 3시 실행
Gemini 신상 발굴 → Claude 블로그 초안(2개) + 마스터 코멘트 자동생성 → 이메일 발송
"""

import os
import re
import io
import json
import time
import base64
import random
import smtplib
import requests
import anthropic
from google import genai
from google.genai import types
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# ─── 면책 문구 로테이션 ───────────────────────────────────
DISCLAIMER_VERSIONS = [
    "이 글은 해외 크라우드펀딩 플랫폼에서 발견한 신제품을 소개하는 정보성 포스팅입니다. "
    "국내 정식 판매처가 없어 구매 링크는 제공하지 않으며, 관심 있으신 분은 제품명으로 "
    "직접 검색해 캠페인 페이지에서 최신 진행 상황을 확인하시길 권합니다.",

    "국내 정식 판매처가 아직 없는 상품이라 참고용으로 정리했습니다. 크라우드펀딩 특성상 "
    "배송 지연이나 스펙 변경이 생길 수 있으니, 실제 구매 전 캠페인 페이지에서 최신 정보를 "
    "직접 확인하세요.",

    "해외 크라우드펀딩 신상 소개 코너입니다. 구매 링크는 따로 제공하지 않으며, "
    "관심 있는 분은 제품명으로 검색해 캠페인 페이지에서 현황을 확인하시기 바랍니다.",
]

# ─── 마스터 코멘트 관점 풀 ───────────────────────────────
COMMENT_PERSPECTIVES = [
    "국내 통관/관세/인증(KC 등) 관점에서의 실무적 시사점",
    "국내 유사 카테고리 시장 규모나 경쟁 구도에 대한 판단",
    "해외 소싱 실무에서 자주 보는 배송·물류 리스크와의 비교",
    "이 상품이 국내에 들어온다면 예상되는 반응이나 걸림돌",
    "스펙/가격 대비 실제 실용성에 대한 실무자 시각의 짧은 평가",
]

# ─── 발행 이력 관리 ──────────────────────────────────────
def load_history() -> dict:
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return {"products": [], "perspectives_used": []}
    try:
        gh = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        r = requests.get(f"https://api.github.com/repos/{GITHUB_REPO}/contents/{HISTORY_FILE}", headers=gh)
        if r.status_code == 200:
            return json.loads(base64.b64decode(r.json()["content"]).decode("utf-8"))
    except Exception as e:
        print(f"  ⚠️  이력 로드 실패: {e}")
    return {"products": [], "perspectives_used": []}


def save_history(history: dict, new_products: list, perspectives_used: list):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    history["products"]           = (history.get("products", []) + new_products)[-60:]
    history["perspectives_used"]  = (history.get("perspectives_used", []) + perspectives_used)[-10:]
    history["last_sent"]          = datetime.now().strftime("%Y-%m-%d")
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
                "최근 2~4주 내 주목받는 신상 제품을 정확히 2개만 발굴해줘.\n\n"
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
                "수치는 확인된 것만. 추정이면 (추정)으로 표시."
                + exclude_block +
                "\n\n마지막에 반드시 아래 블록 추가 (각 제품의 영문명·구글 검색으로 확인한 실제 캠페인 URL·플랫폼, JSON 배열):\n"
                "===PRODUCTS===\n"
                "[{\"name\": \"영문제품명1\", \"url\": \"https://실제URL\", \"platform\": \"kickstarter\"}, "
                "{\"name\": \"영문제품명2\", \"url\": \"https://실제URL\", \"platform\": \"indiegogo\"}]\n"
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

    m = re.search(r"===PRODUCTS===\s*(\[.*?\])\s*===END===", research, re.DOTALL)
    if m:
        try:
            products = json.loads(m.group(1))
            lines = ["\n\n─── 캠페인 URL 목록 (Claude는 이 값을 최우선 사용) ───"]
            for p in products:
                name = p.get("name", "") if isinstance(p, dict) else p
                url  = p.get("url",  "확인불가") if isinstance(p, dict) else "확인불가"
                short = url[:70] if url != "확인불가" else "확인불가"
                print(f"    🔗 [{name}] {short}")
                lines.append(f"\n제품명: {name}")
                lines.append(f"  캠페인 URL: {url}")
            research += "\n".join(lines)
        except Exception as e:
            print(f"  ⚠️  제품 파싱 실패: {e}")

    return research


def download_og_image(url: str, product_name: str) -> tuple[bytes | None, str]:
    """캠페인 URL에서 og:image 다운로드. 성공 시 (bytes, 캡션) 반환."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](https?://[^"\']+)["\']', r.text)
        if not m:
            m = re.search(r'<meta[^>]+content=["\'](https?://[^"\']+)["\'][^>]+property=["\']og:image["\']', r.text)
        if not m:
            return None, ""
        img_url = m.group(1)
        img_r = requests.get(img_url, headers=headers, timeout=10)
        img_r.raise_for_status()
        caption = f"이미지 출처: {product_name} 공식 캠페인 페이지"
        print(f"    🖼️  이미지 다운로드 완료: {img_url[:60]}...")
        return img_r.content, caption
    except Exception as e:
        print(f"    ⚠️  이미지 다운로드 실패: {e}")
        return None, ""


def pick_perspectives(history: dict, count: int = 2) -> list[str]:
    """이전에 적게 쓴 관점 우선으로 선택."""
    used = history.get("perspectives_used", [])
    pool = COMMENT_PERSPECTIVES.copy()
    random.shuffle(pool)
    pool.sort(key=lambda p: used.count(p))
    selected = []
    for p in pool:
        if p not in selected:
            selected.append(p)
        if len(selected) == count:
            break
    return selected


def generate_blog_drafts(research: str, perspectives: list[str]) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    today  = datetime.now().strftime("%Y년 %m월 %d일")

    disclaimer = random.choice(DISCLAIMER_VERSIONS)
    persp_text = "\n".join(f"  - 제품{i+1}: {p}" for i, p in enumerate(perspectives))

    prompt = f"""당신은 '상품 보는 남자' 네이버 블로그 운영자입니다.
해외 소싱 경력 15년차 전문가 시각에서 크라우드펀딩 신상품 2개를 각각 별도 게시글로 소개합니다.

작성일: {today}

조사 자료:
{research}

===

⚠️ URL 사용 원칙:
조사 자료 하단 "캠페인 URL 목록" 섹션의 URL을 반드시 캠페인 링크에 사용하세요.
이미지는 시스템이 자동 다운로드하므로 이미지 관련 안내 문구는 생략하세요.

제품 2개에 대해 아래 형식으로 각각 작성하세요.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 [제품명 (한글)]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

▶ 캠페인 링크: [URL — 조사 자료 하단 "캠페인 URL 목록"의 값 사용]

▶ 제목 후보 A (검색형 — 키워드+정보형, 40자 이내):
▶ 제목 후보 B (홈피드형 — 호기심·질문형, 40자 이내):

▶ 본문 (총 1,200~1,600자):

[도입부]
문제 제기 또는 현상 포착으로 시작. 2~3문장. 결론(이 제품이 어떤 사람에게 맞는지)을 도입부 마지막에 한 줄로 예고.

[어떤 물건인가]
브랜드명·제품명·핵심 기능. 기술 구조나 작동 방식까지 포함. 3~4문장.

[누구에게 맞는 물건인가]
맞는 사용자 유형 2가지 + 맞지 않는 경우도 솔직히 명시.

[스펙 요약]
무게·배터리·인증·색상/사이즈 등 핵심 수치. 항목별로 나열.

[가격과 진행 상황]
캠페인가, 펀딩 달성률, 현재 참여 가능 여부, 배송 예정 시기.
반드시 포함: 크라우드펀딩은 선주문이지 확정 구매가 아닙니다. 배송 지연·스펙 변경 가능성이 있습니다.

[솔직히 아쉬운 점]
알려진 한계점 1~2가지. 정보가 없으면 "현재까지 알려진 주요 리스크: OO" 형태로.

[마스터 코멘트]
아래 지시대로 반드시 직접 작성 (빈칸 금지):
{persp_text}

관점에 맞게 소싱 경력 15년차 전문가 시각으로 1~2문장. 실무 정보·판단을 담을 것.
금지: "좋아 보입니다", "관심이 갑니다" 류의 감상형 / 본문 요약 반복 / 두 제품 동일 어투

[마무리]
아래 문구를 정확히 그대로 삽입:
{disclaimer}

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
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}]
    )
    return next((b.text for b in resp.content if b.type == "text"), "").strip()


def send_email(drafts: str, research: str, images: list[tuple[bytes, str, str]]) -> bool:
    """images: [(bytes, caption, product_name), ...]"""
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
        elif stripped.startswith("[마스터 코멘트]"):
            formatted += f'<div style="background-color:#f0fdf4;border-left:4px solid #22c55e;border-radius:0 8px 8px 0;padding:12px 16px;margin:10px 0;font-size:14px;color:#166534;font-weight:600;">{stripped}</div>'
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

    # 이미지 섹션
    img_section = ""
    for _, caption, pname in images:
        img_section += f'<div style="font-size:12px;color:#64748b;margin:4px 0;">📷 {pname} 대표 이미지 첨부됨 — {caption}</div>'

    research_preview = research[:2000].replace("<", "&lt;").replace(">", "&gt;")

    html = f"""
<div style="max-width:700px;margin:0 auto;font-family:'Apple SD Gothic Neo','Malgun Gothic',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:20px;">
  <tr><td style="background-color:#0f172a;border-radius:14px;padding:32px;text-align:center;">
    <div style="font-size:26px;font-weight:900;color:#ffffff;">상품 보는 남자</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:8px;">해외 신상 발굴 리포트 · Kickstarter / Indiegogo</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:4px;">{today} ({weekday_str}) · 이번 회차 2개</div>
    <div style="display:inline-block;background-color:#f59e0b;color:#1a1a2e;border-radius:20px;padding:6px 20px;font-size:13px;font-weight:700;margin-top:12px;">🌐 해외 신상 발굴 v2</div>
  </td></tr>
  </table>

  {f'<table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:16px;"><tr><td style="background-color:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:12px 16px;"><div style="font-size:13px;font-weight:700;color:#166534;margin-bottom:4px;">🖼️ 첨부 이미지</div>{img_section}</td></tr></table>' if img_section else ''}

  <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-bottom:20px;">
  <tr><td style="background-color:#fef2f2;border-left:4px solid #ef4444;border-radius:0 8px 8px 0;padding:16px 20px;">
    <div style="font-size:13px;font-weight:800;color:#991b1b;margin-bottom:8px;">📋 발행 전 체크리스트</div>
    <div style="font-size:13px;color:#1e293b;line-height:1.9;">
      ☐ 제목 전체를 네이버에 검색 → 통합검색·블로그탭 노출 여부 확인<br>
      ☐ 첨부 이미지 확인 후 블로그에 업로드<br>
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
    상품 보는 남자 | Powered by Gemini + Claude v2
  </div>
</div>"""

    subject = f"🌐 [신상발굴] 해외 크라우드펀딩 신상품 2선 | {today}"

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText("상품 보는 남자 - 해외 신상 발굴 리포트 v2", "plain", "utf-8"))
    alt.attach(MIMEText(html, "html", "utf-8"))
    msg.attach(alt)

    for img_bytes, caption, pname in images:
        img_part = MIMEImage(img_bytes)
        safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", pname)[:30]
        img_part.add_header("Content-Disposition", "attachment", filename=f"{safe_name}.jpg")
        img_part.add_header("Content-Description", caption)
        msg.attach(img_part)

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
    print("🌐 상품 보는 남자 - 신상 발굴 시작 v2")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    print("\n📂 발행 이력 로드 중...")
    history  = load_history()
    excluded = history.get("products", [])
    print(f"   이전 제품 {len(excluded)}개 제외 예정\n")

    # 마스터 코멘트 관점 선택 (이전에 덜 쓴 것 우선)
    perspectives = pick_perspectives(history, count=2)
    print(f"   📌 이번 회 코멘트 관점: {', '.join(perspectives[:1])[:40]}...\n")

    print("🔍 Gemini 신상 탐색 중 (2개 발굴)...")
    research = search_products_with_gemini(excluded)
    if not research.strip():
        print("\n🚨 Gemini 검색 실패 — 발행 중단")
        raise SystemExit(1)
    print("   탐색 완료\n")

    # 캠페인 URL 파싱 → 이미지 다운로드
    images = []
    m = re.search(r"===PRODUCTS===\s*(\[.*?\])\s*===END===", research, re.DOTALL)
    if m:
        try:
            products = json.loads(m.group(1))
            print("🖼️  캠페인 이미지 다운로드 중...")
            for p in products[:2]:
                pname = p.get("name", "product") if isinstance(p, dict) else str(p)
                purl  = p.get("url", "") if isinstance(p, dict) else ""
                if purl.startswith("http"):
                    img_bytes, caption = download_og_image(purl, pname)
                    if img_bytes:
                        images.append((img_bytes, caption, pname))
            print(f"   {len(images)}개 이미지 첨부 예정\n")
        except Exception as e:
            print(f"  ⚠️  이미지 파싱 실패: {e}\n")

    print("✍️  Claude 블로그 초안 작성 중 (2개 개별 게시글)...")
    drafts = generate_blog_drafts(research, perspectives)
    print("   완료\n")

    fname = f"kickstarter_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(drafts)
    print(f"  📄 저장: {fname}\n")

    print("📧 메일 발송 중...")
    send_email(drafts, research, images)

    # 이력 저장
    if m:
        try:
            data = json.loads(m.group(1))
            new_products = [p["name"] if isinstance(p, dict) else p for p in data]
            print(f"\n📂 이력 저장 중... {new_products}")
            save_history(history, new_products, perspectives)
        except Exception as e:
            print(f"  ⚠️  이력 저장 파싱 실패: {e}")

    print("\n✅ 완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
