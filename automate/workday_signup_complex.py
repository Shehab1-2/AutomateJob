import asyncio
import os
import logging
import time
from typing import Dict, Optional
from dataclasses import dataclass

from playwright.async_api import async_playwright, Page
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('workday_signup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class SignupCredentials:
    """Credentials for Workday sign-up"""
    email: str
    password: str

class WorkdaySignupAutomation:
    def __init__(self, user_data_dir: str = "./browser_data"):
        self.user_data_dir = user_data_dir
        self.browser = None
        self.context = None
        
        # YOUR CREDENTIALS - CUSTOMIZE THESE
        self.credentials = SignupCredentials(
            email="sam@fitme.lol",
            password="Sam123!!"
        )
        
        # "Apply Now" button selectors
        self.apply_now_selectors = [
            'button:has-text("Apply Now")',
            'button:has-text("Apply now")',
            'button:has-text("APPLY NOW")',
            'a:has-text("Apply Now")',
            'a:has-text("Apply now")',
            'input[type="button"][value*="Apply Now"]',
            'input[type="submit"][value*="Apply Now"]',
            '[data-automation-id*="apply"]',
            '.apply-button',
            '.apply-now-button',
            'button[aria-label*="Apply"]',
            'button[title*="Apply"]',
            'a:has-text("Apply")',
            'a[data-automation-id="adventureButton"]'
        ]
        
        # Email field selectors
        self.email_selectors = [
            'input[type="email"]',
            'input[name="email"]',
            'input[name="emailAddress"]',
            'input[name="username"]',
            'input[placeholder*="email"]',
            'input[placeholder*="Email"]',
            'input[aria-label*="Email"]',
            'input[data-automation-id*="email"]',
            'input[id*="email"]',
            'input[id*="Email"]'
        ]
        
        # Password field selectors
        self.password_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            'input[placeholder*="password"]',
            'input[placeholder*="Password"]',
            'input[aria-label*="Password"]',
            'input[data-automation-id*="password"]',
            'input[id*="password"]',
            'input[id*="Password"]'
        ]
        
        # Confirm/Verify password selectors
        self.confirm_password_selectors = [
            'input[name="confirmPassword"]',
            'input[name="confirm_password"]',
            'input[name="passwordConfirm"]',
            'input[name="password_confirm"]',
            'input[name="verifyPassword"]',
            'input[name="verify_password"]',
            'input[name="retypePassword"]',
            'input[name="retype_password"]',
            'input[placeholder*="confirm"]',
            'input[placeholder*="Confirm"]',
            'input[placeholder*="verify"]',
            'input[placeholder*="Verify"]',
            'input[placeholder*="retype"]',
            'input[placeholder*="Re-type"]',
            'input[aria-label*="Confirm"]',
            'input[aria-label*="Verify"]',
            'input[data-automation-id*="confirm"]',
            'input[data-automation-id*="verify"]',
            'input[id*="confirm"]',
            'input[id*="Confirm"]',
            'input[id*="verify"]',
            'input[id*="Verify"]'
        ]
        
        # Continue/Next/Submit button selectors
        self.continue_selectors = [
            'button:has-text("Continue")',
            'button:has-text("Next")',
            'button:has-text("Submit")',
            'button:has-text("Create Account")',
            'button:has-text("Sign Up")',
            'button:has-text("Register")',
            'button[type="submit"]',
            'input[type="submit"]',
            '[data-automation-id*="continue"]',
            '[data-automation-id*="next"]',
            '[data-automation-id*="submit"]',
            '.continue-button',
            '.next-button',
            '.submit-button'
        ]
        
        # Already have account / sign in selectors
        self.signin_link_selectors = [
            'a:has-text("Sign in")',
            'a:has-text("Log in")',
            'a:has-text("Already have an account")',
            'button:has-text("Sign in")',
            'button:has-text("Log in")',
            '[data-automation-id*="signin"]',
            '[data-automation-id*="login"]'
        ]

    async def setup_browser(self):
        """Initialize browser with existing profile"""
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--disable-background-networking',
                '--disable-background-timer-throttling'
            ]
        )
        
        self.context = self.browser
        logger.info("Browser initialized with existing profile")

    async def click_apply_now(self, page: Page) -> bool:
        """Click the 'Apply Now' button"""
        logger.info("Looking for 'Apply Now' button...")
        
        for selector in self.apply_now_selectors:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    logger.info(f"Found 'Apply Now' button: {selector}")
                    
                    # Scroll into view and click
                    await button.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    await button.click()
                    
                    logger.info("✅ 'Apply Now' button clicked!")
                    
                    # Wait for page to load/redirect
                    await page.wait_for_load_state('domcontentloaded')
                    await asyncio.sleep(2)
                    
                    return True
                    
            except Exception as e:
                logger.debug(f"Apply Now selector {selector} failed: {e}")
                continue
        
        logger.warning("❌ Could not find 'Apply Now' button")
        return False

    async def check_if_already_signed_in(self, page: Page) -> bool:
        """Check if user is already signed in and past the signup page"""
        try:
            # Check for indicators that we're past the signup page
            past_signup_indicators = [
                'text=Personal Information',
                'text=Contact Information',
                'text=Resume',
                'text=Application',
                'text=Job Details',
                'button:has-text("Submit Application")',
                '[data-automation-id*="application"]'
            ]
            
            for indicator in past_signup_indicators:
                element = await page.query_selector(indicator)
                if element:
                    logger.info("✅ Already signed in - past signup page")
                    return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking sign-in status: {e}")
            return False

    async def handle_existing_account(self, page: Page) -> bool:
        """Handle case where account already exists - try to sign in"""
        logger.info("Checking if we need to sign in instead...")
        
        for selector in self.signin_link_selectors:
            try:
                link = await page.query_selector(selector)
                if link and await link.is_visible():
                    logger.info(f"Found sign in link: {selector}")
                    await link.click()
                    await asyncio.sleep(2)
                    
                    # Try to sign in with existing credentials
                    return await self.fill_signin_form(page)
                    
            except Exception as e:
                logger.debug(f"Sign in selector {selector} failed: {e}")
                continue
        
        return False

    async def fill_signin_form(self, page: Page) -> bool:
        """Fill sign-in form if account already exists"""
        logger.info("Attempting to sign in with existing account...")
        
        try:
            # Fill email
            email_filled = await self.fill_field(page, self.email_selectors, self.credentials.email, "email")
            if not email_filled:
                logger.warning("Could not fill email field in sign-in form")
                return False
            
            # Fill password
            password_filled = await self.fill_field(page, self.password_selectors, self.credentials.password, "password")
            if not password_filled:
                logger.warning("Could not fill password field in sign-in form")
                return False
            
            # Click sign in button
            signin_button_selectors = [
                'button:has-text("Sign In")',
                'button:has-text("Log In")',
                'button:has-text("Login")',
                'button[type="submit"]',
                'input[type="submit"]'
            ]
            
            for selector in signin_button_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        await button.click()
                        logger.info("✅ Sign in button clicked")
                        
                        # Wait for sign in to complete
                        await asyncio.sleep(3)
                        return True
                        
                except Exception as e:
                    continue
            
            logger.warning("Could not find sign in button")
            return False
            
        except Exception as e:
            logger.error(f"Error during sign in: {e}")
            return False

    async def fill_field(self, page: Page, selectors: list, value: str, field_name: str) -> bool:
        logger.info(f"Filling {field_name} field...")

        # Try direct selectors first
        for selector in selectors:
            try:
                field = await page.query_selector(selector)
                if field and await field.is_visible():
                    await field.fill("")
                    await field.fill(value)
                    await page.evaluate('(el) => el.style.border = "2px solid red"', field)  # 🔴 Highlight field
                    logger.info(f"✅ {field_name} field filled via selector: {selector}")
                    return True
                else:
                    logger.debug(f"❌ {field_name} selector '{selector}' not found or not visible")
            except Exception as e:
                logger.debug(f"⚠️ Error using selector '{selector}' for {field_name}: {e}")


        # Fallback: label-based association
        try:
            label = await page.query_selector(f'label:has-text("{field_name.title()}")')
            if label:
                for_attr = await label.get_attribute("for")
                if for_attr:
                    input_selector = f'input[id="{for_attr}"]'
                    field = await page.query_selector(input_selector)
                    if field:
                        await field.fill("")
                        await field.fill(value)
                        logger.info(f"✅ {field_name} field filled via label association")
                        return True
        except Exception as e:
            logger.warning(f"Label association for {field_name} failed: {e}")

        logger.warning(f"❌ Could not find {field_name} field")
        return False


    async def click_continue_button(self, page: Page) -> bool:
        """Click continue/next/submit button"""
        logger.info("Looking for continue button...")
        
        for selector in self.continue_selectors:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    is_disabled = await button.get_attribute('disabled')
                    if not is_disabled:
                        logger.info(f"Found continue button: {selector}")
                        
                        await button.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        await button.click()
                        
                        logger.info("✅ Continue button clicked!")
                        
                        # Wait for page transition
                        await asyncio.sleep(3)
                        return True
                        
            except Exception as e:
                logger.debug(f"Continue selector {selector} failed: {e}")
                continue
        
        logger.warning("❌ Could not find continue button")
        return False

    async def handle_signup_form(self, page: Page) -> bool:
        """Handle the main signup form: email + password + confirm password"""
        logger.info("Filling signup form...")
        
        # Step 1: Fill email
        email_filled = await self.fill_field(page, self.email_selectors, self.credentials.email, "email")
        if not email_filled:
            logger.error("Failed to fill email field")
            return False
        
        await asyncio.sleep(1)
        
        # Step 2: Fill password
        password_filled = await self.fill_field(page, self.password_selectors, self.credentials.password, "password")
        if not password_filled:
            logger.error("Failed to fill password field")
            return False
        
        await asyncio.sleep(1)
        
        # Step 3: Fill confirm password (if present)
        confirm_password_filled = await self.fill_field(page, self.confirm_password_selectors, self.credentials.password, "confirm password")
        if confirm_password_filled:
            logger.info("✅ Confirm password field filled")
        else:
            logger.info("ℹ️  No confirm password field found (may not be required)")
        
        await asyncio.sleep(1)
        
        # Step 4: Click continue/submit
        #continue_clicked = await self.click_continue_button(page)
        #if not continue_clicked:
         #   logger.error("Failed to click continue button")
          #  return False
        
        logger.info("✅ Signup form completed successfully!")
        logger.info("🛑 Paused after filling signup form for manual verification")
        await asyncio.get_event_loop().run_in_executor(None, input, "Press ENTER to continue...")

        return True

    async def wait_for_signup_completion(self, page: Page, timeout: int = 30) -> bool:
        """Wait for signup to complete and redirect to application"""
        logger.info("Waiting for signup completion...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check if we've moved past signup to application pages
                application_indicators = [
                    'text=Personal Information',
                    'text=Contact Information',
                    'text=Resume',
                    'text=Application',
                    'text=Job Application',
                    'text=Tell us about yourself',
                    'button:has-text("Submit Application")',
                    '[data-automation-id*="application"]',
                    'input[name="firstName"]',
                    'input[name="lastName"]'
                ]
                
                for indicator in application_indicators:
                    element = await page.query_selector(indicator)
                    if element:
                        logger.info(f"✅ Signup completed - found application page indicator: {indicator}")
                        return True
                
                # Check for error messages
                error_indicators = [
                    'text=Email already exists',
                    'text=Account already exists',
                    'text=Invalid email',
                    'text=Password too weak',
                    '.error-message',
                    '.alert-error'
                ]
                
                for indicator in error_indicators:
                    element = await page.query_selector(indicator)
                    if element:
                        error_text = await element.inner_text()
                        logger.warning(f"❌ Signup error: {error_text}")
                        
                        # If account exists, try to sign in
                        if 'already exists' in error_text.lower() or 'already registered' in error_text.lower():
                            logger.info("Account already exists - attempting to sign in...")
                            return await self.handle_existing_account(page)
                        
                        return False
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.warning(f"Error waiting for signup completion: {e}")
                await asyncio.sleep(1)
        
        logger.warning("Signup completion timeout")
        return False

    async def automate_signup_process(self, job_url: str) -> bool:
        """Complete automation of Workday signup process"""
        logger.info(f"Starting Workday signup automation for: {job_url}")
        
        page = await self.context.new_page()
        
        try:
            # Step 1: Navigate to job URL
            logger.info(f"Navigating to: {job_url}")
            await page.goto(job_url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            
            # Step 2: Check if already signed in
          #  if await self.check_if_already_signed_in(page):
           #     logger.info("✅ Already signed in and past signup - ready for application!")
            #    return True
            
            # Step 3: Click "Apply Now" button
            apply_clicked = await self.click_apply_now(page)
            if not apply_clicked:
                logger.error("Failed to click 'Apply Now' button")
                return False
            # Step 3.5: Handle Workday modal (Apply Manually vs Autofill)
            
            try:
                await page.wait_for_selector('text="Start Your Application"', timeout=5000)
                await asyncio.sleep(1)

                apply_manually_btn = await page.query_selector('a[data-automation-id="applyManually"]')
                if apply_manually_btn:
                    await apply_manually_btn.click()
                    logger.info("✅ Clicked 'Apply Manually' on Workday modal")
                    await asyncio.sleep(2)

                    # ✅ Switch to new popup page (Workday opens a new tab)
                    pages = self.context.pages
                    if len(pages) > 1:
                        page = pages[-1]  # Latest page should be the signup form
                        logger.info(f"🧭 Switched to new signup page: {page.url}")
                    else:
                        logger.warning("⚠️ No new page detected after clicking 'Apply Manually'")

                    await page.wait_for_selector('label:has-text("Email Address")', timeout=8000)
                    logger.info("✅ Signup form detected")
                    await asyncio.sleep(10)

                else:
                    logger.warning("⚠️ 'Apply Manually' button not found – modal skipped")
            except Exception as e:
                logger.warning(f"⚠️ Modal step skipped (not detected): {e}")

            
            # Step 4: Check if already signed in after apply click
            if await self.check_if_already_signed_in(page):
                logger.info("✅ Already signed in after Apply Now - ready for application!")
                return True
            
            # Step 5: Fill signup form
            signup_success = await self.handle_signup_form(page)
            if not signup_success:
                logger.error("Failed to complete signup form")
                return False
            
            # Step 6: Wait for signup to complete
            #completion_success = await self.wait_for_signup_completion(page)
            #if not completion_success:
             #   logger.error("Signup did not complete successfully")
              #  return False
              #logger.info("🎉 Workday signup automation completed successfully!")
               # return True
            
            # Step 6: Pause for testing instead of continuing
            logger.info("🧪 TEST MODE: Signup form filled. Skipping submission to allow visual inspection.")
            await asyncio.get_event_loop().run_in_executor(None, input, "🛑 Press ENTER after you've inspected the filled form...")
            return True


            
                
            
        except Exception as e:
            logger.error(f"❌ Error during signup automation: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
            
        finally:
            # Keep the page open for manual review or further automation
            logger.info("Signup complete - page ready for application automation")
            # Don't close the page - leave it open for the main application automation

    async def run_signup_automation(self, job_urls: list):
        """Run signup automation for multiple job URLs"""
        try:
            await self.setup_browser()
            
            successful = 0
            failed = 0
            
            for i, job_url in enumerate(job_urls, 1):
                logger.info(f"\n{'='*80}")
                logger.info(f"Processing signup {i}/{len(job_urls)}")
                logger.info(f"{'='*80}")
                
                success = await self.automate_signup_process(job_url)
                
                if success:
                    successful += 1
                    logger.info(f"✅ Signup successful for job {i}")
                else:
                    failed += 1
                    logger.error(f"❌ Signup failed for job {i}")
                
                # Small delay between jobs
                if i < len(job_urls):
                    logger.info("Waiting 5 seconds before next signup...")
                    await asyncio.sleep(5)
            
            # Final summary
            logger.info(f"\n{'='*80}")
            logger.info(f"🎉 SIGNUP AUTOMATION COMPLETE")
            logger.info(f"{'='*80}")
            logger.info(f"Total jobs: {len(job_urls)}")
            logger.info(f"Successful signups: {successful}")
            logger.info(f"Failed signups: {failed}")
            logger.info(f"Success rate: {successful/len(job_urls)*100:.1f}%")
            logger.info(f"{'='*80}")
            
        except Exception as e:
            logger.error(f"Signup automation error: {e}")
            
        finally:
            if self.browser:
                logger.info("Browser kept open for manual review or further automation")
                # Don't close browser automatically

async def main():
    """Main function for testing"""
    # CUSTOMIZE THESE
    job_urls = [
        "https://horizonmedia.wd1.myworkdayjobs.com/CareerOpportunities/job/New-York-New-York/Data-Engineer-II_R0016008?sid=16&source=Linkedin",
        # Add more Workday job URLs here
    ]
    
    automation = WorkdaySignupAutomation()
    
    # Update credentials before running
    automation.credentials.email = "your.email@gmail.com"  # CHANGE THIS
    automation.credentials.password = "YourSecurePassword123!"  # CHANGE THIS
    
    await automation.run_signup_automation(job_urls)

if __name__ == "__main__":
    asyncio.run(main())