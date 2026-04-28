#!/usr/bin/env python3
"""
시니어 건강 채널 대본 자동 생성
매주 월·목 오후 3시 실행

파이프라인:
1. Gemini → 시니어 건강 이슈 서치
2. Claude → 파트별 5회 호출 (한국어)
3. Claude → 파트별 5회 호출 (일본어)
4. Gmail → 한국어·일본어 대본 각각 메일 발송
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

# ─── 주제 풀 (16개 순환) ──────────────────────────────────
TOPICS = [
    {"category": "몸", "ko": "무릎이 시려서 잠 못 자는 밤, 혼자서 할 수 있는 것들", "ja": "膝が冷えて眠れない夜、一人でできること"},
    {"category": "몸", "ko": "넘어질 것 같은 두려움, 집에서 혼자 고치는 방법", "ja": "転びそうな恐怖、自宅でできる改善法"},
    {"category": "마음", "ko": "자식한테 전화하기 미안한 어르신께 드리는 말씀", "ja": "子供に電話するのが申し訳ない、そんな親御さんへ"},
    {"category": "마음", "ko": "혼자 밥 먹는 게 서러운 날을 위한 이야기", "ja": "一人で食事するのが寂しい日のために"},
    {"category": "실용", "ko": "혼자 사는 70대가 꼭 알아야 할 것 5가지", "ja": "一人暮らしの70代が必ず知っておくべき5つのこと"},
    {"category": "실용", "ko": "병원에서 의사한테 꼭 물어봐야 할 것들", "ja": "病院で医師に必ず聞くべきこと"},
    {"category": "위로", "ko": "오래 살아서 미안하다고 하지 마세요", "ja": "長生きして申し訳ないなんて、言わないでください"},
    {"category": "위로", "ko": "나이 드는 게 무서운 게 아닙니다", "ja": "歳をとることは怖いことじゃありません"},
    {"category": "몸", "ko": "밥맛이 없어진 이유, 병원 가기 전에 먼저 확인하세요", "ja": "食欲がなくなった理由、病院の前に確認すること"},
    {"category": "마음", "ko": "친구들이 하나둘 떠나갈 때 마음을 지키는 방법", "ja": "友人が一人一人逝く中で、心を守る方法"},
    {"category": "실용", "ko": "자식한테 폐 안 끼치고 혼자 건강하게 사는 법", "ja": "子供に迷惑をかけず、一人で健康に暮らす方法"},
    {"category": "위로", "ko": "당신이 살아온 것만으로 충분합니다", "ja": "あなたが生きてきたこと、それだけで十分です"},
    {"category": "몸", "ko": "소변이 자꾸 마려운 70대, 창피한 게 아닙니다", "ja": "頻尿に悩む70代へ、恥ずかしいことじゃありません"},
    {"category": "마음", "ko": "내가 짐이 되는 것 같아서 무서운 밤", "ja": "自分が重荷になっているようで怖い夜"},
    {"category": "실용", "ko": "겨울 새벽 화장실 가다 쓰러지는 이유와 예방법", "ja": "冬の早朝、トイレで倒れる理由と予防法"},
    {"category": "위로", "ko": "지금 이 나이가 가장 솔직한 나이입니다", "ja": "今のこの年齢が、最も正直な年齢です"},
]

# ─── 공통 스타일 가이드 ───────────────────────────────────
KO_STYLE = """
## 한국어 대본 톤 (필수 준수)
- 따뜻하고 친근한 경어체 (~하세요, ~하셨나요, ~하시죠)
- 전문용어 절대 금지 → 쉬운 말로
- 마치 오래된 동네 친구가 이야기하듯 편안하게
- 뻔한 상투어 금지 (건강이 최고입니다 X)
- 시청자 감정을 먼저 인정하고 공감
- 구체적이고 생생한 상황 묘사 ("무릎이 욱신욱신 쑤시는 밤" 같은 표현)
- 자식 걱정·효도 문화 반영 ("자녀분들께 폐 끼치기 싫으시죠")
- 직접적이고 실용적인 조언
- 유머와 따뜻함이 공존
- 각 씬은 정확히 200자 내외
- 씬과 씬 사이는 빈 줄 하나로 구분
- 지문·설명 없이 읽을 수 있는 더빙 텍스트만
"""

JA_STYLE = """
## 日本語台本のトーン（必ず守ること）
- 丁寧で品のある敬語（〜ですね、〜ましょう、〜でございます）
- 専門用語は絶対に使わない → 平易な言葉で
- 少し距離感を保ちながらも温かく（韓国語より formal に）
- 紋切り型の言葉は禁止
- 視聴者の気持ちをまず静かに認める（韓国語より控えめに）
- 孤独・孤独死への不安など日本シニア特有の感情を反映
- 「迷惑をかけたくない」という日本人特有の心理に寄り添う
- 間接的で繊細な表現（直接的すぎない）
- 季節や自然の表現を活用（日本文化）
- 各シーンは正確に200字前後
- シーンとシーンの間は空白行一つで区切る
- ト書き・説明なしで読める吹き替えテキストのみ
"""


# ─── 1. Gemini 서치 ───────────────────────────────────────
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
                f"4. 집에서 혼자 할 수 있는 실질적 방법 5가지 이상\n"
                f"5. 일본 시니어 관련 정보도 포함\n"
            ),
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        return resp.text
    except Exception as e:
        print(f"  ⚠️  Gemini 서치 실패: {e}")
        return ""


# ─── 2. 파트별 대본 생성 (한국어) ────────────────────────
def generate_korean_script(topic: dict, research: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def call(part_prompt: str, tokens: int = 1000) -> str:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=tokens,
            messages=[{"role": "user", "content": part_prompt}]
        )
        return resp.content[0].text.strip()

    base = f"""
