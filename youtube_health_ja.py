#!/usr/bin/env python3
"""
시니어 건강 채널 - 일본어 대본 자동 생성
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
    {"category": "長寿",   "ja": "110歳を超えた人たちが、静かに続けていた朝の習慣"},
    {"category": "対比",   "ja": "同じ85歳なのに、なぜこの人だけ背筋が伸びているのか"},
    {"category": "暮らし", "ja": "100歳の現役理容師が、60年間やめなかったこと"},
    {"category": "長寿",   "ja": "世界の長寿地域に共通する、たった一つの暮らし方"},
    {"category": "対比",   "ja": "90歳で記憶力が40代の人たちは、何が違ったのか"},
    {"category": "暮らし", "ja": "施設に入らず、自宅で最期まで暮らした人の一日"},
    {"category": "言葉",   "ja": "80歳から始めた人たち。遅すぎることはなかった"},
    {"category": "暮らし", "ja": "一人暮らしの90代が「寂しくない」と言った理由"},
    {"category": "長寿",   "ja": "長生きした人が口を揃えて言う「やらなかったこと」"},
    {"category": "言葉",   "ja": "105歳の医師が、患者に伝え続けた言葉"},
    {"category": "暮らし", "ja": "夫を見送った80代の女性が、その後に始めたこと"},
    {"category": "対比",   "ja": "歳をとっても友人が減らなかった人の共通点"},
    {"category": "長寿",   "ja": "認知症にならなかった人たちの、退屈な毎日"},
    {"category": "言葉",   "ja": "70代で人生が変わったと語る人たちの話"},
    {"category": "対比",   "ja": "老いを受け入れた人と、抗い続けた人の違い"},
    {"category": "言葉",   "ja": "静かに歳を重ねた人が残した、短い言葉"},
]

JA_STYLE = """
## 日本語台本のトーン（必ず守ること）
- 丁寧で品のある敬語（〜ですね、〜ましょう、〜でございます）
- 専門用語は絶対に使わない
- 少し距離感を保ちながらも温かく
- 孤独・孤独死への不安など日本シニア特有の感情を反映
- 主題は「病気」ではなく「人」。病名を軸にしない
- 医学的な診断・治療・助言は一切行わない
- 実在する人物・研究・報道のみを扱い、架空の人物や事例を作らない
- 断定を避け、「〜と報告されています」「〜という研究があります」と出典を示す
- 「迷惑をかけたくない」という心理に寄り添う
- 間接的で繊細な表現
- 季節や自然の表現を活用
- 各シーンは正確に200字前後
- シーンとシーンの間は空白行一つで区切る
- タイトル、小見出し、ハッシュタグ、マークダウン(#, ##, **)絶対禁止
- 純粋な吹き替えテキストのみ
"""

def search_with_gemini(topic: dict) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                f"次のテーマについて、実在する人物と研究に基づいた資料を調査してください: {topic['ja']}\n\n"
                f"1. 該当する実在の人物（超長寿者、高齢の現役者など）の具体的なエピソード\n"
                f"2. 老年学・長寿研究の知見（研究機関名・発表年を必ず明記）\n"
                f"3. 報道・ドキュメンタリーで紹介された実例（媒体名を明記）\n"
                f"4. その人物や集団が実際に続けていた具体的な習慣を9つ以上\n"
                f"5. 日本国内の事例を優先し、なければ海外事例も可\n\n"
                f"【必須】すべての情報に出典（機関名・媒体名・年）を添えること。\n"
                f"【禁止】架空の人物や創作されたエピソードは絶対に含めないこと。\n"
                f"【禁止】病気の治療法や医学的助言は含めないこと。\n"
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

    def call(prompt: str, tokens: int = 1200) -> str:
        resp = client.messages.create(
            model="claude-sonnet-5",
            max_tokens=tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return next(b.text for b in resp.content if b.type == "text").strip()

    base = f"""テーマ: {topic['ja']}
カテゴリー: {topic['category']}
スタイル: {JA_STYLE}
調査資料: {research[:2000]}"""

    rules = """ルール:
- タイトル、小見出し、ハッシュタグ、マークダウン(#, ##, **)絶対禁止
- 純粋な吹き替えテキストのみ
- 各シーン正確に200字前後
- シーンとシーンの間は空白行一つだけ
吹き替えテキストのみ出力。"""

    print("    → フッキングシーン...")
    hooking = call(f"{base}\n[フッキングシーン - 1つ]\n{rules}\nイントロなしで直接感情へ。")

    print("    → 共感シーン...")
    empathy = call(f"{base}\n[共感シーン - 4つ]\n{rules}", 2500)

    print("    → 情報シーン...")
    info = call(f"{base}\n[情報・解決シーン - 9つ]\n{rules}\nその人物・集団が実際に続けていた習慣を9つ。医学的助言ではなく事実の紹介として書くこと。", 6000)

    print("    → 励ましシーン...")
    comfort = call(f"{base}\n[励まし・まとめシーン - 3つ]\n{rules}", 2000)

    print("    → アウトロシーン...")
    outro = call(f"{base}\n[アウトロシーン - 1つ]\n{rules}\n次の動画の予告 + 登録のお願い。")

    print("    → メタデータ...")
    meta = call(f"""テーマ: {topic['ja']}
カテゴリー: {topic['category']}

[YouTubeメタデータ - 以下の形式を全て必ず出力]
※ 全項目に【한국어】韓国語訳を必ず併記すること

▶ 動画タイトル A（感情訴求。40字以内）:
  【한국어】:

▶ 動画タイトル B（情報系。数字含む。40字以内）:
  【한국어】:

▶ サムネイル文言 A
  メイン:（10字以内）
  【한국어】:
  サブ:（15字以内）
  【한국어】:

▶ サムネイル文言 B
  メイン:（10字以内）
  【한국어】:
  サブ:（15字以内）
  【한국어】:

▶ 参考資料（動画説明欄に記載する出典リスト。研究機関名・媒体名・年）:

▶ 動画説明欄:（4〜5行。共感＋内容＋チャンネル紹介＋ハッシュタグ5個）
  【한국어】:

全項目必須。【한국어】병기 빠지면 안 됩니다。""", 3000)

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

def send_email(script: str, subject: str) -> bool:
    lines = script.split("\n")
    formatted = ""
    scene_count = 0
    colors = ["#ffffff", "#f8fafc"]
    for line in lines:
        if line.strip() == "":
            formatted += "<br>"
            scene_count += 1
        elif line.startswith("【") or line.startswith("━") or line.startswith("📋"):
            formatted += f'<div style="font-size:11px;font-weight:800;color:#3A2C21;margin:16px 0 6px;">{line}</div>'
        else:
            bg = colors[scene_count % 2]
            formatted += f'<div style="background:{bg};border-left:3px solid #E8A33D;padding:12px 16px;margin-bottom:2px;font-size:15px;color:#1e293b;line-height:1.9;border-radius:0 6px 6px 0;">{line}</div>'

    html = f"""
<div style="max-width:700px;margin:0 auto;font-family:'Apple SD Gothic Neo','Malgun Gothic',Arial,sans-serif;">
  <div style="background-color:#3A2C21;border-radius:14px;padding:32px;text-align:center;margin-bottom:20px;">
    <div style="font-size:26px;font-weight:900;color:#ffffff;">🌅 ゴールデンヘルパー 롱폼 대본</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:8px;">{datetime.now().strftime('%Y年%m月%d日')}</div>
    <div style="display:inline-block;background-color:#E8A33D;color:#1a1a2e;border-radius:20px;padding:6px 20px;font-size:13px;font-weight:700;margin-top:12px;">🇯🇵 日本語台本</div>
  </div>
  <div style="background-color:#fffbeb;border-left:4px solid #E8A33D;border-radius:0 8px 8px 0;padding:16px 20px;margin-bottom:20px;">
    <div style="font-size:13px;font-weight:800;color:#92400e;margin-bottom:8px;">📌 制作ガイド</div>
    <div style="font-size:13px;color:#1e293b;line-height:1.8;">
      ✅ シーンごとに画像1枚<br>
      ✅ 丁寧で温かいトーンで<br>
      ✅ ゆっくりはっきりと<br>
      ✅ 空白行 = シーン転換
    </div>
  </div>
  <div>{formatted}</div>
  <div style="text-align:center;padding:20px;font-size:12px;color:#94a3b8;">
    🌅 ゴールデンヘルパー | 長く生きた人たちの、静かな習慣
  </div>
</div>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText("シニア健康チャンネル台本", "plain", "utf-8"))
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
    print("🎙️ 시니어 건강 채널 일본어 대본 생성")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)

    week_num    = datetime.now().isocalendar()[1]
    weekday     = datetime.now().weekday()
    slot        = (week_num * 2 + (0 if weekday == 0 else 1)) % len(TOPICS)
    topic       = TOPICS[slot]
    today       = datetime.now().strftime("%Y년 %m월 %d일")
    weekday_str = "월요일" if weekday == 0 else "목요일"

    print(f"\n📅 오늘({weekday_str}) 주제: {topic['ja']}\n")

    print("🔍 Gemini 자료 조사 중...")
    research = search_with_gemini(topic)
    print("   조사 완료\n")

    print("✍️  일본어 대본 작성 중...")
    script = generate_script(topic, research)
    print("   완료\n")

    fname = f"health_ja_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(fname, "w", encoding="utf-8") as f:
        f.write(script)
    print(f"  📄 저장: {fname}\n")

    print("📧 메일 발송 중...")
    send_email(script, f"🎙️ [日本語台本] {topic['ja']} | {today}")

    print("\n✅ 완료!")
    print("=" * 55)

if __name__ == "__main__":
    main()
