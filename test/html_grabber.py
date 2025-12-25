# pip install playwright
# playwright install

from playwright.sync_api import sync_playwright

url = "https://www.nuratechsystems.com/"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        viewport={"width": 1366, "height": 768},
        java_script_enabled=True,
    )
    page = context.new_page()

    # Optional: block heavy assets to speed up
    def route_block_fonts_images(route):
        if any(s in route.request.resource_type for s in ["image", "font", "media"]):
            return route.abort()
        route.continue_()
    context.route("**/*", route_block_fonts_images)

    page.goto(url, wait_until="domcontentloaded")

    # Wait for network to settle or a specific selector that guarantees content is in the DOM
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except:
        pass  # some SPAs never fully go idle; fall back to selector or a sleep if you must

    # If you know a key element exists when content is ready, prefer this:
    # page.wait_for_selector("main, #root, #app, body", timeout=10000)

    html = page.content()  # This is the fully rendered DOM snapshot
    print("Chars:", len(html))
    with open("page_rendered.html", "w", encoding="utf-8") as f:
        f.write(html)

    browser.close()
