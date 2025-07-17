import asyncio
import time
from playwright.async_api import async_playwright
from honeypot_detector import HoneypotDetector

# Test data for form filling
TEST_DATA = {
    'email': 'test.user@example.com',
    'password': 'TestPassword123!',
    'confirm_password': 'TestPassword123!'
}

async def highlight_element(element, color='red'):
    """Add a colored border to an element for visual verification"""
    await element.evaluate(f'element => element.style.border = "3px solid {color}"')

async def fill_signup_form(page):
    """Fill signup form fields with test data and highlight them"""
    print("🔍 Looking for signup form fields...")

    # Initialize honeypot detector
    detector = HoneypotDetector()

    
    # Common email field selectors
    email_selectors = [
        'input[data-automation-id="email"]',
        'input[type="email"]',
        'input[name*="email" i]',
        'input[id*="email" i]',
        'input[placeholder*="email" i]'
    ]
    
    # Common password field selectors
    password_selectors = [
        'input[type="password"]',
        'input[name*="password" i]',
        'input[id*="password" i]'
    ]
    
    # Common confirm password selectors
    confirm_password_selectors = [
        'input[name*="confirm" i]',
        'input[id*="confirm" i]',
        'input[placeholder*="confirm" i]',
        'input[name*="repeat" i]',
        'input[id*="repeat" i]',
        'input[placeholder*="repeat" i]'
    ]
    
    # Fill email field
    email_filled = False
    for selector in email_selectors:
        try:
            email_field = page.locator(selector).first
            if await email_field.is_visible():
                if await detector.safe_fill_field(email_field, TEST_DATA['email'], "email"):
                    await highlight_element(email_field, 'green')
                    print(f"✅ Email filled: {TEST_DATA['email']}")
                    email_filled = True
                    break
        except Exception as e:
            print(f"❌ Error with email selector '{selector}': {e}")
            continue
    
    if not email_filled:
        print("❌ Email field not found")
    
    # Check terms and conditions checkbox
    print("🔍 Looking for terms and conditions checkbox...")
    terms_selectors = [
        'input[data-automation-id="createAccountCheckbox"]',
        'input[type="checkbox"]',
        'input[name*="terms" i]',
        'input[id*="terms" i]',
        'input[name*="agree" i]',
        'input[id*="agree" i]'
    ]
    
    terms_checked = False
    for selector in terms_selectors:
        try:
            checkbox = page.locator(selector).first
            if await checkbox.is_visible():
                if await detector.safe_check_checkbox(checkbox, "terms checkbox"):
                    await highlight_element(checkbox, 'green')
                    print("✅ Terms and conditions checkbox checked")
                    terms_checked = True
                    break
        except Exception as e:
            print(f"❌ Error with checkbox selector '{selector}': {e}")
            continue
    
    if not terms_checked:
        print("❌ Terms and conditions checkbox not found")
    
    # Find all password fields first
    print("🔍 Finding all password fields...")
    password_fields = []
    
    # First, try to find all password fields using type="password"
    try:
        all_password_fields = page.locator('input[type="password"]')
        count = await all_password_fields.count()
        print(f"📊 Found {count} password fields")
        
        for i in range(count):
            field = all_password_fields.nth(i)
            if await field.is_visible():
                # Get field attributes for debugging
                name = await field.get_attribute('name') or 'unnamed'
                id_attr = await field.get_attribute('id') or 'no-id'
                placeholder = await field.get_attribute('placeholder') or 'no-placeholder'
                print(f"  📋 Password field {i+1}: name='{name}', id='{id_attr}', placeholder='{placeholder}'")
                
                # Check if it's not a honeypot using improved detector
                if not await detector.is_honeypot_field(field):
                    password_fields.append(field)
                    print(f"    ✅ Added to usable fields")
                else:
                    print(f"    ❌ Detected as honeypot, skipping")
    except Exception as e:
        print(f"❌ Error finding password fields: {e}")
    
    print(f"📊 Total usable password fields: {len(password_fields)}")
    
    # Fill password fields
    if len(password_fields) >= 1:
        # Fill first password field
        try:
            print(f"🔐 Attempting to fill first password field...")
            if await detector.safe_fill_field(password_fields[0], TEST_DATA['password'], "password"):
                await highlight_element(password_fields[0], 'green')
                print(f"✅ Password filled: {TEST_DATA['password']}")
                
                # Add a small delay before filling second field
                await asyncio.sleep(500)
                
                # If there's a second password field, fill it
                if len(password_fields) >= 2:
                    try:
                        print(f"🔐 Attempting to fill second password field...")
                        if await detector.safe_fill_field(password_fields[1], TEST_DATA['confirm_password'], "confirm password"):
                            await highlight_element(password_fields[1], 'green')
                            print(f"✅ Confirm password filled: {TEST_DATA['confirm_password']}")
                        else:
                            print("❌ Failed to fill confirm password field")
                    except Exception as e:
                        print(f"❌ Error filling confirm password: {e}")
                else:
                    print("⚠️  Only one password field found, searching for confirm password separately...")
                    
                    # Search for confirm password using specific selectors
                    confirm_filled = False
                    for selector in confirm_password_selectors:
                        try:
                            confirm_field = page.locator(selector).first
                            if await confirm_field.is_visible():
                                # Make sure it's not the same field we already filled
                                first_field_id = await password_fields[0].get_attribute('id')
                                confirm_field_id = await confirm_field.get_attribute('id')
                                
                                if first_field_id != confirm_field_id:
                                    if await detector.safe_fill_field(confirm_field, TEST_DATA['confirm_password'], "confirm password"):
                                        await highlight_element(confirm_field, 'green')
                                        print(f"✅ Confirm password filled: {TEST_DATA['confirm_password']}")
                                        confirm_filled = True
                                        break
                        except Exception as e:
                            print(f"❌ Error with selector '{selector}': {e}")
                            continue
                    
                    if not confirm_filled:
                        print("❌ Confirm password field not found")
            else:
                print("❌ Failed to fill password field")
        except Exception as e:
            print(f"❌ Error filling password: {e}")
    else:
        print("❌ No password fields found")

    # Debug: Print all input fields on the page
    print("\n🐛 Debug: All input fields on page:")
    try:
        all_inputs = page.locator('input')
        input_count = await all_inputs.count()
        for i in range(min(input_count, 10)):  # Limit to first 10 for readability
            field = all_inputs.nth(i)
            if await field.is_visible():
                field_type = await field.get_attribute('type') or 'text'
                name = await field.get_attribute('name') or 'unnamed'
                id_attr = await field.get_attribute('id') or 'no-id'
                placeholder = await field.get_attribute('placeholder') or 'no-placeholder'
                print(f"  📋 Input {i+1}: type='{field_type}', name='{name}', id='{id_attr}', placeholder='{placeholder}'")
    except Exception as e:
        print(f"❌ Error debugging input fields: {e}")

async def main():
    # Replace with your Workday job URL
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
                '[data-automation-id*="apply"]',
                '.apply-button'
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
            
            await page.wait_for_timeout(3000)  # Wait for modal or page load
            
            # Step 2: Handle modal if it appears
            print("🔍 Checking for modal...")
            modal_selectors = [
                'a[data-automation-id="applyManually"]',
                'button:has-text("Apply Manually")',
                'button:has-text("Manual")',
                '[data-automation-id*="manual"]',
                '[data-automation-id="applyManually"]'
            ]
            
            modal_handled = False
            for selector in modal_selectors:
                try:
                    modal_button = page.locator(selector).first
                    if await modal_button.is_visible():
                        await modal_button.click()
                        print("✅ Apply Manually clicked")
                        modal_handled = True
                        break
                except:
                    continue
            
            if modal_handled:
                await page.wait_for_timeout(3000)
            
            # Step 3: Handle new tab if opened
            print("🔍 Checking for new tabs...")
            if len(context.pages) > 1:
                # Switch to the newest tab
                page = context.pages[-1]
                await page.bring_to_front()
                print("✅ Switched to new tab")
                await page.wait_for_load_state('networkidle')
            
            # Step 4: Fill signup form
            await fill_signup_form(page)
            
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