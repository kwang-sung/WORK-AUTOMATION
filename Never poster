#!/usr/bin/env python3
"""
네이버 블로그 자동 포스팅 모듈
카테고리 이름으로 직접 선택
"""

import os
import json
import time
from playwright.sync_api import sync_playwright

NAVER_COOKIES  = os.environ.get("NAVER_COOKIES", "")
BLOG_WRITE_URL = "https://blog.naver.com/gngsun/postwrite"


def load_cookies() -> list:
    if NAVER_COOKIES:
        return json.loads(NAVER_COOKIES)
    if os.path.exists("naver_cookies.json"):
        with open("naver_cookies.json", "r", encoding="utf-8") as f:
            return json.load(f)
    raise Exception("NAVER_COOKIES 환경변수가 없습니다!")


def post_to_blog(title: str, html_content: str, category: str) -> str:
    """
    네이버 블로그 자동 포스팅
    category: "구매대행 인사이트" 또는 "AI 트렌드"
    """
    cookies = load_cookies()
    posted_url = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        context.add_cookies(cookies)
        page = context.new_page()

        print(f"  🌐 블로그 글쓰기 이동 중... (카테고리: {category})")
        page.goto(BLOG_WRITE_URL, wait_until="networkidle", timeout=30000)
        time.sleep(3)

        # ── 카테고리 선택 ──────────────────────────────
        print(f"  📂 카테고리 선택 중: {category}")
        try:
            # 카테고리 버튼 클릭
            cat_btn = page.locator("button:has-text('카테고리'), .category_btn, [class*='category']").first
            if cat_btn.is_visible():
                cat_btn.click()
                time.sleep(1)

            # 카테고리 이름으로 선택
            cat_item = page.locator(f"text={category}").first
            if cat_item.is_visible():
                cat_item.click()
                time.sleep(1)
                print(f"  ✅ 카테고리 선택 완료: {category}")
            else:
                # select 태그로 시도
                page.select_option("select[name*='category'], select[id*='category']", label=category)
                print(f"  ✅ 카테고리 선택 완료: {category}")
        except Exception as e:
            print(f"  ⚠️  카테고리 선택 실패 (계속 진행): {e}")

        # ── 제목 입력 ──────────────────────────────────
        try:
            page.locator("input[placeholder*='제목']").first.fill(title)
            time.sleep(1)
            print("  ✅ 제목 입력 완료")
        except Exception as e:
            print(f"  ⚠️  제목 실패: {e}")

        # ── 본문 입력 ──────────────────────────────────
        try:
            page.evaluate(f"""
                const iframes = document.querySelectorAll('iframe');
                for (const iframe of iframes) {{
                    try {{
                        const doc = iframe.contentDocument || iframe.contentWindow.document;
                        const body = doc.querySelector('[contenteditable="true"]');
                        if (body) {{
                            body.innerHTML = {json.dumps(html_content)};
                            body.dispatchEvent(new Event('input', {{bubbles: true}}));
                            break;
                        }}
                    }} catch(e) {{}}
                }}
            """)
            time.sleep(2)
            print("  ✅ 본문 입력 완료")
        except Exception as e:
            print(f"  ⚠️  본문 실패: {e}")

        # ── 발행 버튼 ──────────────────────────────────
        try:
            for btn_text in ["발행", "등록", "완료", "올리기"]:
                btn = page.locator(f"button:has-text('{btn_text}')").first
                if btn.is_visible():
                    btn.click()
                    time.sleep(3)
                    break
            posted_url = page.url
            print(f"  ✅ 블로그 포스팅 완료 → {posted_url}")
        except Exception as e:
            print(f"  ⚠️  발행 실패: {e}")

        browser.close()

    return posted_url


def post_to_cafe(write_url: str, title: str, html_content: str) -> str:
    """네이버 카페 자동 게시"""
    cookies = load_cookies()
    posted_url = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        context.add_cookies(cookies)
        page = context.new_page()

        print("  🌐 카페 글쓰기 이동 중...")
        page.goto(write_url, wait_until="networkidle", timeout=30000)
        time.sleep(3)

        # 제목 입력
        try:
            page.locator("input[placeholder*='제목']").first.fill(title)
            time.sleep(1)
            print("  ✅ 제목 입력 완료")
        except Exception as e:
            print(f"  ⚠️  제목 실패: {e}")

        # 본문 입력
        try:
            page.evaluate(f"""
                const iframes = document.querySelectorAll('iframe');
                for (const iframe of iframes) {{
                    try {{
                        const doc = iframe.contentDocument || iframe.contentWindow.document;
                        const body = doc.querySelector('[contenteditable="true"]');
                        if (body) {{
                            body.innerHTML = {json.dumps(html_content)};
                            body.dispatchEvent(new Event('input', {{bubbles: true}}));
                            break;
                        }}
                    }} catch(e) {{}}
                }}
            """)
            time.sleep(2)
            print("  ✅ 본문 입력 완료")
        except Exception as e:
            print(f"  ⚠️  본문 실패: {e}")

        # 등록 버튼
        try:
            for btn_text in ["등록", "발행", "완료", "올리기"]:
                btn = page.locator(f"button:has-text('{btn_text}')").first
                if btn.is_visible():
                    btn.click()
                    time.sleep(3)
                    break
            posted_url = page.url
            print(f"  ✅ 카페 게시 완료 → {posted_url}")
        except Exception as e:
            print(f"  ⚠️  등록 실패: {e}")

        browser.close()

    return posted_url


if __name__ == "__main__":
    # 로컬 테스트
    print("테스트 실행 중...")
    test_title   = "🏄 테스트 게시글"
    test_content = "<h2>테스트</h2><p>자동 포스팅 테스트입니다.</p>"

    post_to_blog(test_title, test_content, "구매대행 인사이트")
