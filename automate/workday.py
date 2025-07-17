import asyncio
import os
import logging
import time
from typing import List, Dict, Optional
from dataclasses import dataclass

import aiohttp
import openai
from playwright.async_api import async_playwright, Page
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('workday_automation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class WorkdayJob:
    """Data class for Workday job applications"""
    id: str
    title: str
    company: str
    apply_link: str

class WorkdayAutomation:
    def __init__(self, notion_token: str, database_id: str, user_data_dir: str = "./browser_data"):
        self.notion_token = notion_token
        self.database_id = database_id
        self.user_data_dir = user_data_dir
        self.session = None
        self.browser = None
        self.context = None
        
        # Initialize OpenAI
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Your professional background (customize this!)
        self.professional_profile = {
            "name": "Your Name",
            "experience": "3+ years of software development experience",
            "skills": "Python, JavaScript, React, Node.js, SQL, AWS, Docker",
            "education": "Bachelor's degree in Computer Science", 
            "achievements": "Led development of multiple web applications, improved system performance by 40%",
            "interests": "Full-stack development, automation, machine learning",
            "work_authorization": "Authorized to work in the United States",
            "availability": "Available to start immediately"
        }
        
        # Simplify detection selectors
        self.simplify_indicators = [
            '[data-simplify="true"]',
            '.simplify-autofilled',
            '.simplify-detected',
            '.simplify-extension',
            'div[id*="simplify"]',
            'div[class*="simplify"]',
            'input[data-autofilled="true"]',
            'input[data-filled="true"]'
        ]
        
        # Workday-specific navigation selectors
        self.next_button_selectors = [
            'button:has-text("Next")',
            'button:has-text("Continue")',
            'button[data-automation-id*="next"]',
            'button[data-automation-id*="continue"]',
            'button[aria-label*="Next"]',
            'button[aria-label*="Continue"]',
            '.next-button',
            '.continue-button',
            'button[type="button"]:has-text("Next")',
            'input[type="button"][value*="Next"]',
            'input[type="button"][value*="Continue"]'
        ]
        
        # Submit button selectors (final page)
        self.submit_selectors = [
            'button:has-text("Submit Application")',
            'button:has-text("Submit")',
            'button[data-automation-id*="submit"]',
            'button[aria-label*="Submit"]',
            'input[type="submit"][value*="Submit"]',
            'input[type="button"][value*="Submit"]',
            '.submit-button',
            'button:has-text("Apply")',
            'button:has-text("Complete Application")'
        ]
        
        # Progress indicators for page detection
        self.progress_indicators = [
            '[data-automation-id*="step"]',
            '[data-automation-id*="progress"]',
            '.progress-indicator',
            '.step-indicator',
            'text=/Step \\d+ of \\d+/',
            'text=/\\d+ of \\d+/',
            '.progress-bar'
        ]
        
        # Success indicators
        self.success_indicators = [
            'text=Application submitted',
            'text=Thank you for applying',
            'text=Application received',
            'text=Successfully submitted',
            'text=Your application has been submitted',
            '.confirmation',
            '.success-message',
            '[data-automation-id*="success"]',
            '[data-automation-id*="confirmation"]'
        ]
        
        # Default values for common fields
        self.default_values = {
            'cover_letter': """Dear Hiring Manager,

I am excited to apply for this position. With my background in software development and passion for technology, I believe I would be a valuable addition to your team. I am eager to contribute my skills and learn from your experienced team.

Thank you for considering my application. I look forward to hearing from you.

Best regards""",
            
            'why_interested': "I am passionate about this role because it aligns perfectly with my career goals and allows me to apply my technical skills in a meaningful way. Your company's mission and values resonate with me, and I am excited about the opportunity to contribute to your team's success.",
            
            'availability': "I am available to start within two weeks and can work full-time.",
            
            'salary_expectation': "Negotiable based on the complete compensation package",
            
            'additional_info': "I am authorized to work in the United States and do not require visa sponsorship."
        }
        
        # Field patterns
        self.field_patterns = {
            'cover_letter': [
                'textarea[name*="cover"]',
                'textarea[placeholder*="cover"]',
                'textarea[id*="cover"]',
                'textarea[aria-label*="cover"]',
                'textarea:has(~ label:has-text("Cover Letter"))',
                'textarea[name*="letter"]'
            ],
            'why_interested': [
                'textarea[name*="why"]',
                'textarea[placeholder*="why"]',
                'textarea[placeholder*="interested"]',
                'textarea[name*="motivation"]',
                'textarea:has(~ label:has-text("Why"))',
                'textarea[name*="interest"]'
            ],
            'availability': [
                'input[name*="availability"]',
                'input[placeholder*="availability"]',
                'textarea[name*="availability"]',
                'input[name*="start"]',
                'input[placeholder*="start date"]'
            ],
            'additional_info': [
                'textarea[name*="additional"]',
                'textarea[placeholder*="additional"]',
                'textarea[name*="other"]',
                'textarea[placeholder*="anything else"]',
                'textarea[name*="comments"]'
            ]
        }
    
    async def setup_session(self):
        """Setup aiohttp session for Notion API"""
        headers = {
            'Authorization': f'Bearer {self.notion_token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
        self.session = aiohttp.ClientSession(headers=headers)

    async def get_workday_jobs(self) -> List[WorkdayJob]:
        """Get Workday jobs from Notion database"""
        url = f'https://api.notion.com/v1/databases/{self.database_id}/query'
        
        jobs = []
        
        try:
            logger.info("Fetching Workday jobs from database...")
            logger.info(f"Using database ID: {self.database_id}")
            
            async with self.session.post(url, json={}) as response:
                logger.info(f"Response status: {response.status}")
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to fetch jobs: {response.status}")
                    logger.error(f"Error response: {error_text}")
                    return jobs
                
                data = await response.json()
                all_results = data.get('results', [])
                logger.info(f"Total jobs in database: {len(all_results)}")
                
                if len(all_results) == 0:
                    logger.warning("No results found in database!")
                    return jobs
                
                # Filter for Workday jobs
                workday_jobs = []
                for result in all_results:
                    props = result.get('properties', {})
                    
                    type_prop = props.get('Type', {})
                    type_value = ""
                    if type_prop.get('rich_text') and len(type_prop['rich_text']) > 0:
                        type_value = type_prop['rich_text'][0]['text']['content']
                    
                    apply_url_prop = props.get('Apply URL', {})
                    apply_url = apply_url_prop.get('url', '')
                    
                    if type_value.lower() == "workday" and apply_url:
                        job = self._parse_workday_job(result)
                        if job:
                            workday_jobs.append(job)
                            logger.info(f"✅ Found Workday job: {job.title} at {job.company}")
                
                logger.info(f"\nFound {len(workday_jobs)} Workday jobs to process")
                return workday_jobs
                
        except Exception as e:
            logger.error(f"Error fetching Workday jobs: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return jobs
    
    def _parse_workday_job(self, result: Dict) -> Optional[WorkdayJob]:
        """Parse Notion result into WorkdayJob"""
        try:
            props = result.get('properties', {})
            
            title_prop = props.get('Job Title', {})
            title = ""
            if title_prop.get('title'):
                title = title_prop['title'][0]['text']['content']
            
            company_prop = props.get('Company', {})
            company = ""
            if company_prop.get('rich_text'):
                company = company_prop['rich_text'][0]['text']['content']
            
            apply_link_prop = props.get('Apply URL', {})
            apply_link = apply_link_prop.get('url', '')
            
            if not apply_link:
                return None
            
            return WorkdayJob(
                id=result['id'],
                title=title,
                company=company,
                apply_link=apply_link
            )
            
        except Exception as e:
            logger.error(f"Error parsing job: {e}")
            return None
    
    async def setup_browser(self):
        """Initialize browser with existing profile and load Simplify extension"""
        playwright = await async_playwright().start()
        
        self.browser = await playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=False,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-first-run',
                '--disable-background-networking',
                '--disable-background-timer-throttling',
                '--load-extension=./extensions/Simplify',
                '--disable-extensions-except=./extensions/Simplify'
            ]
        )
        
        self.context = self.browser
        logger.info("Browser initialized with existing profile and Simplify extension")
        
        await asyncio.sleep(3)
        
        # Verify Simplify extension
        page = await self.context.new_page()
        try:
            await page.goto('chrome://extensions/', timeout=10000)
            await asyncio.sleep(2)
            
            simplify_elements = await page.query_selector_all('text=Simplify')
            if simplify_elements:
                logger.info("✅ Simplify extension successfully loaded!")
                
                enabled_toggle = await page.query_selector('cr-toggle[checked]')
                if enabled_toggle:
                    logger.info("✅ Simplify extension is enabled")
                else:
                    logger.warning("⚠️ Simplify extension loaded but may not be enabled")
            else:
                logger.warning("⚠️ Simplify extension not found in extensions list")
                
        except Exception as e:
            logger.warning(f"Could not verify extension status: {e}")
        finally:
            await page.close()
    
    async def trigger_simplify_autofill(self, page: Page) -> bool:
        """Actively trigger Simplify's autofill button"""
        logger.info("Looking for Simplify autofill button...")
        
        simplify_button_selectors = [
            'button:has-text("Autofill this page")',
            'button:has-text("Autofill")',
            '[aria-label*="Autofill"]',
            '[title*="Autofill"]',
            '.simplify-autofill-button',
            'button[class*="simplify"]',
            'div[id*="simplify"] button',
            'iframe[src*="simplify"] button',
            'button:has-text("Fill")',
            'button:has-text("Auto Fill")'
        ]
        
        await asyncio.sleep(3)
        
        for selector in simplify_button_selectors:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    logger.info(f"Found Simplify button with selector: {selector}")
                    await button.click()
                    logger.info("✅ Clicked Simplify autofill button!")
                    return True
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue
        
        # Check iframes for Simplify
        try:
            frames = page.frames
            for frame in frames:
                try:
                    if 'simplify' in frame.url.lower():
                        for selector in simplify_button_selectors:
                            button = await frame.query_selector(selector)
                            if button and await button.is_visible():
                                logger.info(f"Found Simplify button in iframe: {selector}")
                                await button.click()
                                logger.info("✅ Clicked Simplify autofill button in iframe!")
                                return True
                except:
                    continue
        except:
            pass
        
        logger.warning("❌ Could not find Simplify autofill button")
        return False
    
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
                
                # Check if fields are filled
                filled_inputs = await page.evaluate("""
                    () => {
                        const inputs = document.querySelectorAll('input[type="text"], input[type="email"], textarea, select');
                        let filledCount = 0;
                        inputs.forEach(input => {
                            if (input.value && input.value.trim().length > 0) {
                                filledCount++;
                            }
                        });
                        return filledCount;
                    }
                """)
                
                if filled_inputs >= 3:
                    logger.info(f"Detected {filled_inputs} filled fields - assuming Simplify completed")
                    return True
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.warning(f"Error checking Simplify status: {e}")
                await asyncio.sleep(1)
        
        logger.warning("Simplify autofill timeout - proceeding anyway")
        return False
    
    async def detect_page_info(self, page: Page) -> Dict[str, any]:
        """Detect current page information and progress"""
        page_info = {
            'current_page': 1,
            'total_pages': None,
            'is_final_page': False,
            'has_next_button': False,
            'has_submit_button': False,
            'progress_text': ""
        }
        
        try:
            # Check for progress indicators
            for selector in self.progress_indicators:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        text = await element.inner_text()
                        page_info['progress_text'] = text.strip()
                        
                        # Try to extract page numbers from text like "Step 2 of 5"
                        import re
                        match = re.search(r'(\d+)\s*of\s*(\d+)', text)
                        if match:
                            page_info['current_page'] = int(match.group(1))
                            page_info['total_pages'] = int(match.group(2))
                            page_info['is_final_page'] = page_info['current_page'] == page_info['total_pages']
                        break
                except:
                    continue
            
            # Check for Next button
            for selector in self.next_button_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        is_disabled = await button.get_attribute('disabled')
                        if not is_disabled:
                            page_info['has_next_button'] = True
                            break
                except:
                    continue
            
            # Check for Submit button
            for selector in self.submit_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button and await button.is_visible():
                        is_disabled = await button.get_attribute('disabled')
                        if not is_disabled:
                            page_info['has_submit_button'] = True
                            page_info['is_final_page'] = True
                            break
                except:
                    continue
            
            # If no progress indicator found but has submit button, assume final page
            if page_info['has_submit_button'] and not page_info['progress_text']:
                page_info['is_final_page'] = True
            
            logger.info(f"Page info: {page_info}")
            return page_info
            
        except Exception as e:
            logger.warning(f"Error detecting page info: {e}")
            return page_info
    
    async def navigate_to_next_page(self, page: Page) -> bool:
        """Navigate to the next page by clicking Next button"""
        logger.info("Looking for Next button...")
        
        for selector in self.next_button_selectors:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    is_disabled = await button.get_attribute('disabled')
                    if not is_disabled:
                        logger.info(f"Found Next button: {selector}")
                        
                        # Get current URL to detect navigation
                        current_url = page.url
                        
                        # Scroll button into view and click
                        await button.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        await button.click()
                        
                        logger.info("Next button clicked!")
                        
                        # Wait for page to navigate or content to change
                        await self.wait_for_page_navigation(page, current_url)
                        
                        return True
                        
            except Exception as e:
                logger.debug(f"Next button selector {selector} failed: {e}")
                continue
        
        logger.error("No Next button found!")
        return False
    
    async def wait_for_page_navigation(self, page: Page, previous_url: str, timeout: int = 10):
        """Wait for page navigation or content change after clicking Next"""
        logger.info("Waiting for page navigation...")
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                current_url = page.url
                
                # Check if URL changed
                if current_url != previous_url:
                    logger.info(f"URL changed: {previous_url} -> {current_url}")
                    await page.wait_for_load_state('domcontentloaded')
                    await asyncio.sleep(2)  # Extra time for dynamic content
                    return
                
                # Check if page content significantly changed
                page_ready = await page.evaluate("""
                    () => {
                        // Check if page is still loading
                        if (document.readyState !== 'complete') return false;
                        
                        // Check for common Workday loading indicators
                        const loadingElements = document.querySelectorAll(
                            '[data-automation-id*="loading"], .loading, .spinner, [aria-label*="loading"]'
                        );
                        
                        return loadingElements.length === 0;
                    }
                """)
                
                if page_ready:
                    logger.info("Page appears to be ready")
                    await asyncio.sleep(1)  # Small buffer
                    return
                
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"Error waiting for navigation: {e}")
                await asyncio.sleep(0.5)
        
        logger.warning("Page navigation timeout - proceeding anyway")
    
    async def generate_intelligent_response(self, question: str, field_context: dict, job: WorkdayJob) -> str:
        """Use OpenAI to generate intelligent responses to application questions"""
        try:
            # Try quick response first
            quick_response = self._get_quick_response(question, field_context)
            if quick_response:
                logger.info(f"✅ Used quick response for: '{question[:50]}...'")
                return quick_response
            
            prompt = f"""You are filling out a job application. Generate CONCISE, DIRECT responses. Follow these strict rules:

RESPONSE RULES:
1. For dropdown/select fields: Give 1-3 words maximum (e.g., "Yes", "Bachelor's", "3-5 years")
2. For salary questions: Just "90000" (or "$90,000" if currency format needed)
3. For start date/availability: Always "2 weeks"
4. For text fields: Be SPARTAN - no fluff, 50-150 words maximum
5. Be direct and professional, avoid flowery language
6. Adapt to different phrasings of similar questions

JOB DETAILS:
- Position: {job.title}
- Company: {job.company}

APPLICANT PROFILE:
- Experience: {self.professional_profile['experience']}
- Skills: {self.professional_profile['skills']}
- Education: {self.professional_profile['education']}

FIELD TYPE: {field_context.get('tag', 'unknown')}
QUESTION: {question}

Generate a CONCISE, appropriate response:"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a concise job application assistant. Give direct, spartan responses with no fluff."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            answer = response.choices[0].message.content.strip()
            logger.info(f"✅ Generated AI response for: '{question[:50]}...'")
            return answer
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return self._get_quick_response(question, field_context) or "See resume for details"
    
    def _get_quick_response(self, question: str, field_context: dict) -> Optional[str]:
        """Fast rule-based responses for common question patterns"""
        question_lower = question.lower()
        field_type = field_context.get('tag', '').lower()
        
        # Salary questions - always 90,000
        if any(word in question_lower for word in ['salary', 'compensation', 'pay', 'wage', 'expected pay']):
            if '$' in question or 'dollar' in question_lower:
                return "$90,000"
            return "90000"
        
        # Start date / availability - always 2 weeks
        if any(phrase in question_lower for phrase in [
            'start date', 'available to start', 'begin work', 'earliest start', 
            'when can you start', 'availability', 'available to begin',
            'start immediately', 'notice period', 'when available'
        ]):
            return "2 weeks"
        
        # Work authorization - Yes
        if any(phrase in question_lower for phrase in [
            'authorized to work', 'work authorization', 'legal right to work',
            'eligible to work', 'visa', 'work permit', 'citizen', 'green card'
        ]):
            return "Yes"
        
        # Willing to relocate
        if any(phrase in question_lower for phrase in [
            'willing to relocate', 'relocate', 'move to', 'open to relocation'
        ]):
            return "Yes"
        
        # Travel requirements
        if any(phrase in question_lower for phrase in [
            'willing to travel', 'travel required', 'travel up to'
        ]):
            return "Yes"
        
        # Background check / drug test
        if any(phrase in question_lower for phrase in [
            'background check', 'drug test', 'screening', 'background screening'
        ]):
            return "Yes"
        
        # Years of experience
        if any(phrase in question_lower for phrase in [
            'years of experience', 'how many years', 'experience in'
        ]):
            return "3-5 years"
        
        # Education level
        if any(phrase in question_lower for phrase in [
            'education level', 'degree', 'education background'
        ]):
            return "Bachelor's degree"
        
        # Cover letter or why interested (spartan version)
        if any(phrase in question_lower for phrase in [
            'cover letter', 'why interested', 'why apply', 'why this position'
        ]):
            return f"I am interested in this {self.professional_profile.get('name', 'role')} position because it aligns with my technical background and career goals. My experience in software development makes me a strong fit for this position."
        
        # References available
        if any(phrase in question_lower for phrase in [
            'references', 'provide references', 'reference available'
        ]):
            return "Available upon request"
        
        # For dropdowns/selects
        if field_type == 'select':
            if 'yes' in question_lower or 'willing' in question_lower or 'authorized' in question_lower:
                return "Yes"
            elif 'experience' in question_lower:
                return "3-5 years"
            elif 'education' in question_lower or 'degree' in question_lower:
                return "Bachelor's"
        
        return None
    
    async def fill_missing_required_fields(self, page: Page, job: WorkdayJob) -> bool:
        """Fill any required fields that Simplify missed using AI"""
        logger.info("Checking for missing required fields...")
        
        fields_filled = 0
        
        try:
            empty_required_fields = await page.evaluate("""
                () => {
                    const fields = [];
                    
                    const requiredElements = document.querySelectorAll(
                        'input[required], textarea[required], select[required], ' +
                        'input[aria-required="true"], textarea[aria-required="true"], select[aria-required="true"], ' +
                        '.required input, .required textarea, .required select, ' +
                        '[data-automation-id*="required"] input, [data-automation-id*="required"] textarea, [data-automation-id*="required"] select'
                    );
                    
                    requiredElements.forEach(element => {
                        const value = element.value || '';
                        if (value.trim() === '' || value === 'Select an option' || value === 'Please select') {
                            
                            let question = '';
                            
                            // Try to find label or question text
                            const label = element.labels?.[0]?.textContent || 
                                         document.querySelector(`label[for="${element.id}"]`)?.textContent;
                            
                            const parent = element.closest('div, fieldset, section');
                            if (parent) {
                                const prevText = parent.querySelector('label, legend, h3, h4, p, span');
                                if (prevText && prevText.textContent) {
                                    question = prevText.textContent;
                                }
                            }
                            
                            if (!question) {
                                question = element.placeholder || element.name || 'Please provide information';
                            }
                            
                            fields.push({
                                tag: element.tagName.toLowerCase(),
                                type: element.type || '',
                                name: element.name || '',
                                id: element.id || '',
                                placeholder: element.placeholder || '',
                                className: element.className || '',
                                ariaLabel: element.getAttribute('aria-label') || '',
                                question: question.trim(),
                                selector: element.name ? `[name="${element.name}"]` : `[id="${element.id}"]`
                            });
                        }
                    });
                    
                    return fields;
                }
            """)
            
            logger.info(f"Found {len(empty_required_fields)} empty required fields")
            
            for field in empty_required_fields:
                logger.info(f"Processing field: {field['question']}")
                
                # Try pattern-based filling first
                filled = await self._fill_field_by_pattern(page, field)
                if filled:
                    fields_filled += 1
                    continue
                
                # Handle different field types
                if field['tag'] == 'select':
                    filled = await self._fill_select_field(page, field)
                    if filled:
                        fields_filled += 1
                        continue
                
                if field['type'] == 'checkbox':
                    filled = await self._fill_checkbox_field(page, field)
                    if filled:
                        fields_filled += 1
                        continue
                
                if field['tag'] in ['input', 'textarea'] and field['type'] in ['text', 'email', '']:
                    filled = await self._fill_with_ai(page, field, job)
                    if filled:
                        fields_filled += 1
                        continue
                
                # Fallback: generic field filling
                await self._fill_generic_field(page, field)
                fields_filled += 1
            
            logger.info(f"✅ Filled {fields_filled} missing required fields")
            return fields_filled > 0
            
        except Exception as e:
            logger.error(f"Error filling missing fields: {e}")
            return False
    
    async def _fill_with_ai(self, page: Page, field: dict, job: WorkdayJob) -> bool:
        """Fill text field using AI-generated response"""
        try:
            question = field['question']
            if not question or len(question.strip()) < 3:
                return False
            
            logger.info(f"🤖 Generating AI response for: '{question}'")
            
            ai_response = await self.generate_intelligent_response(question, field, job)
            
            selector = field['selector']
            element = await page.query_selector(selector)
            
            if element:
                await element.fill(ai_response)
                logger.info(f"✅ Filled field with AI response (length: {len(ai_response)})")
                return True
            else:
                logger.warning(f"Could not find element with selector: {selector}")
                return False
                
        except Exception as e:
            logger.error(f"Error filling field with AI: {e}")
            return False
    
    async def _fill_field_by_pattern(self, page: Page, field: dict) -> bool:
        """Fill field based on known patterns"""
        field_text = f"{field['name']} {field['placeholder']} {field['ariaLabel']}".lower()
        
        for pattern_type, selectors in self.field_patterns.items():
            for selector in selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        element_name = await element.get_attribute('name') or ''
                        element_id = await element.get_attribute('id') or ''
                        element_placeholder = await element.get_attribute('placeholder') or ''
                        
                        if (element_name == field['name'] or 
                            element_id == field['id'] or
                            (element_placeholder and element_placeholder == field['placeholder'])):
                            
                            await element.fill(self.default_values[pattern_type])
                            logger.info(f"✅ Filled {pattern_type} field with default value")
                            return True
                except:
                    continue
        
        return False
    
    async def _fill_select_field(self, page: Page, field: dict) -> bool:
        """Fill select dropdown with appropriate option"""
        try:
            selector = f"select[name='{field['name']}']" if field['name'] else f"select[id='{field['id']}']"
            select_element = await page.query_selector(selector)
            
            if not select_element:
                return False
            
            options = await page.evaluate(f"""
                () => {{
                    const select = document.querySelector("{selector}");
                    if (!select) return [];
                    return Array.from(select.options).map(option => ({{
                        value: option.value,
                        text: option.text
                    }}));
                }}
            """)
            
            if not options or len(options) <= 1:
                return False
            
            field_context = f"{field['name']} {field['placeholder']}".lower()
            
            # Country selection
            if 'country' in field_context:
                for option in options:
                    if 'united states' in option['text'].lower() or 'us' in option['text'].lower():
                        await select_element.select_option(option['value'])
                        logger.info(f"✅ Selected country: {option['text']}")
                        return True
            
            # Experience selection
            elif 'experience' in field_context or 'years' in field_context:
                for option in options:
                    if '2-5' in option['text'] or '3-5' in option['text'] or '1-3' in option['text']:
                        await select_element.select_option(option['value'])
                        logger.info(f"✅ Selected experience: {option['text']}")
                        return True
            
            # Education selection
            elif 'education' in field_context or 'degree' in field_context:
                for option in options:
                    if 'bachelor' in option['text'].lower() or 'master' in option['text'].lower():
                        await select_element.select_option(option['value'])
                        logger.info(f"✅ Selected education: {option['text']}")
                        return True
            
            # Default: select first non-empty option
            for option in options[1:]:
                if option['value'] and option['value'] != '':
                    await select_element.select_option(option['value'])
                    logger.info(f"✅ Selected default option: {option['text']}")
                    return True
            
        except Exception as e:
            logger.warning(f"Error filling select field: {e}")
            
        return False
    
    async def _fill_checkbox_field(self, page: Page, field: dict) -> bool:
        """Fill checkbox fields (usually terms and conditions)"""
        try:
            selector = f"input[name='{field['name']}']" if field['name'] else f"input[id='{field['id']}']"
            checkbox = await page.query_selector(selector)
            
            if checkbox:
                field_context = f"{field['name']} {field['placeholder']} {field['ariaLabel']}".lower()
                if any(term in field_context for term in ['terms', 'condition', 'agree', 'consent', 'privacy']):
                    await checkbox.check()
                    logger.info("✅ Checked terms/conditions checkbox")
                    return True
                    
        except Exception as e:
            logger.warning(f"Error filling checkbox: {e}")
            
        return False
    
    async def _fill_generic_field(self, page: Page, field: dict):
        """Fill any remaining field with generic content"""
        try:
            selector = f"input[name='{field['name']}']" if field['name'] else f"input[id='{field['id']}']"
            element = await page.query_selector(selector)
            
            if element:
                field_context = f"{field['name']} {field['placeholder']}".lower()
                
                if 'phone' in field_context:
                    await element.fill("555-123-4567")
                elif 'linkedin' in field_context:
                    await element.fill("https://linkedin.com/in/yourprofile")
                elif 'github' in field_context:
                    await element.fill("https://github.com/yourusername")
                elif 'website' in field_context or 'portfolio' in field_context:
                    await element.fill("https://yourportfolio.com")
                else:
                    await element.fill("Please see resume for details")
                
                logger.info(f"✅ Filled generic field: {field['name']}")
                
        except Exception as e:
            logger.warning(f"Error filling generic field: {e}")
    
    async def confirm_page_submission(self, job: WorkdayJob, page: Page, page_info: Dict) -> bool:
        """Ask user for confirmation before proceeding with current page"""
        current_page = page_info.get('current_page', 1)
        total_pages = page_info.get('total_pages', '?')
        progress_text = page_info.get('progress_text', '')
        is_final = page_info.get('is_final_page', False)
        
        print(f"\n{'='*60}")
        if is_final:
            print(f"🚀 READY TO SUBMIT APPLICATION")
        else:
            print(f"📄 PAGE {current_page} OF {total_pages} COMPLETED")
        print(f"{'='*60}")
        print(f"Job: {job.title}")
        print(f"Company: {job.company}")
        if progress_text:
            print(f"Progress: {progress_text}")
        print(f"{'='*60}")
        
        try:
            filled_fields = await page.evaluate("""
                () => {
                    const fields = [];
                    const inputs = document.querySelectorAll('input[type="text"], input[type="email"], textarea, select');
                    
                    inputs.forEach(input => {
                        if (input.value && input.value.trim() !== '') {
                            const label = input.labels?.[0]?.textContent || 
                                         input.getAttribute('aria-label') || 
                                         input.getAttribute('placeholder') || 
                                         input.name || 
                                         'Unknown field';
                            
                            let value = input.value;
                            if (value.length > 50) {
                                value = value.substring(0, 50) + '...';
                            }
                            
                            fields.push({
                                label: label.trim(),
                                value: value.trim()
                            });
                        }
                    });
                    
                    return fields;
                }
            """)
            
            if filled_fields:
                print(f"\n📝 FILLED FIELDS ON THIS PAGE:")
                for i, field in enumerate(filled_fields[:10], 1):
                    print(f"  {i}. {field['label']}: {field['value']}")
                
                if len(filled_fields) > 10:
                    print(f"  ... and {len(filled_fields) - 10} more fields")
            
        except Exception as e:
            logger.warning(f"Could not display form preview: {e}")
        
        print(f"\n{'='*60}")
        print("OPTIONS:")
        if is_final:
            print("  [y] Yes - Submit the application")
            print("  [n] No - Skip this application")
        else:
            print("  [y] Yes - Continue to next page")
            print("  [n] No - Skip this application")
        print("  [v] View browser - Inspect the form manually")
        print("  [e] Edit - Pause to manually edit form")
        print("  [q] Quit - Stop automation")
        print(f"{'='*60}")
        
        while True:
            try:
                action = "submit" if is_final else "continue"
                choice = input(f"\nWhat would you like to do? [y/n/v/e/q]: ").lower().strip()
                
                if choice in ['y', 'yes']:
                    print(f"✅ Proceeding to {action}...")
                    return True
                    
                elif choice in ['n', 'no']:
                    print("❌ Skipping this application")
                    return False
                    
                elif choice in ['v', 'view']:
                    print("👁️  Check the browser window to review the form")
                    print("Press Enter when you're ready to choose an option...")
                    input()
                    continue
                    
                elif choice in ['e', 'edit']:
                    print("✏️  Pausing for manual editing...")
                    print("Make any changes in the browser window, then press Enter to continue...")
                    input()
                    continue
                    
                elif choice in ['q', 'quit']:
                    print("🛑 Stopping automation")
                    raise KeyboardInterrupt("User requested to quit")
                    
                else:
                    print("❌ Invalid choice. Please enter y, n, v, e, or q")
                    
            except KeyboardInterrupt:
                print("\n🛑 Automation stopped by user")
                raise
            except EOFError:
                print("\n❌ Input interrupted, skipping application")
                return False
    
    async def find_and_click_submit(self, page: Page) -> bool:
        """Find and click the submit button on final page"""
        logger.info("Looking for submit button...")
        
        for selector in self.submit_selectors:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible():
                    is_disabled = await button.get_attribute('disabled')
                    if not is_disabled:
                        logger.info(f"Found submit button: {selector}")
                        
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
            # Check for success indicators
            for indicator in self.success_indicators:
                try:
                    await page.wait_for_selector(indicator, timeout=timeout * 1000)
                    logger.info(f"Success confirmed via: {indicator}")
                    return True
                except:
                    continue
            
            # Check URL for success indicators
            await asyncio.sleep(3)
            current_url = page.url
            if any(word in current_url.lower() for word in ['thank', 'success', 'confirmation', 'submitted']):
                logger.info("Success inferred from URL change")
                return True
            
            # Check page title
            try:
                page_title = await page.title()
                if any(word in page_title.lower() for word in ['thank', 'success', 'confirmation', 'submitted']):
                    logger.info("Success inferred from page title")
                    return True
            except:
                pass
            
            logger.warning("Could not confirm submission success")
            return False
            
        except Exception as e:
            logger.error(f"Error waiting for confirmation: {e}")
            return False
    
    async def process_workday_application(self, job: WorkdayJob) -> bool:
        """Process a single Workday application with multi-page support"""
        logger.info(f"Processing: {job.title} at {job.company}")
        
        page = await self.context.new_page()
        
        try:
            logger.info(f"Navigating to: {job.apply_link}")
            await page.goto(job.apply_link, wait_until='domcontentloaded', timeout=30000)
            
            await asyncio.sleep(3)
            
            # Check if already applied
            already_applied_selectors = [
                'text=You have already applied',
                'text=Application already submitted',
                'text=Already applied',
                '[data-automation-id*="already-applied"]'
            ]
            
            for selector in already_applied_selectors:
                already_applied = await page.query_selector(selector)
                if already_applied:
                    logger.info("Already applied to this position - skipping")
                    return True
            
            # Multi-page processing loop
            page_count = 0
            max_pages = 10  # Safety limit to prevent infinite loops
            
            while page_count < max_pages:
                page_count += 1
                logger.info(f"\n--- Processing Page {page_count} ---")
                
                # Detect current page information
                page_info = await self.detect_page_info(page)
                
                # Step 1: Try to trigger Simplify's autofill button
                simplify_triggered = await self.trigger_simplify_autofill(page)
                
                # Step 2: Wait for Simplify to autofill
                simplify_success = await self.wait_for_simplify(page, timeout=20)
                
                if simplify_success:
                    await asyncio.sleep(2)
                
                # Step 3: Fill any missing required fields
                await self.fill_missing_required_fields(page, job)
                
                await asyncio.sleep(1)
                
                # Step 4: Ask for user confirmation
                should_continue = await self.confirm_page_submission(job, page, page_info)
                
                if not should_continue:
                    logger.info("User chose to skip this application")
                    return False
                
                # Step 5: Check if this is the final page
                if page_info['is_final_page'] or page_info['has_submit_button']:
                    logger.info("This is the final page - submitting application")
                    
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
                        return True
                
                # Step 6: Navigate to next page
                else:
                    logger.info("Navigating to next page...")
                    
                    navigation_success = await self.navigate_to_next_page(page)
                    
                    if not navigation_success:
                        logger.error("Failed to navigate to next page")
                        return False
                    
                    # Wait a bit for the new page to load
                    await asyncio.sleep(3)
                    
                    # Continue to next iteration of the loop
                    continue
            
            logger.error(f"Reached maximum page limit ({max_pages}) - stopping")
            return False
                
        except Exception as e:
            logger.error(f"❌ Error processing {job.title}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
            
        finally:
            await page.close()
    
    async def update_notion_status(self, job_id: str, status: str):
        """Update job status in Notion"""
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
    
    async def run_automation(self, delay_between_jobs: int = 15):
        """Run the complete Workday automation"""
        try:
            await self.setup_session()
            await self.setup_browser()
            
            jobs = await self.get_workday_jobs()
            
            if not jobs:
                logger.info("No Workday jobs found to process")
                return
            
            logger.info(f"Starting Workday automation for {len(jobs)} jobs")
            
            successful = 0
            failed = 0
            
            for i, job in enumerate(jobs, 1):
                logger.info(f"\n{'='*80}")
                logger.info(f"Processing job {i}/{len(jobs)}: {job.title} at {job.company}")
                logger.info(f"{'='*80}")
                
                success = await self.process_workday_application(job)
                
                if success:
                    successful += 1
                    await self.update_notion_status(job.id, "Applied")
                else:
                    failed += 1
                    await self.update_notion_status(job.id, "Failed")
                
                # Delay between jobs
                if i < len(jobs):
                    logger.info(f"Waiting {delay_between_jobs} seconds before next application...")
                    await asyncio.sleep(delay_between_jobs)
            
            # Final summary
            logger.info(f"\n{'='*80}")
            logger.info(f"🎉 WORKDAY AUTOMATION COMPLETE")
            logger.info(f"{'='*80}")
            logger.info(f"Total jobs processed: {len(jobs)}")
            logger.info(f"Successful applications: {successful}")
            logger.info(f"Failed applications: {failed}")
            logger.info(f"Success rate: {successful/len(jobs)*100:.1f}%")
            logger.info(f"{'='*80}")
            
        except KeyboardInterrupt:
            logger.info("\n🛑 Automation stopped by user")
            
        except Exception as e:
            logger.error(f"Automation error: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
        finally:
            if self.session:
                await self.session.close()
            if self.browser:
                await self.browser.close()

async def main():
    """Main function"""
    NOTION_TOKEN = os.getenv('NOTION_API_KEY')
    DATABASE_ID = os.getenv('NOTION_DB_ID_TEST')
    
    if not NOTION_TOKEN or not DATABASE_ID:
        logger.error("Please set NOTION_API_KEY and NOTION_DB_ID_TEST environment variables")
        return
    
    automation = WorkdayAutomation(NOTION_TOKEN, DATABASE_ID)
    await automation.run_automation(delay_between_jobs=20)

if __name__ == "__main__":
    asyncio.run(main())