주제: {topic['ko']}
카테고리: {topic['category']}
스타일: {KO_STYLE}
조사자료: {research[:2000]}
"""

    print("    → 후킹 씬 작성...")
    hooking = call(f"""{base}
[후킹 씬 작성]
영상 첫 5초 안에 시청자의 심장을 찌르는 한 마디로 시작하세요.
인트로 없이 바로 핵심 감정으로 들어갑니다.
"혹시 이런 적 있으셨나요?" 또는 충격적인 사실로 시작.
정확히 200자 내외. 씬 1개만.
더빙 텍스트만 출력.""")

    print("    → 공감 씬 작성...")
    empathy = call(f"""{base}
[공감 씬 작성 - 3개]
시청자가 겪는 상황을 구체적으로 묘사하는 씬 3개.
각 씬은 정확히 200자 내외.
씬과 씬 사이 빈 줄 하나.
"이런 적 있으셨나요?", "그 마음 당연한 겁니다" 같은 공감 표현.
혼자만 겪는 게 아님을 알려주기.
더빙 텍스트만 출력.""", 1500)

    print("    → 정보 씬 작성...")
    info = call(f"""{base}
[정보·해결 씬 작성 - 6개]
집에서 혼자 할 수 있는 실질적 방법 6가지를 각각 씬으로.
각 씬은 정확히 200자 내외.
씬과 씬 사이 빈 줄 하나.
번호 없이 자연스럽게 이어지도록.
왜 효과있는지 쉽게 설명. 주의사항 포함.
더빙 텍스트만 출력.""", 3000)

    print("    → 위로 씬 작성...")
    comfort = call(f"""{base}
[위로·마무리 씬 작성 - 2개]
진심 어린 위로와 응원 씬 2개.
각 씬은 정확히 200자 내외.
씬과 씬 사이 빈 줄 하나.
"오늘 하루도 잘 버티셨습니다" 같은 따뜻한 마무리.
더빙 텍스트만 출력.""", 1000)

    print("    → 아웃트로 씬 작성...")
    outro = call(f"""{base}
[아웃트로 씬 작성 - 1개]
다음 영상 예고 + 구독·좋아요 부탁 (부담없이).
정확히 200자 내외. 씬 1개만.
더빙 텍스트만 출력.""")

    print("    → 메타데이터 작성...")
    meta = call(f"""{base}
[유튜브 메타데이터 작성]
반드시 아래 형식 그대로 빠짐없이 출력하세요.

▶ 영상 제목 A (클릭하고 싶은 제목. 감정 자극. 40자 이내):
▶ 영상 제목 B (정보성 제목. 숫자 포함. 40자 이내):

▶ 썸네일 문구 A
  메인: (크게 들어가는 핵심 문구. 10자 이내. 감정적)
  서브: (작게 들어가는 보조 문구. 15자 이내)

▶ 썸네일 문구 B
  메인: (다른 버전 핵심 문구. 10자 이내)
  서브: (보조 문구. 15자 이내)

