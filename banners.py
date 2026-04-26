# ─── 배너 HTML 상수 ────────────────────────────────────────
# purchasing_insight.py 와 newsletter.py 에서 공통 사용

BANNER_COUDAE_DARK = """
<div style="background-color:#0f172a;border-radius:14px;padding:24px 28px;display:flex;align-items:center;justify-content:space-between;gap:16px;border:1px solid #334155;margin:24px 0;">
  <div style="width:44px;height:44px;background-color:#6366f1;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;">🤖</div>
  <div style="flex:1;">
    <div style="font-size:16px;font-weight:800;color:#ffffff;">쿠대 — 구매대행 자동화 프로그램</div>
    <div style="font-size:12px;color:#94a3b8;margin-top:4px;">상품 등록·가격 모니터링·주문 관리 자동화 · 누적회원 15,900명</div>
  </div>
  <div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end;">
    <a href="https://admin.coudae.kr/#/login" style="background-color:#6366f1;color:#ffffff;border-radius:8px;padding:10px 20px;font-size:13px;font-weight:800;white-space:nowrap;text-decoration:none;display:inline-block;">무료로 시작하기 →</a>
    <div style="display:flex;align-items:center;gap:5px;font-size:11px;color:#64748b;white-space:nowrap;">
      <div style="width:14px;height:14px;background-color:#475569;border-radius:50% 50% 50% 0;display:inline-block;flex-shrink:0;"></div>
      좌측 하단 말풍선으로 문의하세요
    </div>
  </div>
</div>
"""

BANNER_COUDAE_SIMPLE = """
<div style="background-color:#fffbeb;border:1px solid #fcd34d;border-left:4px solid #e2b04a;border-radius:0 12px 12px 0;padding:18px 22px;display:flex;align-items:center;justify-content:space-between;gap:16px;margin:24px 0;">
  <div style="flex:1;">
    <div style="display:inline-block;background-color:#e2b04a;color:#1a1a2e;border-radius:4px;padding:2px 8px;font-size:10px;font-weight:800;margin-bottom:6px;">FREE</div>
    <div style="font-size:15px;font-weight:800;color:#1e293b;">쿠대 프로그램 — 지금 무료로 시작하세요</div>
    <div style="font-size:12px;color:#64748b;margin-top:3px;">구매대행 자동화의 시작 · 누적회원 15,900명</div>
  </div>
  <div style="display:flex;flex-direction:column;gap:8px;align-items:flex-end;">
    <a href="https://admin.coudae.kr/#/login" style="background-color:#e2b04a;color:#1a1a2e;border-radius:8px;padding:10px 18px;font-size:13px;font-weight:800;white-space:nowrap;text-decoration:none;display:inline-block;">무료 시작 →</a>
    <div style="display:flex;align-items:center;gap:5px;font-size:11px;color:#94a3b8;white-space:nowrap;">
      <div style="width:14px;height:14px;background-color:#cbd5e1;border-radius:50% 50% 50% 0;display:inline-block;"></div>
      좌측 하단 말풍선으로 문의하세요
    </div>
  </div>
</div>
"""

BANNER_SNS = """
<div style="margin:24px 0;">
  <div style="font-size:13px;font-weight:800;color:#1e293b;margin-bottom:12px;">🔗 쿠대 공식 채널</div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
    <a href="https://www.youtube.com/@coudae" style="background-color:#0f172a;border-radius:12px;padding:14px 16px;display:flex;align-items:center;gap:10px;border:1px solid #1e293b;text-decoration:none;">
      <div style="width:34px;height:34px;background-color:#cc0000;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;font-weight:800;flex-shrink:0;">▶</div>
      <div>
        <div style="font-size:13px;font-weight:800;color:#ffffff;">쿠대 유튜브</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">구매대행 실전 노하우</div>
      </div>
      <div style="margin-left:auto;color:#e2b04a;font-weight:800;">→</div>
    </a>
    <a href="https://cafe.naver.com/coudae" style="background-color:#0f172a;border-radius:12px;padding:14px 16px;display:flex;align-items:center;gap:10px;border:1px solid #1e293b;text-decoration:none;">
      <div style="width:34px;height:34px;background-color:#03c75a;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;font-weight:800;flex-shrink:0;">N</div>
      <div>
        <div style="font-size:13px;font-weight:800;color:#ffffff;">쿠대 네이버 카페</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">회원 18,000명 커뮤니티</div>
      </div>
      <div style="margin-left:auto;color:#e2b04a;font-weight:800;">→</div>
    </a>
    <a href="https://open.kakao.com/o/gKWnrBDg" style="background-color:#0f172a;border-radius:12px;padding:14px 16px;display:flex;align-items:center;gap:10px;border:1px solid #1e293b;text-decoration:none;">
      <div style="width:34px;height:34px;background-color:#fee500;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#3c1e1e;font-size:14px;font-weight:800;flex-shrink:0;">💬</div>
      <div>
        <div style="font-size:13px;font-weight:800;color:#ffffff;">쿠대 단톡방</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">실시간 소싱 정보 공유</div>
      </div>
      <div style="margin-left:auto;color:#e2b04a;font-weight:800;">→</div>
    </a>
    <a href="https://www.threads.com/@coudae_official" style="background-color:#0f172a;border-radius:12px;padding:14px 16px;display:flex;align-items:center;gap:10px;border:1px solid #1e293b;text-decoration:none;">
      <div style="width:34px;height:34px;background-color:#ffffff;border-radius:8px;display:flex;align-items:center;justify-content:center;color:#000;font-size:14px;font-weight:800;flex-shrink:0;">@</div>
      <div>
        <div style="font-size:13px;font-weight:800;color:#ffffff;">쿠대 스레드</div>
        <div style="font-size:11px;color:#64748b;margin-top:2px;">일상 인사이트 팔로우</div>
      </div>
      <div style="margin-left:auto;color:#e2b04a;font-weight:800;">→</div>
    </a>
  </div>
</div>
"""
