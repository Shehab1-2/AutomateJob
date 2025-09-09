# job_analyzer_lib/evaluator.py
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

from tqdm import tqdm

from .config import Config
from .services import OpenAIClient, NotionService
from .utils import Logger, JobEvaluationError, ApplicationTypeDetector

class JobEvaluator:
    """Main job evaluation orchestrator."""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.openai_client = OpenAIClient(self.logger)
        self.notion_client = NotionService(os.getenv("NOTION_DB_ID"), self.logger) # type: ignore
        self.cache = self._load_cache()
        self.processed_count = 0
        self.skipped_count = 0
        self.failed_count = 0
        self.below_threshold_count = 0

    def _setup_logging(self) -> Logger:
        """Setup logging infrastructure."""
        os.makedirs(Config.LOG_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_file_path = f"{Config.LOG_DIR}/enhanced_run_{timestamp}.log"
        return Logger(log_file_path)

    def _load_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load existing evaluation cache."""
        if os.path.exists(Config.CACHE_FILE):
            try:
                with open(Config.CACHE_FILE, "r", encoding="utf-8") as f:
                    cached_results = json.load(f)
                return {str(job["id"]): job for job in cached_results}
            except Exception as e:
                self.logger.warning(f"Failed to load cache: {e}")
        return {}

    def _save_cache(self):
        """Save evaluation cache."""
        try:
            with open(Config.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(list(self.cache.values()), f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save cache: {e}")

    def _load_resume(self) -> str:
        """Load resume text."""
        try:
            with open(Config.RESUME_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except FileNotFoundError:
            raise JobEvaluationError(f"Resume file not found: {Config.RESUME_FILE}")

    def _load_jobs(self) -> List[Dict[str, Any]]:
        """Load latest filtered jobs."""
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
        """Validate required environment variables."""
        required_vars = ["OPENAI_API_KEY", "NOTION_API_KEY", "NOTION_DB_ID"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise JobEvaluationError(f"Missing required environment variables: {missing_vars}")

    def process_job(self, job: Dict[str, Any], resume_text: str) -> bool:
        """Process a single job evaluation."""
        job_id = str(job.get("id", "unknown"))
        if job_id in self.cache:
            self.logger.info(f"⏩ Skipping cached job ID {job_id}")
            self.skipped_count += 1
            return True
        
        try:
            evaluation = self.openai_client.evaluate_job_fit(job, resume_text)
            job["rating"] = evaluation["rating"]
            job["explanation"] = evaluation["explanation"]
            
            apply_url = job.get("applyUrl", "")
            app_type = ApplicationTypeDetector.detect_application_type(apply_url)
            self.logger.info(f"🔗 Application Type: {app_type} ({apply_url[:50]}...)")
            
            # Check rating threshold before pushing to Notion
            if job["rating"] >= Config.MINIMUM_RATING_THRESHOLD:
                # Push to Notion for high-rated jobs
                if self.notion_client.create_job_page(job):
                    self.logger.info(f"✅ Added high-rated job (rating: {job['rating']}) to Notion")
                    self.processed_count += 1
                    notion_success = True
                else:
                    self.logger.error(f"❌ Failed to add job to Notion")
                    self.failed_count += 1
                    notion_success = False
            else:
                self.logger.info(f"⏸️ Skipping job ID {job_id} - rating {job['rating']} below threshold ({Config.MINIMUM_RATING_THRESHOLD})")
                self.below_threshold_count += 1
                notion_success = True  # Consider it "processed" even though not added to Notion

            # Always cache the evaluation (regardless of rating)
            self.cache[job_id] = {
                "id": job_id,
                "rating": job["rating"],
                "explanation": job["explanation"]
            }

            return notion_success
        except Exception as e:
            self.logger.error(f"❌ Error processing job '{job.get('title', 'unknown')}': {e}")
            self.failed_count += 1
            return False

    def run(self):
        """Main execution method."""
        try:
            self.logger.info("🚀 Starting Enhanced Job Evaluation System")
            self._validate_environment()
            resume_text = self._load_resume()
            jobs = self._load_jobs()
            self.logger.info(f"📄 Resume loaded ({len(resume_text)} characters)")
            self.logger.info(f"📋 Found {len(self.cache)} cached evaluations")
            
            for job in tqdm(jobs, desc="Evaluating Jobs", unit="job"):
                self.process_job(job, resume_text)
                if self.processed_count % 10 == 0:
                    self._save_cache()
            
            self._save_cache()
            self._generate_summary()
        except Exception as e:
            self.logger.error(f"❌ Critical error: {e}")
            raise
        finally:
            self.logger.close()

    def _generate_summary(self):
        """Generate and log final summary."""
        usage_summary = self.openai_client.get_usage_summary()
        self.logger.info("=" * 60)
        self.logger.info("📊 FINAL SUMMARY")
        self.logger.info("=" * 60)
        self.logger.info(f"✅ Jobs Added to Notion: {self.processed_count}")
        self.logger.info(f"⏸️ Below Threshold (Cached Only): {self.below_threshold_count}")
        self.logger.info(f"⏩ Skipped (Previously Cached): {self.skipped_count}")
        self.logger.info(f"❌ Failed: {self.failed_count}")
        self.logger.info(f"🎯 Rating Threshold: {Config.MINIMUM_RATING_THRESHOLD}")
        self.logger.info(f"🤖 Backup Model Calls: {usage_summary['gpt4_calls']}")
        self.logger.info(f"🎯 Total Tokens: {usage_summary['total_tokens']:,}")
        self.logger.info(f"💰 Total Cost: ${usage_summary['total_cost']:.2f}")
        self.logger.info("=" * 60)