▶ 영상 설명란:
(3~5줄. 이 영상에서 다루는 내용 + 공감 한마디 + 채널 소개.
SEO 키워드 자연스럽게 포함. 해시태그 5개 포함)

※ 위 항목 중 하나라도 빠지면 안 됩니다. 반드시 전부 작성하세요.""", 1500)

    # 합치기
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


# ─── 3. 파트별 대본 생성 (일본어) ────────────────────────
def generate_japanese_script(topic: dict, research: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def call(part_prompt: str, tokens: int = 1000) -> str:
        resp = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=tokens,
            messages=[{"role": "user", "content": part_prompt}]
        )
        return resp.content[0].text.strip()

    base = f"""
テーマ: {topic['ja']}
カテゴリー: {topic['category']}
スタイル: {JA_STYLE}
調査資料: {research[:2000]}
"""

    print("    → フッキングシーン作成...")
    hooking = call(f"""{base}
[フッキングシーン作成]
動画最初の5秒で視聴者の心をつかむ一言から始めてください。
イントロなしで直接核心の感情へ。
「こんなことはありませんでしたか？」または衝撃的な事実から始める。
正確に200字前後。シーン1つだけ。
吹き替えテキストのみ出力。""")

    print("    → 共感シーン作成...")
    empathy = call(f"""{base}
[共感シーン作成 - 3つ]
視聴者が経験する状況を具体的に描写するシーン3つ。
各シーンは正確に200字前後。
シーンとシーンの間は空白行一つ。
「こんなことはありませんでしたか？」などの共感表現。
一人だけの経験ではないことを伝える。
吹き替えテキストのみ出力。""", 1500)

    print("    → 情報シーン作成...")
    info = call(f"""{base}
[情報・解決シーン作成 - 6つ]
自宅で一人でできる実践的な方法6つを各シーンで。
各シーンは正確に200字前後。
シーンとシーンの間は空白行一つ。
番号なしで自然につながるように。
効果がある理由をわかりやすく説明。注意点も含める。
吹き替えテキストのみ出力。""", 3000)

    print("    → 励ましシーン作成...")
    comfort = call(f"""{base}
[励まし・まとめシーン作成 - 2つ]
心からの励ましと応援シーン2つ。
各シーンは正確に200字前後。
シーンとシーンの間は空白行一つ。
「今日も一日、よく頑張られました」のような温かいまとめ。
吹き替えテキストのみ出力。""", 1000)

    print("    → アウトロシーン作成...")
    outro = call(f"""{base}
[アウトロシーン作成 - 1つ]
次の動画の予告 + 登録・高評価のお願い（さりげなく）。
正確に200字前後。シーン1つだけ。
吹き替えテキストのみ出力。""")

    print("    → メタデータ作成...")
    meta = call(f"""{base}
[YouTubeメタデータ作成]
以下の形式そのまま出力してください。
日本語の後に必ず韓国語訳を【한국어】として併記してください。

▶ 動画タイトル A（クリックしたくなるタイトル。感情訴求。40字以内）:
  【한국어】:

▶ 動画タイトル B（情報系タイトル。数字含む。40字以内）:
  【한국어】:

▶ サムネイル文言 A
  メイン:（大きく入る核心フレーズ。10字以内。感情的）
  【한국어】:
  サブ:（小さく入る補助フレーズ。15字以内）
  【한국어】:

▶ サムネイル文言 B
  メイン:（別バージョン核心フレーズ。10字以内）
  【한국어】:
  サブ:（補助フレーズ。15字以内）
  【한국어】:

▶ 動画説明欄:
（3〜5行。この動画で扱う内容＋共感一言＋チャンネル紹介。
SEOキーワード自然に含む。ハッシュタグ5個含む）
  【한국어】:

※ 위 모든 항목에 반드시 【한국어】 병기를 작성하세요. 빠지면 안 됩니다.""", 1500)

    full = f"""【フッキング】
{hooking}

【共感】
{empathy}

【情報・解決】
{info}

【励まし】
{comfort}

