import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# Test data for form filling
TEST_DATA = {
    'email': 'test.user@example.com',
    'password': 'TestPassword123!',
    'confirm_password': 'TestPassword123!',
    'first_name': 'John',
    'last_name': 'Doe',
    'phone': '555-123-4567'
}

def classify_field(tag, label_text=""):
    """Classify a form field based on its attributes and label"""
    attrs = tag.attrs
    name = attrs.get('name', '').lower()
    _id = attrs.get('id', '').lower()
    _type = attrs.get('type', '').lower()
    placeholder = attrs.get('placeholder', '').lower()
    automation_id = attrs.get('data-automation-id', '').lower()
    
    # Combine all text for pattern matching
    all_text = f"{name} {_id} {_type} {placeholder} {automation_id} {label_text}".lower()
    
    # Skip honeypot fields
    if any(keyword in all_text for keyword in ['beecatcher', 'honeypot', 'trap', 'bot']):
        return 'honeypot'
    
    # Email field
    if 'email' in all_text or _type == 'email':
        return 'email'
    
    # Password fields - check specific automation IDs first
    if automation_id == 'password':
        return 'password'
    if automation_id == 'verifypassword':
        return 'confirm_password'
    if 'password' in all_text or _type == 'password':
        if 'verify' in all_text or 'confirm' in all_text or 'repeat' in all_text:
            return 'confirm_password'
        return 'password'
    
    # Checkboxes - check specific automation ID first
    if _type == 'checkbox':
        if automation_id == 'createaccountcheckbox':
            return 'terms_checkbox'
        if 'terms' in all_text or 'conditions' in all_text or 'agree' in all_text:
            return 'terms_checkbox'
        return 'checkbox'
    
    # Common text fields
    if 'first' in all_text and 'name' in all_text:
        return 'first_name'
    if 'last' in all_text and 'name' in all_text:
        return 'last_name'
    if 'phone' in all_text or _type == 'tel':
        return 'phone'
    
    return 'unknown'

def build_selector(tag):
    """Build a CSS selector for the field"""
    attrs = tag.attrs
    
    # Prefer data-automation-id
    if 'data-automation-id' in attrs:
        return f'{tag.name}[data-automation-id="{attrs["data-automation-id"]}"]'
    
    # Then id
    if 'id' in attrs:
        return f'{tag.name}[id="{attrs["id"]}"]'
    
    # Then name
    if 'name' in attrs:
        return f'{tag.name}[name="{attrs["name"]}"]'
    
    return f'{tag.name}'

