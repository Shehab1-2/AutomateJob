import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from notion_client import Client as NotionClient

# === Environment Variable Validation ===
load_dotenv()
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DB_ID = os.getenv("NOTION_DB_ID")

if not NOTION_API_KEY:
    print("❌ ERROR: NOTION_API_KEY not found in environment variables")
    sys.exit(1)
if not NOTION_DB_ID:
    print("❌ ERROR: NOTION_DB_ID not found in environment variables")
    sys.exit(1)

notion = NotionClient(auth=NOTION_API_KEY)

# === Load Configuration ===
def load_config():
    config_path = Path(__file__).parent / "config.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ ERROR: Config file not found at {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in config file: {e}")
        sys.exit(1)

config = load_config()

# === Directory Setup ===
CONDENSED_DIR = Path(__file__).parent.parent / "condensed" / "condense_data"
OUTPUT_DIR = Path(__file__).parent / "filter_data"
LOG_DIR = Path(__file__).parent / "log"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# === Logging Setup ===
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file_path = LOG_DIR / f"log_{timestamp}.txt"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# === Check for dry run mode ===
DRY_RUN = "--dry-run" in sys.argv

# === Helper Functions ===
def normalize_text(text):
    """Normalize text for consistent comparison"""
    return text.lower().strip() if text else ""

def get_latest_condensed_file():
    """Get the most recent condensed jobs file"""
    try:
        json_files = list(CONDENSED_DIR.glob("condensed_jobs_*.json"))
        if not json_files:
            logger.error("No condensed jobs files found.")
            return None
        return max(json_files, key=os.path.getmtime)
    except Exception as e:
        logger.error(f"Error finding condensed files: {e}")
        return None

def get_existing_job_ids():
    """Fetch existing job IDs from Notion database"""
    existing_ids = set()
    has_more = True
    start_cursor = None

    try:
        while has_more:
            response = notion.databases.query(
                database_id=NOTION_DB_ID,
                start_cursor=start_cursor
            )
            for page in response["results"]:
                props = page.get("properties", {})
                job_id_prop = props.get("Job ID", {}).get("rich_text", [])
                if job_id_prop:
                    job_id = job_id_prop[0]["text"]["content"]
                    existing_ids.add(job_id)
            has_more = response.get("has_more", False)
            start_cursor = response.get("next_cursor")
    except Exception as e:
        logger.error(f"Error fetching existing job IDs: {e}")
        return set()

    return existing_ids

def passes_filter(job, existing_ids):
    """Check if a job passes all filters"""
    job_id = str(job.get("id", ""))
    
    # Skip if already exists
    if job_id in existing_ids:
        return False, "already_exists"

    title = normalize_text(job.get("title", ""))
    description = normalize_text(job.get("description", ""))
    location = normalize_text(job.get("location", ""))
    company = job.get("company", "").strip()

    # Company filter
    if company in config["bad_companies"]:
        return False, "bad_company"

    # Aggregator filter
    if any(keyword in description or keyword in normalize_text(company) 
           for keyword in config["aggregator_keywords"]):
        return False, "aggregator"

    # Excluded keywords filter
    if any(keyword in description for keyword in config["excluded_keywords"]):
        return False, "excluded_keyword"

    # Seniority filter
    if any(term in title for term in config["excluded_seniority"]):
        return False, "senior_role"

    # ✅ Location filter (optional)
    if config.get("use_location_filter", True):  # default True if not present
        location_match = False
        if location:
            # Check if location matches allowed locations
            if any(allowed in location for allowed in config["allowed_locations"]):
                location_match = True

        # Also check description for remote work indicators
        remote_indicators = [
            "remote", "work from home", "wfh", "telecommute", 
            "distributed team", "remote-friendly", "100% remote"
        ]
        if any(indicator in description for indicator in remote_indicators):
            location_match = True

        # If we have location data but no match, filter out
        if location and not location_match:
            return False, "location_mismatch"

    # Age filter
    posted = job.get("postedAt")
    if posted:
        try:
            post_date = datetime.fromisoformat(posted.rstrip("Z"))
            if (datetime.utcnow() - post_date).days > config["days_limit"]:
                return False, "too_old"
        except Exception:
            pass

    return True, "passed"


def filter_jobs(jobs, existing_ids):
    """Filter jobs based on all criteria"""
    filtered = []
    stats = {"total": len(jobs), "already_exists": 0, "bad_company": 0, 
             "aggregator": 0, "excluded_keyword": 0, "senior_role": 0,
             "location_mismatch": 0, "too_old": 0, "passed": 0}
    duplicate_ids = []  # 🆕 collect IDs that already exist

    for job in jobs:
        try:
            passed, reason = passes_filter(job, existing_ids)
            stats[reason] += 1
            if not passed and reason == "already_exists":  # 🆕 record duplicate IDs without changing logic
                duplicate_ids.append(str(job.get("id", "")))
            if passed:
                filtered.append(job)
        except Exception as e:
            logger.warning(f"Error processing job {job.get('id', 'unknown')}: {e}")

    # Log statistics
    logger.info(f"Filtering Results:")
    logger.info(f"  Total jobs: {stats['total']}")
    logger.info(f"  Already exists: {stats['already_exists']}")
    if stats["already_exists"] > 0:  # 🆕 output the specific duplicate IDs
        logger.info(f"  Duplicate Job IDs: {', '.join(duplicate_ids)}")
    logger.info(f"  Bad company: {stats['bad_company']}")
    logger.info(f"  Aggregator: {stats['aggregator']}")
    logger.info(f"  Excluded keyword: {stats['excluded_keyword']}")
    logger.info(f"  Senior role: {stats['senior_role']}")
    logger.info(f"  Location mismatch: {stats['location_mismatch']}")
    logger.info(f"  Too old: {stats['too_old']}")
    logger.info(f"  Passed filters: {stats['passed']}")

    return filtered

def main():
    """Main execution function"""
    if DRY_RUN:
        logger.info("🔍 DRY RUN MODE - No files will be written")

    # Get input file
    input_file = get_latest_condensed_file()
    if not input_file:
        return

    logger.info(f"📄 Reading from: {input_file}")
    
    # Load and validate jobs data
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            jobs = json.load(f)
        
        if not isinstance(jobs, list):
            logger.error("Input file does not contain a list of jobs")
            return
            
        logger.info(f"📊 Loaded {len(jobs)} jobs from file")
        
    except Exception as e:
        logger.error(f"Error reading input file: {e}")
        return

    # Get existing job IDs
    if not DRY_RUN:
        existing_ids = get_existing_job_ids()
        logger.info(f"🔎 Found {len(existing_ids)} existing job IDs in Notion")
    else:
        existing_ids = set()
        logger.info("🔎 Skipping Notion check (dry run)")

    # Filter jobs
    filtered_jobs = filter_jobs(jobs, existing_ids)

    # Save results
    if not DRY_RUN:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            output_path = OUTPUT_DIR / f"filtered_jobs_{timestamp}.json"
            
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(filtered_jobs, f, indent=2)
            
            logger.info(f"✅ Saved {len(filtered_jobs)} filtered jobs to {output_path}")
        except Exception as e:
            logger.error(f"Error saving filtered jobs: {e}")
    else:
        logger.info(f"✅ Would save {len(filtered_jobs)} filtered jobs (dry run)")

if __name__ == "__main__":
    main()
