import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm
from notion_client import Client as NotionClient
import tiktoken


# Configuration Constants
@dataclass
class Config:
    # OpenAI Models
    PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "gpt-4o-mini")
    BACKUP_MODEL = os.getenv("BACKUP_MODEL", "gpt-4o")
    
   # Cost per 1K tokens ($) - Updated with actual OpenAI pricing
    MODEL_COSTS = {
        "gpt-3.5-turbo": 0.0015,
        "gpt-4": 0.03,
        "gpt-4o": 0.005,     # Updated pricing
        "gpt-4o-mini": 0.00015,  # Updated pricing
        "gpt-5": 0.01125,
        "gpt-5-mini": 0.00225,
        "gpt-5-nano": 0.00045,
    }
    
    # Evaluation thresholds
    MIN_EXPLANATION_WORDS = 30
    VAGUE_RATING_RANGE = (4, 6)
    MAX_EXPLANATION_TOKENS = 300
    
    # File paths
    RESUME_FILE = "resume.txt"
    FILTERED_DIR = Path("../filtered") / "filter_data"
    CACHE_FILE = "rated_jobs.json"
    LOG_DIR = "logs"
    
    # Notion field limits
    NOTION_TEXT_LIMIT = 2000


class JobEvaluationError(Exception):
    """Custom exception for job evaluation errors"""
    pass


class Logger:
    """Enhanced logging with structured output"""
    
    def __init__(self, log_file_path: str):
        self.log_file = open(log_file_path, "w", encoding="utf-8")
        
        # Configure Python logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file_path),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def info(self, message: str):
        self.logger.info(message)
        self.log_file.write(f"{datetime.now().isoformat()} - INFO - {message}\n")
        self.log_file.flush()
    
    def error(self, message: str):
        self.logger.error(message)
        self.log_file.write(f"{datetime.now().isoformat()} - ERROR - {message}\n")
        self.log_file.flush()
    
    def warning(self, message: str):
        self.logger.warning(message)
        self.log_file.write(f"{datetime.now().isoformat()} - WARNING - {message}\n")
        self.log_file.flush()
    
    def close(self):
        self.log_file.close()


