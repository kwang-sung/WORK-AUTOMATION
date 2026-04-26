# ─── 배너 HTML 상수 ────────────────────────────────────────
# newsletter.py 와 purchasing_insight.py 에서 공통 사용

# ── 쿠대 프로그램 배너 (카페용 - 심플) ───────────────────
BANNER_COUDAE_SIMPLE = """
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0;background-color:#fffbeb;border:1px solid #fcd34d;border-left:4px solid #e2b04a;border-radius:10px;">
  <tr>
    <td style="padding:14px 18px;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="vertical-align:middle;">
            <span style="display:inline-block;background-color:#e2b04a;color:#1a1a2e;border-radius:4px;padding:2px 7px;font-size:10px;font-weight:800;">FREE</span>
            <span style="font-size:14px;font-weight:800;color:#1e293b;margin-left:8px;">쿠대 프로그램 — 지금 무료로 시작하세요</span>
            <div style="font-size:11px;color:#64748b;margin-top:3px;">구매대행 자동화의 시작 · 누적회원 15,900명</div>
          </td>
          <td style="vertical-align:middle;text-align:right;white-space:nowrap;padding-left:16px;">
            <a href="https://admin.coudae.kr/#/login" style="display:inline-block;background-color:#e2b04a;color:#1a1a2e;border-radius:6px;padding:8px 16px;font-size:12px;font-weight:800;text-decoration:none;">무료 시작 →</a>
            <div style="font-size:10px;color:#94a3b8;margin-top:4px;">💬 좌측 하단 말풍선 문의</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
"""

# ── 쿠대 프로그램 배너 (블로그용 - 다크) ─────────────────
BANNER_COUDAE_DARK = """
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0;background-color:#0f172a;border-radius:12px;border:1px solid #334155;">
  <tr>
    <td style="padding:18px 22px;">
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="vertical-align:middle;width:44px;">
            <div style="width:40px;height:40px;background-color:#6366f1;border-radius:10px;text-align:center;line-height:40px;font-size:18px;">🤖</div>
          </td>
          <td style="vertical-align:middle;padding-left:14px;">
            <div style="font-size:15px;font-weight:800;color:#ffffff;">쿠대 — 구매대행 자동화 프로그램</div>
            <div style="font-size:11px;color:#94a3b8;margin-top:3px;">상품 등록·가격 모니터링·주문 관리 자동화 · 누적회원 15,900명</div>
          </td>
          <td style="vertical-align:middle;text-align:right;white-space:nowrap;padding-left:16px;">
            <a href="https://admin.coudae.kr/#/login" style="display:inline-block;background-color:#6366f1;color:#ffffff;border-radius:8px;padding:10px 18px;font-size:12px;font-weight:800;text-decoration:none;">무료로 시작하기 →</a>
            <div style="font-size:10px;color:#64748b;margin-top:4px;">💬 좌측 하단 말풍선 문의</div>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
"""

# ── SNS 공식채널 (한 행 배치) ─────────────────────────────
BANNER_SNS = """
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0;">
  <tr>
    <td>
      <div style="font-size:12px;font-weight:800;color:#1e293b;margin-bottom:12px;">🔗 쿠대 공식채널 바로가기</div>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td width="25%" style="text-align:center;padding:0 4px;">
            <a href="https://www.youtube.com/@coudae" style="text-decoration:none;display:block;">
              <div style="width:36px;height:36px;background-color:#cc0000;border-radius:8px;text-align:center;line-height:36px;font-size:14px;font-weight:800;color:#ffffff;margin:0 auto;">▶</div>
              <div style="font-size:12px;font-weight:700;color:#1e293b;margin-top:5px;">유튜브</div>
            </a>
          </td>
          <td width="25%" style="text-align:center;padding:0 4px;">
            <a href="https://cafe.naver.com/coudae" style="text-decoration:none;display:block;">
              <div style="width:36px;height:36px;background-color:#03c75a;border-radius:8px;text-align:center;line-height:36px;font-size:14px;font-weight:800;color:#ffffff;margin:0 auto;">N</div>
              <div style="font-size:12px;font-weight:700;color:#1e293b;margin-top:5px;">네이버 카페</div>
            </a>
          </td>
          <td width="25%" style="text-align:center;padding:0 4px;">
            <a href="https://open.kakao.com/o/gKWnrBDg" style="text-decoration:none;display:block;">
              <div style="width:36px;height:36px;background-color:#fee500;border-radius:8px;text-align:center;line-height:36px;font-size:16px;margin:0 auto;">💬</div>
              <div style="font-size:12px;font-weight:700;color:#1e293b;margin-top:5px;">단톡방</div>
            </a>
          </td>
          <td width="25%" style="text-align:center;padding:0 4px;">
            <a href="https://www.threads.com/@coudae_official" style="text-decoration:none;display:block;">
              <div style="width:36px;height:36px;background-color:#0f172a;border-radius:8px;text-align:center;line-height:36px;font-size:13px;font-weight:800;color:#ffffff;margin:0 auto;">@</div>
              <div style="font-size:12px;font-weight:700;color:#1e293b;margin-top:5px;">스레드</div>
            </a>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
"""
