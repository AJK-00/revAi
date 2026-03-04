from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup


def fetch_website_data(url):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, timeout=60000)
            page.wait_for_load_state("networkidle")

            html = page.content()
            browser.close()

    except Exception as e:
        return {"error": str(e)}

    soup = BeautifulSoup(html, "html.parser")

    title = soup.title.string if soup.title else ""

    meta_tags = [
        tag.get("content", "")
        for tag in soup.find_all("meta")
        if tag.get("content")
    ]

    scripts = [
        script.get("src")
        for script in soup.find_all("script")
        if script.get("src")
    ]

    stylesheets = [
        link.get("href")
        for link in soup.find_all("link")
        if link.get("rel") and "stylesheet" in link.get("rel")
    ]

    return {
        "title": title,
        "meta_tags": meta_tags[:30],
        "scripts": scripts[:30],
        "stylesheets": stylesheets[:30],
        "html_sample": html[:8000]
    }