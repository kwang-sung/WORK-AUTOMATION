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
    {"category": "몸", "ko": "무릎이 시려서 잠 못 자는 밤", "ja": "膝が冷えて眠れない夜、一人でできること"},
    {"category": "몸", "ko": "넘어질 것 같은 두려움", "ja": "転びそうな恐怖、自宅でできる改善法"},
    {"category": "마음", "ko": "자식한테 전화하기 미안한 어르신", "ja": "子供に電話するのが申し訳ない、そんな親御さんへ"},
    {"category": "마음", "ko": "혼자 밥 먹는 게 서러운 날", "ja": "一人で食事するのが寂しい日のために"},
    {"category": "실용", "ko": "혼자 사는 70대가 꼭 알아야 할 것", "ja": "一人暮らしの70代が必ず知っておくべき5つのこと"},
    {"category": "실용", "ko": "병원에서 의사한테 꼭 물어봐야 할 것들", "ja": "病院で医師に必ず聞くべきこと"},
    {"category": "위로", "ko": "오래 살아서 미안하다고 하지 마세요", "ja": "長生きして申し訳ないなんて、言わないでください"},
    {"category": "위로", "ko": "나이 드는 게 무서운 게 아닙니다", "ja": "歳をとることは怖いことじゃありません"},
    {"category": "몸", "ko": "밥맛이 없어진 이유", "ja": "食欲がなくなった理由、病院の前に確認すること"},
    {"category": "마음", "ko": "친구들이 하나둘 떠나갈 때", "ja": "友人が一人一人逝く中で、心を守る方法"},
    {"category": "실용", "ko": "자식한테 폐 안 끼치고 혼자 건강하게", "ja": "子供に迷惑をかけず、一人で健康に暮らす方法"},
    {"category": "위로", "ko": "당신이 살아온 것만으로 충분합니다", "ja": "あなたが生きてきたこと、それだけで十分です"},
    {"category": "몸", "ko": "소변이 자꾸 마려운 70대", "ja": "頻尿に悩む70代へ、恥ずかしいことじゃありません"},
    {"category": "마음", "ko": "내가 짐이 되는 것 같아서 무서운 밤", "ja": "自分が重荷になっているようで怖い夜"},
    {"category": "실용", "ko": "겨울 새벽 화장실 가다 쓰러지는 이유", "ja": "冬の早朝、トイレで倒れる理由と予防法"},
    {"category": "위로", "ko": "지금 이 나이가 가장 솔직한 나이", "ja": "今のこの年齢が、最も正直な年齢です"},
]

JA_STYLE = """
## 日本語台本のトーン（必ず守ること）
- 丁寧で品のある敬語（〜ですね、〜ましょう、〜でございます）
- 専門用語は絶対に使わない
- 少し距離感を保ちながらも温かく
- 孤独・孤独死への不安など日本シニア特有の感情を反映
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
                f"70代以上のシニア向けに次のテーマで最新情報を調査してください: {topic['ja']}\n\n"
                f"1. 関連する最新の医学・心理研究や統計\n"
                f"2. 専門家のアドバイス\n"
                f"3. 実際のシニアが経験する具体的な状況\n"
                f"4. 自宅で一人でできる実践的な方法9つ以上\n"
                f"5. 日本のシニア特有の状況も含めて\n"
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
            model="claude-sonnet-4-5",
            max_tokens=tokens,
            messages=[{"role": "user", "content": prompt}]
        )
        return resp.content[0].text.strip()

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
    info = call(f"{base}\n[情報・解決シーン - 9つ]\n{rules}\n自宅で一人でできる方法9つ。", 6000)

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
            formatted += f'<div style="font-size:11px;font-weight:800;color:#0f2744;margin:16px 0 6px;">{line}</div>'
        else:
            bg = colors[scene_count % 2]
            formatted += f'<div style="background:{bg};border-left:3px solid #e2b04a;padding:12px 16px;margin-bottom:2px;font-size:15px;color:#1e293b;line-height:1.9;border-radius:0 6px 6px 0;">{line}</div>'

    html = f"""
<div style="max-width:700px;margin:0 auto;font-family:'Apple SD Gothic Neo','Malgun Gothic',Arial,sans-serif;">
  <div style="background-color:#0f2744;border-radius:14px;padding:32px;text-align:center;margin-bottom:20px;">
    <div style="font-size:26px;font-weight:900;color:#ffffff;">🎙️ シニア健康チャンネル台本</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:8px;">{datetime.now().strftime('%Y年%m月%d日')}</div>
    <div style="display:inline-block;background-color:#e2b04a;color:#1a1a2e;border-radius:20px;padding:6px 20px;font-size:13px;font-weight:700;margin-top:12px;">🇯🇵 日本語台本</div>
  </div>
  <div style="background-color:#fffbeb;border-left:4px solid #e2b04a;border-radius:0 8px 8px 0;padding:16px 20px;margin-bottom:20px;">
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
    🎙️ シニア健康チャンネル | Powered by Gemini + Claude
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
