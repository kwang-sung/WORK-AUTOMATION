#!/usr/bin/env python3
"""
네이버 블로그·카페 자동 포스팅 모듈
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


def _input_title(page, title: str):
    """네이버 에디터 제목 입력 - 여러 방법 시도"""
    selectors = [
        "input.se-title-input",
        "input[class*='title']",
        ".se-title-input",
        "[contenteditable='true'][class*='title']",
        "div.se-title-input",
        "textarea[class*='title']",
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=3000):
                el.click()
                el.fill(title)
                print(f"  ✅ 제목 입력 완료 ({sel})")
                time.sleep(1)
                return True
        except Exception:
            continue

    # contenteditable 방식 시도
    try:
        page.evaluate(f"""
            const titleEls = document.querySelectorAll('[contenteditable="true"]');
            for (const el of titleEls) {{
                if (el.className && el.className.includes('title')) {{
                    el.focus();
                    el.textContent = {json.dumps(title)};
                    el.dispatchEvent(new Event('input', {{bubbles: true}}));
                    break;
                }}
            }}
        """)
        print("  ✅ 제목 입력 완료 (contenteditable)")
        time.sleep(1)
        return True
    except Exception as e:
        print(f"  ⚠️  제목 입력 실패: {e}")
        return False


def _input_body(page, html_content: str):
    """네이버 에디터 본문 입력"""
    try:
        page.evaluate(f"""
            // iframe 내부 에디터 시도
            const iframes = document.querySelectorAll('iframe');
            let done = false;
            for (const iframe of iframes) {{
                try {{
                    const doc = iframe.contentDocument || iframe.contentWindow.document;
                    const body = doc.querySelector('[contenteditable="true"]');
                    if (body) {{
                        body.innerHTML = {json.dumps(html_content)};
                        body.dispatchEvent(new Event('input', {{bubbles: true}}));
                        done = true;
                        break;
                    }}
                }} catch(e) {{}}
            }}
            // 직접 에디터 시도
            if (!done) {{
                const editors = document.querySelectorAll('[contenteditable="true"]');
                for (const ed of editors) {{
                    if (!ed.className.includes('title')) {{
                        ed.innerHTML = {json.dumps(html_content)};
                        ed.dispatchEvent(new Event('input', {{bubbles: true}}));
                        break;
                    }}
                }}
            }}
        """)
        print("  ✅ 본문 입력 완료")
        time.sleep(2)
        return True
    except Exception as e:
        print(f"  ⚠️  본문 입력 실패: {e}")
        return False


def _click_submit(page, label: str) -> str:
    """등록/발행 버튼 클릭"""
    btn_texts = ["발행", "등록", "완료", "올리기", "Publish"]
    for btn_text in btn_texts:
        try:
            btn = page.locator(f"button:has-text('{btn_text}')").first
            if btn.is_visible(timeout=3000):
                btn.click()
                print(f"  ✅ {label} '{btn_text}' 버튼 클릭")
                time.sleep(4)
                return page.url
        except Exception:
            continue
    print(f"  ⚠️  {label} 버튼 못 찾음")
    return page.url


def post_to_blog(title: str, html_content: str, category: str) -> str:
    """네이버 블로그 자동 포스팅"""
    cookies = load_cookies()
    posted_url = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        context.add_cookies(cookies)
        page = context.new_page()

        print(f"  🌐 블로그 글쓰기 이동 중... (카테고리: {category})")
        page.goto(BLOG_WRITE_URL, wait_until="networkidle", timeout=30000)
        time.sleep(4)

        # 카테고리 선택
        try:
            cat_btn = page.locator("button:has-text('카테고리'), [class*='category'] button").first
            if cat_btn.is_visible(timeout=3000):
                cat_btn.click()
                time.sleep(1)
                cat_item = page.locator(f"text='{category}'").first
                if cat_item.is_visible(timeout=3000):
                    cat_item.click()
                    time.sleep(1)
                    print(f"  ✅ 카테고리 선택: {category}")
        except Exception as e:
            print(f"  ⚠️  카테고리 선택 실패 (계속): {e}")

        # 제목 입력
        _input_title(page, title)

        # 본문 입력
        _input_body(page, html_content)

        # 발행
        posted_url = _click_submit(page, "블로그")
        print(f"  ✅ 블로그 완료 → {posted_url}")

        browser.close()

    return posted_url


def post_to_cafe(write_url: str, title: str, html_content: str) -> str:
    """네이버 카페 자동 게시"""
    cookies = load_cookies()
    posted_url = ""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        context.add_cookies(cookies)
        page = context.new_page()

        print("  🌐 카페 글쓰기 이동 중...")
        page.goto(write_url, wait_until="networkidle", timeout=30000)
        time.sleep(4)

        # 제목 입력
        _input_title(page, title)

        # 본문 입력
        _input_body(page, html_content)

        # 등록
        posted_url = _click_submit(page, "카페")
        print(f"  ✅ 카페 완료 → {posted_url}")

        browser.close()

    return posted_url


if __name__ == "__main__":
    print("테스트 실행 중...")
    test_title   = "🏄 테스트 게시글"
    test_content = "<h2>테스트</h2><p>자동 포스팅 테스트입니다.</p>"
    post_to_blog(test_title, test_content, "구매대행 인사이트")