class OpenAIClient:
    """Enhanced OpenAI client with better error handling and token management"""
    
    def __init__(self, logger: Logger):
        self.client = OpenAI()
        self.logger = logger
        
        self.encoding = tiktoken.get_encoding("cl100k_base")
        
        # Usage tracking
        self.cumulative_tokens = 0
        self.cumulative_cost = 0.0
        self.gpt4_usage_count = 0
    
    def _calculate_cost(self, tokens: int, model: str) -> float:
        """Calculate API cost based on token usage"""
        cost_per_1k = Config.MODEL_COSTS.get(model, 0.01)  # fallback if unknown
        return (tokens / 1000) * cost_per_1k
    
    def _make_api_call(self, prompt: str, model: str, max_retries: int = 3) -> Tuple[str, int, float]:
        """Make OpenAI API call with retry logic"""
        for attempt in range(max_retries):
            try:
                # Use max_completion_tokens for newer models, max_tokens for older ones
                if model in ["gpt-5", "gpt-5-mini", "gpt-5-nano"]:
                    completion_params = {
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_completion_tokens": 400,
                        "timeout": 30
                    }
                else:
                    completion_params = {
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,
                        "max_tokens": 400,
                        "timeout": 30
                    }
                
                response = self.client.chat.completions.create(**completion_params)
                
                usage = response.usage
                tokens = usage.total_tokens
                cost = self._calculate_cost(tokens, model)
                
                return response.choices[0].message.content, tokens, cost
                
            except Exception as e:
                if attempt == max_retries - 1:
                    raise JobEvaluationError(f"OpenAI API call failed after {max_retries} attempts: {e}")
                
                wait_time = 2 ** attempt  # Exponential backoff
                self.logger.warning(f"API call attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
    
    def _needs_gpt4_evaluation(self, result: Dict[str, Any], explanation: str) -> bool:
        """Determine if GPT-4 evaluation is needed based on quality metrics"""
        rating = result.get("rating", 0)
        word_count = len(explanation.split())
        
        # Use GPT-4 for vague ratings or insufficient explanations
        is_vague_rating = Config.VAGUE_RATING_RANGE[0] <= rating <= Config.VAGUE_RATING_RANGE[1]
        is_insufficient_explanation = word_count < Config.MIN_EXPLANATION_WORDS
        
        # Check for generic phrases that indicate low-quality evaluation
        generic_phrases = [
            "good fit", "aligns well", "strong background", "relevant experience",
            "would be suitable", "meets requirements", "has experience"
        ]
        has_generic_language = any(phrase in explanation.lower() for phrase in generic_phrases)
        
        return is_vague_rating or is_insufficient_explanation or has_generic_language
    
    def evaluate_job_fit(self, job: Dict[str, Any], resume_text: str) -> Dict[str, Any]:
        """Evaluate job fit using enhanced prompt and model selection logic"""
        
        # Enhanced structured prompt
        prompt = self._create_evaluation_prompt(job, resume_text)
        
        # Initial evaluation with primary model
        content, tokens_primary, cost_primary = self._make_api_call(prompt, Config.PRIMARY_MODEL)
        
        try:
            result = json.loads(content)
            self._validate_evaluation_result(result)
            
            explanation = result.get("explanation", "")
            
            # Determine if GPT-4 re-evaluation is needed
            if self._needs_gpt4_evaluation(result, explanation):
                self.logger.info("🔁 Using backup model for higher quality evaluation")
                self.gpt4_usage_count += 1
                
                content, tokens_backup, cost_backup = self._make_api_call(prompt, Config.BACKUP_MODEL)
                result = json.loads(content)
                self._validate_evaluation_result(result)
                
                total_tokens = tokens_primary + tokens_backup
                total_cost = cost_primary + cost_backup
                explanation_tokens = len(self.encoding.encode(result["explanation"]))
            else:
                total_tokens = tokens_primary
                total_cost = cost_primary
                explanation_tokens = len(self.encoding.encode(result["explanation"]))
            
            # Update cumulative metrics
            self.cumulative_tokens += total_tokens
            self.cumulative_cost += total_cost
            
            # Log evaluation summary
            self._log_evaluation_summary(job, result, explanation_tokens, total_tokens, total_cost)
            
            return result
            
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}")
            self.logger.error(f"Raw content: {content}")
            raise JobEvaluationError(f"Failed to parse OpenAI response: {e}")
    
    def _create_evaluation_prompt(self, job: Dict[str, Any], resume_text: str) -> str:
        """Create enhanced structured evaluation prompt"""
        
        format_examples = '''
EVALUATION EXAMPLES:

✅ Strong Match (8-10):
{
  "rating": 8.5,
  "explanation": "CS degree + 3 years full-stack experience directly matches senior developer role requirements. React/Node.js expertise aligns with tech stack. Client-facing experience adds value for cross-functional collaboration. Automation background relevant for DevOps responsibilities. Slightly over-qualified but strong technical fit."
}

❌ Poor Match (1-4):
{
  "rating": 2.5,
  "explanation": "Role requires 5+ years embedded systems and C/C++ firmware development. Candidate has web development background with no hardware experience. Skill gap too large - would need 2+ years retraining. Not cost-effective hire for this specialized position."
}

🔄 Moderate Match (5-7):
{
  "rating": 6,
  "explanation": "Marketing background with some technical exposure matches product manager role partially. Lacks direct B2B SaaS experience and technical depth for API discussions. Could succeed with 6-month learning curve but other candidates likely stronger immediate fit."
}
'''
        
        return f"""You are a technical recruiter with 15+ years experience. Evaluate this candidate's job fit using a structured approach.

CANDIDATE RESUME:
{resume_text}

JOB DETAILS:
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Location: {job.get('location', 'N/A')}
Seniority: {job.get('seniorityLevel', 'N/A')}
Description: {job.get('description', 'N/A')}

EVALUATION FRAMEWORK:
Rate 1-10 based on these weighted criteria:
• Technical Skills Match (40%): Stack, languages, frameworks, tools
• Experience Level (25%): Years, seniority, scope of responsibility  
• Domain Relevance (20%): Industry, business model, problem space
• Soft Skills Alignment (15%): Client-facing, teamwork, communication

REQUIREMENTS:
- Be precise and specific about skill gaps or overlaps
- Reference concrete resume evidence
- Consider learning curve and ramp-up time
- Avoid generic phrases like "good fit" or "strong background"
- Stay under 300 tokens in explanation
- Use direct, factual language

OUTPUT FORMAT:
{{"rating": [1-10 number], "explanation": "[specific reasoning]"}}

{format_examples}
"""
    
    def _validate_evaluation_result(self, result: Dict[str, Any]):
        """Validate the evaluation result structure"""
        if not isinstance(result, dict):
            raise JobEvaluationError("Evaluation result must be a dictionary")
        
        if "rating" not in result:
            raise JobEvaluationError("Evaluation result missing 'rating' field")
        
        if "explanation" not in result:
            raise JobEvaluationError("Evaluation result missing 'explanation' field")
        
        rating = result["rating"]
        if not isinstance(rating, (int, float)) or not 1 <= rating <= 10:
            raise JobEvaluationError(f"Rating must be a number between 1-10, got: {rating}")
    
    def _log_evaluation_summary(self, job: Dict[str, Any], result: Dict[str, Any], 
                               explanation_tokens: int, total_tokens: int, total_cost: float):
        """Log structured evaluation summary"""
        self.logger.info("═" * 50)
        self.logger.info(f"JOB: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
        self.logger.info(f"RATING: {result['rating']}/10")
        self.logger.info(f"EXPLANATION: {result['explanation'][:100]}...")
        self.logger.info(f"TOKENS: {explanation_tokens} explanation | {total_tokens} total")
        self.logger.info(f"COST: ${total_cost:.4f} | CUMULATIVE: ${self.cumulative_cost:.4f}")
        self.logger.info("═" * 50)
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Get usage summary for final reporting"""
        return {
            "total_tokens": self.cumulative_tokens,
            "total_cost": self.cumulative_cost,
            "gpt4_calls": self.gpt4_usage_count
        }


class ApplicationTypeDetector:
    """Detects the type of application system from apply URLs"""
    
    # URL patterns for different application systems
    PATTERNS = {
        "Greenhouse": [
            "greenhouse.io", "boards.greenhouse.io", "app.greenhouse.io"
        ],
        "Workday": [
            "workday.com", "myworkdayjobs.com", "wd1.myworkdayjobs.com", 
            "wd5.myworkdayjobs.com", "workdayrecruiting.com"
        ],
        "Lever": [
            "lever.co", "jobs.lever.co"
        ],
        "BambooHR": [
            "bamboohr.com", "careers.bamboohr.com"
        ],
        "SmartRecruiters": [
            "smartrecruiters.com", "jobs.smartrecruiters.com"
        ],
        "Jobvite": [
            "jobvite.com", "app.jobvite.com"
        ],
        "Ashby": [
            "ashbyhq.com", "jobs.ashbyhq.com"
        ],
        "iCIMS": [
            "icims.com", "jobs.icims.com"
        ],
        "Taleo": [
            "taleo.net", "chk.tbe.taleo.net"
        ],
        "JazzHR": [
            "jazzhr.com", "recruiting.jazzhr.com"
        ],
        "LinkedIn": [
            "linkedin.com/jobs", "www.linkedin.com/jobs"
        ],
        "Indeed": [
            "indeed.com", "www.indeed.com"
        ],
        "AngelList": [
            "angel.co", "www.angel.co", "angellist.com"
        ],
        "ZipRecruiter": [
            "ziprecruiter.com", "www.ziprecruiter.com"
        ],
        "Glassdoor": [
            "glassdoor.com", "www.glassdoor.com"
        ]
    }
    
    @classmethod
    def detect_application_type(cls, apply_url: str) -> str:
        """
        Detect the application system type from the apply URL
        
        Args:
            apply_url: The URL to analyze
            
        Returns:
            String indicating the application type
        """
        if not apply_url or not isinstance(apply_url, str):
            return "Unknown"
        
        apply_url = apply_url.lower().strip()
        
        # Check each pattern
        for app_type, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in apply_url:
                    return app_type
        
        # Check for common company career page indicators
        if any(indicator in apply_url for indicator in [
            "/careers", "/jobs", "/career", "/job", "/apply", "/hiring"
        ]):
            return "Company Site"
        
        # Check for common ATS indicators in URL structure
        if any(ats_indicator in apply_url for ats_indicator in [
            "recruiting", "applicant", "candidate", "talent", "hr"
        ]):
            return "ATS (Other)"
        
        return "Company Site"


class NotionService:
    """Enhanced Notion client with better error handling"""
    
    def __init__(self, database_id: str, logger: Logger):
        self.client = NotionClient(auth=os.getenv("NOTION_API_KEY"))
        self.database_id = database_id
        self.logger = logger
        self.app_detector = ApplicationTypeDetector()
    
    def create_job_page(self, job: Dict[str, Any], max_retries: int = 3) -> bool:
        """Create a job page in Notion with retry logic"""
        for attempt in range(max_retries):
            try:
                properties = self._build_job_properties(job)
                
                self.client.pages.create(
                    parent={"database_id": self.database_id},
                    properties=properties
                )
                
                self.logger.info(f"✅ Added job ID {job.get('id', 'unknown')} to Notion")
                return True
                
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"❌ Failed to add job ID {job.get('id', 'unknown')} to Notion after {max_retries} attempts: {e}")
                    return False
                
                wait_time = 2 ** attempt
                self.logger.warning(f"Notion API attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
        
        return False
    
    def _build_job_properties(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build Notion properties from job data"""
        def safe_text(value: Any, max_length: int = Config.NOTION_TEXT_LIMIT) -> str:
            """Safely convert value to text with length limit"""
            if value is None:
                return ""
            text = str(value)
            return text[:max_length] if len(text) > max_length else text
        
        def safe_number(value: Any) -> int:
            """Safely convert value to number"""
            if value is None:
                return 0
            try:
                return int(value)
            except (ValueError, TypeError):
                return 0
        
        def safe_url(value: Any) -> str:
            """Safely convert value to URL"""
            if value is None or not str(value).startswith(('http://', 'https://')):
                return "https://www.linkedin.com"
            return str(value)
        
        # Detect application type from apply URL
        apply_url = job.get("applyUrl", "")
        application_type = self.app_detector.detect_application_type(apply_url)
        
        return {
            "Job Title": {"title": [{"text": {"content": safe_text(job.get("title", "Untitled"))}}]},
            "Company": {"rich_text": [{"text": {"content": safe_text(job.get("company", ""))}}]},
            "Location": {"rich_text": [{"text": {"content": safe_text(job.get("location", ""))}}]},
            "Rating": {"number": job.get("rating", 0)},
            "Explanation": {"rich_text": [{"text": {"content": safe_text(job.get("explanation", ""))}}]},
            "Link": {"url": safe_url(job.get("link"))},
            "Apply URL": {"url": safe_url(job.get("applyUrl"))},
            "Type": {"rich_text": [{"text": {"content": application_type}}]},
            "Date Posted": {"date": {"start": job.get("postedAt", "2025-01-01")}},
            "Job ID": {"rich_text": [{"text": {"content": safe_text(job.get("id", "0"))}}]},
            "Seniority Level": {"select": {"name": safe_text(job.get("seniorityLevel", "N/A"))}},
            "Employment Type": {"select": {"name": safe_text(job.get("employmentType", "N/A"))}},
            "Job Function": {"rich_text": [{"text": {"content": safe_text(job.get("jobFunction", ""))}}]},
            "Industries": {"rich_text": [{"text": {"content": safe_text(job.get("industries", ""))}}]},
            "Company Size": {"number": safe_number(job.get("companyEmployeesCount"))},
            "Applicants": {"number": safe_number(job.get("applicantsCount"))},
            "Company Description": {"rich_text": [{"text": {"content": safe_text(job.get("companyDescription", ""))}}]}
        }


class JobEvaluator:
    """Main job evaluation orchestrator"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.openai_client = OpenAIClient(self.logger)
        self.notion_client = NotionService(os.getenv("NOTION_DB_ID"), self.logger)
        self.cache = self._load_cache()
        
        # Metrics
        self.processed_count = 0
        self.skipped_count = 0
        self.failed_count = 0
    
    def _setup_logging(self) -> Logger:
        """Setup logging infrastructure"""
        os.makedirs(Config.LOG_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file_path = f"{Config.LOG_DIR}/enhanced_run_{timestamp}.log"
        return Logger(log_file_path)
    
    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load existing evaluation cache"""
        if os.path.exists(Config.CACHE_FILE):
            try:
                with open(Config.CACHE_FILE, "r", encoding="utf-8") as f:
                    cached_results = json.load(f)
                    return {str(job["id"]): job for job in cached_results}
            except Exception as e:
                self.logger.warning(f"Failed to load cache: {e}")
        return {}
    
    def _save_cache(self):
        """Save evaluation cache"""
        try:
            cache_list = list(self.cache.values())
            with open(Config.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_list, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save cache: {e}")
    
    def _load_resume(self) -> str:
        """Load resume text"""
        try:
            with open(Config.RESUME_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            raise JobEvaluationError(f"Resume file not found: {Config.RESUME_FILE}")
    
    def _load_jobs(self) -> List[Dict[str, Any]]:
        """Load latest filtered jobs"""
        try:
            filtered_dir = Path(Config.FILTERED_DIR)
            latest_filtered = max(filtered_dir.glob("filtered_jobs_*.json"), key=os.path.getmtime)
            
            with open(latest_filtered, "r", encoding="utf-8") as f:
                jobs = json.load(f)
                
            self.logger.info(f"Loaded {len(jobs)} jobs from {latest_filtered}")
            return jobs
            
        except ValueError:
            raise JobEvaluationError(f"No filtered job files found in {Config.FILTERED_DIR}")
        except Exception as e:
            raise JobEvaluationError(f"Failed to load jobs: {e}")
    
    def _validate_environment(self):
        """Validate required environment variables"""
        required_vars = ["OPENAI_API_KEY", "NOTION_API_KEY", "NOTION_DB_ID"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            raise JobEvaluationError(f"Missing required environment variables: {missing_vars}")
    
    def process_job(self, job: Dict[str, Any], resume_text: str) -> bool:
        """Process a single job evaluation"""
        job_id = str(job.get("id", "unknown"))
        
        # Check cache
        if job_id in self.cache:
            self.logger.info(f"⏩ Skipping cached job ID {job_id}")
            self.skipped_count += 1
            return True
        
        try:
            # Evaluate job fit
            evaluation = self.openai_client.evaluate_job_fit(job, resume_text)
            
            # Add evaluation to job data
            job["rating"] = evaluation["rating"]
            job["explanation"] = evaluation["explanation"]
            
            # Log application type detection
            apply_url = job.get("applyUrl", "")
            app_type = ApplicationTypeDetector.detect_application_type(apply_url)
            self.logger.info(f"🔗 Application Type: {app_type} ({apply_url[:50]}...)")
            
            # Push to Notion
            if self.notion_client.create_job_page(job):
                # Cache successful evaluation
                self.cache[job_id] = {
                    "id": job_id,
                    "rating": job["rating"],
                    "explanation": job["explanation"]
                }
                self.processed_count += 1
                return True
            else:
                self.failed_count += 1
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Error processing job '{job.get('title', 'unknown')}' at '{job.get('company', 'unknown')}': {e}")
            self.failed_count += 1
            return False
    
    def run(self):
        """Main execution method"""
        try:
            self.logger.info("🚀 Starting Enhanced Job Evaluation System")
            
            # Validate environment
            self._validate_environment()
            
            # Load data
            resume_text = self._load_resume()
            jobs = self._load_jobs()
            
            self.logger.info(f"📄 Resume loaded ({len(resume_text)} characters)")
            self.logger.info(f"📋 Found {len(self.cache)} cached evaluations")
            
            # Process jobs
            for job in tqdm(jobs, desc="Evaluating Jobs", unit="job"):
                self.process_job(job, resume_text)
                
                # Save cache periodically
                if self.processed_count % 10 == 0:
                    self._save_cache()
            
            # Final cache save
            self._save_cache()
            
            # Generate summary
            self._generate_summary()
            
        except Exception as e:
            self.logger.error(f"❌ Critical error: {e}")
            raise
        finally:
            self.logger.close()
    
    def _generate_summary(self):
        """Generate and log final summary"""
        usage_summary = self.openai_client.get_usage_summary()
        
        self.logger.info("=" * 60)
        self.logger.info("📊 FINAL SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"✅ Jobs Processed: {self.processed_count}")
        self.logger.info(f"⏩ Skipped (Cached): {self.skipped_count}")
        self.logger.info(f"❌ Failed: {self.failed_count}")
        self.logger.info(f"🤖 Backup Model Calls: {usage_summary['gpt4_calls']}")
        self.logger.info(f"🎯 Total Tokens: {usage_summary['total_tokens']:,}")
        self.logger.info(f"💰 Total Cost: ${usage_summary['total_cost']:.2f}")
        self.logger.info("=" * 60)


def main():
    """Main entry point"""
    # Load environment variables
    load_dotenv()
    
    # Create and run job evaluator
    evaluator = JobEvaluator()
    evaluator.run()


if __name__ == "__main__":
    main()