【アウトロ】
{outro}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 YouTubeメタデータ（＋한국어 병기）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{meta}"""

    total = len(full.replace(" ", "").replace("\n", "").replace("　", ""))
    print(f"    → 総文字数: {total}字")
    return full


# ─── 4. 메일 발송 ─────────────────────────────────────────
def send_email(script: str, subject: str, lang: str) -> bool:
    if lang == "ko":
        header_color = "#1a3a6b"
        badge_text   = "🇰🇷 한국어 대본"
        guide_items  = "✅ 씬마다 이미지 1장 배치<br>✅ 따뜻하고 친근한 톤으로<br>✅ 천천히 또박또박<br>✅ 빈 줄 = 씬 전환"
    else:
        header_color = "#0f2744"
        badge_text   = "🇯🇵 日本語台本"
        guide_items  = "✅ シーンごとに画像1枚<br>✅ 丁寧で温かいトーンで<br>✅ ゆっくりはっきりと<br>✅ 空白行 = シーン転換"

    # 씬별 배경색 교대
    lines = script.split("\n")
    formatted = ""
    scene_count = 0
    colors = ["#ffffff", "#f8fafc"]
    for line in lines:
        if line.strip() == "":
            formatted += "<br>"
            scene_count += 1
        elif line.startswith("[") or line.startswith("【"):
            formatted += f'<div style="font-size:11px;font-weight:800;color:#6366f1;margin:16px 0 6px;">{line}</div>'
        else:
            bg = colors[scene_count % 2]
            formatted += f'<div style="background:{bg};border-left:3px solid #e2b04a;padding:12px 16px;margin-bottom:2px;font-size:15px;color:#1e293b;line-height:1.9;border-radius:0 6px 6px 0;">{line}</div>'

    html = f"""
<div style="max-width:700px;margin:0 auto;font-family:'Apple SD Gothic Neo','Malgun Gothic',Arial,sans-serif;">
  <div style="background-color:{header_color};border-radius:14px;padding:32px;text-align:center;margin-bottom:20px;">
    <div style="font-size:26px;font-weight:900;color:#ffffff;">🎙️ 시니어 건강 채널 대본</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:8px;">{datetime.now().strftime('%Y년 %m월 %d일')}</div>
    <div style="display:inline-block;background-color:#e2b04a;color:#1a1a2e;border-radius:20px;padding:6px 20px;font-size:13px;font-weight:700;margin-top:12px;">{badge_text}</div>
  </div>
  <div style="background-color:#fffbeb;border-left:4px solid #e2b04a;border-radius:0 8px 8px 0;padding:16px 20px;margin-bottom:20px;">
    <div style="font-size:13px;font-weight:800;color:#92400e;margin-bottom:8px;">📌 제작 가이드</div>
    <div style="font-size:13px;color:#1e293b;line-height:1.8;">{guide_items}</div>
  </div>
  <div>{formatted}</div>
  <div style="text-align:center;padding:20px;font-size:12px;color:#94a3b8;margin-top:16px;">
    🎙️ 시니어 건강 채널 | Powered by Gemini + Claude
  </div>
</div>
"""

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


# ─── 메인 ─────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("🎙️ 시니어 건강 채널 대본 생성 시작")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    week_num    = datetime.now().isocalendar()[1]
    weekday     = datetime.now().weekday()
    slot        = (week_num * 2 + (0 if weekday == 0 else 1)) % len(TOPICS)
    topic       = TOPICS[slot]
    today       = datetime.now().strftime("%Y년 %m월 %d일")
    weekday_str = "월요일" if weekday == 0 else "목요일"

    print(f"\n📅 오늘({weekday_str}) 주제: {topic['ko']}\n")

    # 1. Gemini 서치
    print("🔍 Gemini 자료 조사 중...")
    research = search_with_gemini(topic)
    print("   조사 완료\n")

    # 2. 한국어 대본 (파트별 5회 호출)
    print("✍️  한국어 대본 작성 중... (파트별 생성)")
    ko_script = generate_korean_script(topic, research)
    print("   완료\n")

    # 3. 일본어 대본 (파트별 5회 호출)
    print("✍️  일본어 대본 작성 중... (파트별 생성)")
    ja_script = generate_japanese_script(topic, research)
    print("   완료\n")

    # 4. 저장
    for lang, script in [("ko", ko_script), ("ja", ja_script)]:
        fname = f"health_{lang}_{datetime.now().strftime('%Y%m%d')}.txt"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(script)
        print(f"  📄 저장: {fname}")

    # 5. 메일 발송
    print("\n📧 메일 발송 중...")
    send_email(ko_script, f"🎙️ [한국어 대본] {topic['ko']} | {today}", "ko")
    send_email(ja_script, f"🎙️ [日本語台本] {topic['ja']} | {today}", "ja")

    print("\n✅ 완료!")
    print("=" * 55)


if __name__ == "__main__":
    main()
