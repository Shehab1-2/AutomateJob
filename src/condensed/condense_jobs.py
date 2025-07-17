import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Configuration
SCRAPED_DIR = Path(__file__).parent.parent / "scraped" / "scraped_data"
OUTPUT_DIR = Path(__file__).parent / "condense_data"
LOG_DIR = Path(__file__).parent / "log"
DESCRIPTION_MAX_LENGTH = 500

# Setup directories
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Setup logging
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

def get_latest_scraped_file() -> Optional[Path]:
    """Find the most recently modified JSON file in the scraped directory."""
    try:
        json_files = list(SCRAPED_DIR.glob("*.json"))
        if not json_files:
            logging.error("❌ No JSON files found in scraped directory")
            return None
        
        latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
        logging.info(f"📁 Found latest file: {latest_file.name}")
        return latest_file
    except Exception as e:
        logging.error(f"❌ Error finding scraped files: {e}")
        return None

def condense_job(job: Dict) -> Dict:
    """Transform a raw job dictionary into condensed format."""
    description = job.get("descriptionText", "")
    company_desc = job.get("companyDescription", "")
    
    return {
        "id": job.get("id"),
        "postedAt": job.get("postedAt"),
        "title": job.get("title"),
        "company": job.get("companyName"),
        "location": job.get("location"),
        "companyEmployeesCount": job.get("companyEmployeesCount"),
        "link": job.get("link"),
        "rating": None,
        "explanation": "",
        "jobDescription": description[:DESCRIPTION_MAX_LENGTH] + "..." if len(description) > DESCRIPTION_MAX_LENGTH else description,
        "companyDescription": company_desc[:DESCRIPTION_MAX_LENGTH] + "..." if len(company_desc) > DESCRIPTION_MAX_LENGTH else company_desc,
        "seniorityLevel": job.get("seniorityLevel"),
        "employmentType": job.get("employmentType"),
        "jobFunction": job.get("jobFunction"),
        "industries": job.get("industries"),
        "applicantsCount": job.get("applicantsCount"),
        "applyUrl": job.get("applyUrl"),
        "type":""
    }

def condense_jobs(input_path: Path, output_path: Path) -> bool:
    """Read raw jobs, condense them, and write to output file."""
    try:
        logging.info(f"📖 Reading jobs from: {input_path}")
        with open(input_path, "r", encoding="utf-8") as f:
            raw_jobs = json.load(f)
        
        if not isinstance(raw_jobs, list):
            logging.error("❌ Input file does not contain a list of jobs")
            return False
        
        logging.info(f"🔄 Processing {len(raw_jobs)} jobs...")
        condensed_jobs = []
        
        for i, job in enumerate(raw_jobs):
            try:
                condensed_jobs.append(condense_job(job))
            except Exception as e:
                logging.warning(f"⚠️ Error processing job {i}: {e}")
                continue
        
        logging.info(f"💾 Writing {len(condensed_jobs)} jobs to: {output_path}")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(condensed_jobs, f, indent=2, ensure_ascii=False)
        
        logging.info(f"✅ Successfully condensed {len(condensed_jobs)} jobs")
        return True
        
    except json.JSONDecodeError as e:
        logging.error(f"❌ Invalid JSON in input file: {e}")
        return False
    except FileNotFoundError:
        logging.error(f"❌ Input file not found: {input_path}")
        return False
    except Exception as e:
        logging.error(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main execution function."""
    logging.info("🚀 Starting job condensation process...")
    
    input_file = get_latest_scraped_file()
    if not input_file:
        logging.error("❌ No input file found, exiting")
        return 1
    
    output_file = OUTPUT_DIR / f"condensed_jobs_{timestamp}.json"
    
    if condense_jobs(input_file, output_file):
        logging.info("🎉 Job condensation completed successfully!")
        return 0
    else:
        logging.error("❌ Job condensation failed")
        return 1

if __name__ == "__main__":
    exit(main())