def analyze_form_fields(html):
    """Analyze HTML and return actionable field information"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Map labels to their inputs
    label_map = {}
    for label in soup.find_all('label'):
        if label.get('for'):
            label_map[label['for']] = label.get_text(strip=True)
    
    # Find actionable form fields
    fields = []
    fillable_types = ['email', 'password', 'confirm_password', 'terms_checkbox', 'first_name', 'last_name', 'phone']
    
    for tag in soup.find_all(['input', 'select', 'textarea']):
        # Skip hidden fields
        if tag.get('type') == 'hidden':
            continue
        
        label_text = label_map.get(tag.get('id', ''), '')
        field_type = classify_field(tag, label_text)
        
        # Only keep fields we can fill
        if field_type in fillable_types:
            selector = build_selector(tag)
            fields.append({
                'type': field_type,
                'selector': selector,
                'label': label_text
            })
    
    return fields

async def highlight_element(element, color='green'):
    """Add a colored border to an element for visual verification"""
    await element.evaluate(f'element => element.style.border = "3px solid {color}"')

async def fill_field_by_type(page, field):
    """Fill a field based on its type"""
    selector = field['selector']
    field_type = field['type']
    
    print(f"\n🔍 Classifying field: {field_type} -> {field['selector']}")
    
    try:
        element = page.locator(selector).first
        if not await element.is_visible():
            return False
        
        if field_type == 'email':
            await element.fill(TEST_DATA['email'])
            await highlight_element(element)
            print(f"✅ Email filled: {TEST_DATA['email']}")
            
        elif field_type == 'password':
            await element.fill(TEST_DATA['password'])
            await highlight_element(element)
            print(f"✅ Password filled: {TEST_DATA['password']}")
            
        elif field_type == 'confirm_password':
            await element.fill(TEST_DATA['confirm_password'])
            await highlight_element(element)
            print(f"✅ Confirm password filled: {TEST_DATA['confirm_password']}")
            
        elif field_type == 'terms_checkbox':
            if not await element.is_checked():
                await element.check()
            await highlight_element(element)
            print(f"✅ Terms checkbox checked")
            
        elif field_type == 'first_name':
            await element.fill(TEST_DATA['first_name'])
            await highlight_element(element)
            print(f"✅ First name filled: {TEST_DATA['first_name']}")
            
        elif field_type == 'last_name':
            await element.fill(TEST_DATA['last_name'])
            await highlight_element(element)
            print(f"✅ Last name filled: {TEST_DATA['last_name']}")
            
        elif field_type == 'phone':
            await element.fill(TEST_DATA['phone'])
            await highlight_element(element)
            print(f"✅ Phone filled: {TEST_DATA['phone']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to fill {field_type}: {selector}")
        return False

async def dynamic_fill_form(page):
    """Dynamically analyze and fill form fields"""
    print("🔍 Analyzing page for form fields...")
    
    # Get current page HTML
    html = await page.content()
    
    # Analyze fields
    fields = analyze_form_fields(html)
    
    if not fields:
        print("❌ No fillable fields found")
        return
    
    print(f"📋 Found {len(fields)} fillable fields:")
    for field in fields:
        print(f"  - {field['type']}: {field['selector']}")
    
    print("\n🖊️  Filling fields...")
    
    # Fill each field
    filled_count = 0
    for field in fields:
        if await fill_field_by_type(page, field):
            filled_count += 1
        await asyncio.sleep(500)  # Small delay between fills
    
    print(f"\n✅ Successfully filled {filled_count}/{len(fields)} fields")

async def main():
    # Get job URL from user
    job_url = input("Enter the Workday job URL: ").strip()
    
    if not job_url:
        print("❌ Please provide a valid job URL")
        return
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            print(f"🌐 Navigating to: {job_url}")
            await page.goto(job_url)
            await page.wait_for_load_state('networkidle')
            
            # Step 1: Click Apply button
            print("🔍 Looking for Apply button...")
            apply_selectors = [
                'button:has-text("Apply")',
                'button:has-text("Apply Now")',
                'a:has-text("Apply")',
                'a:has-text("Apply Now")',
                '[data-automation-id*="apply"]'
            ]
            
            apply_clicked = False
            for selector in apply_selectors:
                try:
                    apply_button = page.locator(selector).first
                    if await apply_button.is_visible():
                        await apply_button.click()
                        print("✅ Apply button clicked")
                        apply_clicked = True
                        break
                except:
                    continue
            
            if not apply_clicked:
                print("❌ Apply button not found")
                return
            
            await page.wait_for_timeout(3000)
            
            # Step 2: Handle modal if it appears
            print("🔍 Checking for modal...")
            modal_selectors = [
                'a[data-automation-id="applyManually"]',
                'button:has-text("Apply Manually")',
                '[data-automation-id="applyManually"]'
            ]
            
            for selector in modal_selectors:
                try:
                    modal_button = page.locator(selector).first
                    if await modal_button.is_visible():
                        await modal_button.click()
                        print("✅ Apply Manually clicked")
                        break
                except:
                    continue
            
            await page.wait_for_timeout(3000)
            
            # Step 3: Handle new tab if opened
            if len(context.pages) > 1:
                page = context.pages[-1]
                await page.bring_to_front()
                print("✅ Switched to new tab")
                await page.wait_for_load_state('networkidle')
            
            # Step 4: Dynamic form filling
            await dynamic_fill_form(page)
            
            print("\n🎉 Automation complete!")
            print("📋 Fields have been filled and highlighted.")
            print("🔍 Please inspect the form manually before proceeding.")
            print("⏸️  Script paused - press Ctrl+C to exit when ready.")
            
            # Keep browser open for manual inspection
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            print("\n👋 Exiting...")
        
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())