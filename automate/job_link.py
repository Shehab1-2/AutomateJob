import asyncio
import os
import logging
import time
from typing import List, Dict, Optional
from dataclasses import dataclass

import aiohttp
from playwright.async_api import async_playwright, Page
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('greenhouse_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class GreenhouseJob:
    """Data class for Greenhouse job applications"""
    id: str
    title: str
    company: str
    apply_link: str
    
class GreenhouseAutomation:
    def __init__(self, notion_token: str, database_id: str, user_data_dir: str = "./browser_data"):
        self.notion_token = notion_token
        self.database_id = database_id
        self.user_data_dir = user_data_dir
        self.session = None
        self.browser = None
        self.context = None
        
        # Simplify detection selectors (common indicators)
        self.simplify_indicators = [
            '[data-simplify="true"]',
            '.simplify-autofilled',
            '.simplify-detected',
            # Add more based on actual Simplify behavior
        ]
        
        # Submit button selectors (priority order)
        self.submit_selectors = [
            'button[type="submit"]:has-text("Submit Application")',
            'button[type="submit"]:has-text("Apply Now")',
            'button[type="submit"]:has-text("Submit")',
            'input[type="submit"][value*="Apply"]',
            'input[type="submit"][value*="Submit"]',
            'button:has-text("Submit Application")',
            'button:has-text("Apply Now")',
            'button:has-text("Apply")',
            '.btn-primary:has-text("Submit")',
            '.btn-primary:has-text("Apply")',
            # Greenhouse-specific patterns
            'button[data-qa="submit-application"]',
            'button[data-testid="submit-application"]'
        ]
        
        # Success indicators
        self.success_indicators = [
            'text=Application submitted',
            'text=Thank you for applying',
            'text=Application received',
            'text=Successfully submitted',
            '.confirmation',
            '.success-message'
        ]
    
    async def setup_session(self):
        """Setup aiohttp session for Notion API"""
        headers = {
            'Authorization': f'Bearer {self.notion_token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
        self.session = aiohttp.ClientSession(headers=headers)
    
    async def get_greenhouse_jobs(self) -> List[GreenhouseJob]:
        """Get Greenhouse jobs from Notion database"""
        url = f'https://api.notion.com/v1/databases/{self.database_id}/query'
        
        jobs = []
        
        try:
            # First, let's get ALL jobs to see what's in the database
            logger.info("Fetching all jobs from database for debugging...")
            async with self.session.post(url, json={}) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch jobs: {response.status}")
                    return jobs
                
                data = await response.json()
                all_results = data.get('results', [])
                logger.info(f"Total jobs in database: {len(all_results)}")
                
                # Debug: Print first few jobs to see structure
                for i, result in enumerate(all_results[:3]):  # Just first 3 for debugging
                    props = result.get('properties', {})
                    
                    # Check Type field
                    type_prop = props.get('Type', {})
                    type_value = ""
                    if type_prop.get('rich_text'):
                        type_value = type_prop['rich_text'][0]['text']['content'] if type_prop['rich_text'] else ""
                    
                    # Check Apply URL field
                    apply_url_prop = props.get('Apply URL', {})
                    apply_url = apply_url_prop.get('url', '')
                    
                    # Check Job Title
                    title_prop = props.get('Job Title', {})
                    title = ""
                    if title_prop.get('title'):
                        title = title_prop['title'][0]['text']['content'] if title_prop['title'] else ""
                    
                    logger.info(f"Job {i+1}: Title='{title}', Type='{type_value}', Apply URL='{apply_url}'")
                
                # Now filter for Greenhouse jobs
                greenhouse_jobs = []
                for result in all_results:
                    props = result.get('properties', {})
                    
                    # Check Type field
                    type_prop = props.get('Type', {})
                    type_value = ""
                    if type_prop.get('rich_text') and len(type_prop['rich_text']) > 0:
                        type_value = type_prop['rich_text'][0]['text']['content']
                    
                    # Check Apply URL field
                    apply_url_prop = props.get('Apply URL', {})
                    apply_url = apply_url_prop.get('url', '')
                    
                    logger.debug(f"Checking job - Type: '{type_value}', Apply URL exists: {bool(apply_url)}")
                    
                    # Check if it's a Greenhouse job with Apply URL
                    if type_value.lower() == "greenhouse" and apply_url:
                        job = self._parse_greenhouse_job(result)
                        if job:
                            greenhouse_jobs.append(job)
                            logger.info(f"✅ Found Greenhouse job: {job.title} at {job.company}")
                
                logger.info(f"Found {len(greenhouse_jobs)} Greenhouse jobs to process")
                return greenhouse_jobs
                
        except Exception as e:
            logger.error(f"Error fetching Greenhouse jobs: {e}")
            return jobs
    
    def _parse_greenhouse_job(self, result: Dict) -> Optional[GreenhouseJob]:
        """Parse Notion result into GreenhouseJob"""
        try:
            props = result.get('properties', {})
            
            # Extract title
            title_prop = props.get('Job Title', {})
            title = ""
            if title_prop.get('title'):
                title = title_prop['title'][0]['text']['content']
            
            # Extract company
            company_prop = props.get('Company', {})
            company = ""
            if company_prop.get('rich_text'):
                company = company_prop['rich_text'][0]['text']['content']
            
            # Extract apply link (Apply URL column)
            apply_link_prop = props.get('Apply URL', {})
            apply_link = apply_link_prop.get('url', '')
            
            if not apply_link:
                return None
            
            return GreenhouseJob(
                id=result['id'],
                title=title,
                company=company,
                apply_link=apply_link
            )
            
        except Exception as e:
            logger.error(f"Error parsing job: {e}")
            return None
    
    async def setup_browser(self):
        """Initialize browser with existing profile"""
        playwright = await async_playwright().start()
        
        # Use your existing browser profile to maintain Simplify login
        self.browser = await playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False,  # Keep visible for monitoring
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-first-run'
            ]
        )
        
        self.context = self.browser
        logger.info("Browser initialized with existing profile")
    
    async def wait_for_simplify(self, page: Page, timeout: int = 30) -> bool:
        """Wait for Simplify to autofill the form"""
        logger.info("Waiting for Simplify to autofill form...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check for Simplify indicators
                for indicator in self.simplify_indicators:
                    element = await page.query_selector(indicator)
                    if element:
                        logger.info(f"Simplify detected via selector: {indicator}")
                        return True
                
                # Alternative: Check for filled form fields
                filled_inputs = await page.evaluate("""
                    () => {
                        const inputs = document.querySelectorAll('input[type="text"], input[type="email"], textarea');
                        let filledCount = 0;
                        inputs.forEach(input => {
                            if (input.value && input.value.trim().length > 0) {
                                filledCount++;
                            }
                        });
                        return filledCount;
                    }
                """)
                
                if filled_inputs >= 3:  # Assume if 3+ fields are filled, Simplify worked
                    logger.info(f"Detected {filled_inputs} filled fields - assuming Simplify completed")
                    return True
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.warning(f"Error checking Simplify status: {e}")
                await asyncio.sleep(1)
        
        logger.warning("Simplify autofill timeout - proceeding anyway")
        return False
    
    async def find_and_click_submit(self, page: Page) -> bool:
        """Find and click the submit button"""
        logger.info("Looking for submit button...")
        
        for selector in self.submit_selectors:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    # Check if button is enabled
                    is_disabled = await button.get_attribute('disabled')
                    if not is_disabled:
                        logger.info(f"Found submit button: {selector}")
                        
                        # Scroll into view and click
                        await button.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        await button.click()
                        
                        logger.info("Submit button clicked!")
                        return True
                        
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        logger.error("No submit button found!")
        return False
    
    async def wait_for_submission_confirmation(self, page: Page, timeout: int = 15) -> bool:
        """Wait for submission confirmation"""
        logger.info("Waiting for submission confirmation...")
        
        try:
            # Wait for any success indicator
            for indicator in self.success_indicators:
                try:
                    await page.wait_for_selector(indicator, timeout=timeout * 1000)
                    logger.info(f"Success confirmed via: {indicator}")
                    return True
                except:
                    continue
            
            # Alternative: Check URL change (often redirects to confirmation page)
            await asyncio.sleep(3)
            current_url = page.url
            if 'thank' in current_url.lower() or 'success' in current_url.lower() or 'confirmation' in current_url.lower():
                logger.info("Success inferred from URL change")
                return True
            
            logger.warning("Could not confirm submission success")
            return False
            
        except Exception as e:
            logger.error(f"Error waiting for confirmation: {e}")
            return False
    
    async def process_greenhouse_application(self, job: GreenhouseJob) -> bool:
        """Process a single Greenhouse application"""
        logger.info(f"Processing: {job.title} at {job.company}")
        
        page = await self.context.new_page()
        
        try:
            # Navigate to application link
            logger.info(f"Navigating to: {job.apply_link}")
            await page.goto(job.apply_link, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for page to stabilize
            await asyncio.sleep(2)
            
            # Check if already applied (common Greenhouse pattern)
            already_applied = await page.query_selector('text=You have already applied')
            if already_applied:
                logger.info("Already applied to this position - skipping")
                return True
            
            # Wait for Simplify to autofill
            simplify_success = await self.wait_for_simplify(page)
            
            # Give a bit more time for Simplify to complete
            if simplify_success:
                await asyncio.sleep(2)
            
            # Find and click submit button
            submit_success = await self.find_and_click_submit(page)
            
            if not submit_success:
                logger.error("Failed to find/click submit button")
                return False
            
            # Wait for confirmation
            confirmation = await self.wait_for_submission_confirmation(page)
            
            if confirmation:
                logger.info(f"✅ Successfully applied to {job.title} at {job.company}")
                return True
            else:
                logger.warning(f"⚠️  Submitted but couldn't confirm success for {job.title}")
                return True  # Assume success if we clicked submit
                
        except Exception as e:
            logger.error(f"❌ Error processing {job.title}: {e}")
            return False
            
        finally:
            await page.close()
    
    async def update_notion_status(self, job_id: str, status: str):
        """Update job status in Notion (optional)"""
        url = f'https://api.notion.com/v1/pages/{job_id}'
        
        payload = {
            'properties': {
                'Status': {
                    'rich_text': [{'text': {'content': status}}]
                }
            }
        }
        
        try:
            async with self.session.patch(url, json=payload) as response:
                if response.status == 200:
                    logger.debug(f"Updated status for job {job_id}: {status}")
                else:
                    logger.warning(f"Failed to update status: {response.status}")
        except Exception as e:
            logger.warning(f"Error updating status: {e}")
    
    async def run_automation(self, delay_between_jobs: int = 10):
        """Run the complete automation"""
        try:
            # Setup
            await self.setup_session()
            await self.setup_browser()
            
            # Get jobs to process
            jobs = await self.get_greenhouse_jobs()
            
            if not jobs:
                logger.info("No Greenhouse jobs found to process")
                return
            
            logger.info(f"Starting automation for {len(jobs)} jobs")
            
            successful = 0
            failed = 0
            
            # Process each job
            for i, job in enumerate(jobs, 1):
                logger.info(f"\n--- Processing job {i}/{len(jobs)} ---")
                
                success = await self.process_greenhouse_application(job)
                
                if success:
                    successful += 1
                    await self.update_notion_status(job.id, "Applied")
                else:
                    failed += 1
                    await self.update_notion_status(job.id, "Failed")
                
                # Delay between applications (be respectful)
                if i < len(jobs):
                    logger.info(f"Waiting {delay_between_jobs} seconds before next application...")
                    await asyncio.sleep(delay_between_jobs)
            
            # Summary
            logger.info(f"\n=== AUTOMATION COMPLETE ===")
            logger.info(f"Total jobs: {len(jobs)}")
            logger.info(f"Successful: {successful}")
            logger.info(f"Failed: {failed}")
            logger.info(f"Success rate: {successful/len(jobs)*100:.1f}%")
            
        except Exception as e:
            logger.error(f"Automation error: {e}")
            
        finally:
            if self.session:
                await self.session.close()
            if self.browser:
                await self.browser.close()

async def main():
    """Main function"""
    # Configuration
    NOTION_TOKEN = os.getenv('NOTION_API_KEY')
    DATABASE_ID = os.getenv('NOTION_DB_ID_TEST')  # Using test database
    
    if not NOTION_TOKEN or not DATABASE_ID:
        logger.error("Please set NOTION_API_KEY and NOTION_DB_ID_TEST environment variables")
        return
    
    # Create automation instance
    automation = GreenhouseAutomation(NOTION_TOKEN, DATABASE_ID)
    
    # Run automation
    await automation.run_automation(delay_between_jobs=15)  # 15 second delay between jobs

if __name__ == "__main__":
    asyncio.run(main())