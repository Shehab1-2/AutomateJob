import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import re

async def fetch_html(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # headless=True for background
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(url, wait_until='networkidle')
        html = await page.content()
        await browser.close()
        return html

def extract_form_fields(html):
    soup = BeautifulSoup(html, 'html.parser')

    print("🔍 Detected form fields:\n")
    
    # Map labels to their associated inputs
    label_map = {}
    for label in soup.find_all('label'):
        if label.get('for'):
            label_map[label['for']] = label.get_text(strip=True)

    for tag in soup.find_all(['input', 'select', 'textarea']):
        tag_type = tag.name
        attrs = tag.attrs
        name = attrs.get('name', '')
        _id = attrs.get('id', '')
        _type = attrs.get('type', '') if tag.name == 'input' else ''
        placeholder = attrs.get('placeholder', '')
        label = label_map.get(_id, '')

        print(f"- [{tag_type.upper()}] name='{name}', id='{_id}', type='{_type}', placeholder='{placeholder}', label='{label}'")

async def main():
    url = "https://horizonmedia.wd1.myworkdayjobs.com/en-US/CareerOpportunities/job/New-York%2C-New-York/Data-Engineer-II_R0016008/apply/applyManually?sid=16&source=Linkedin"  # 🔁 Replace with the Workday signup page
    html = await fetch_html(url)

    with open("page_dump.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    extract_form_fields(html)

asyncio.run(main())
