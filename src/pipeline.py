# pipeline.py

import schedule
import time
import subprocess
import sys
import os
import shutil
from datetime import datetime
from pathlib import Path
import argparse # New import for command-line flags

# === CONFIGURATION ===
SCRIPT_NAMES = {
    "scraper": "scraped/scrape_apify_jobs.py",
    "condenser": "condensed/condense_jobs.py",
    "filter": "filtered/filter_condensed_jobs.py",
    "analyzer": "analyze/analyze.py"
}

# Create logs directory
os.makedirs("logs", exist_ok=True)

def setup_logging():
    """Setup logging for the scheduler"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_path = f"logs/scheduler_log_{timestamp}.txt"
    return open(log_file_path, "w", encoding="utf-8")

def log_message(message: str, log_file=None):
    """Log message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}"
    print(formatted_message)
    if log_file:
        log_file.write(formatted_message + "\n")
        log_file.flush()

def run_script(script_name, log_file, test_mode=False):
    """Run a Python script and capture its output, passing --test flag if needed."""
    script_path = SCRIPT_NAMES[script_name]
    
    if not os.path.exists(script_path):
        log_message(f"❌ Script {script_path} not found!", log_file)
        return False
    
    log_message(f"🚀 Starting {script_name} ({script_path})...", log_file)
    
    # === CHANGE: Build the command dynamically ===
    command = [sys.executable, script_path]
    if script_name == "scraper" and test_mode:
        command.append('--test')
        log_message("   -> Running scraper in TEST mode.", log_file)
    
    try:
        result = subprocess.run(
            command, # Use the dynamically built command
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        if result.returncode == 0:
            log_message(f"✅ {script_name} completed successfully", log_file)
            if result.stdout:
                log_message(f"📄 Output: {result.stdout.strip()}", log_file)
            return True
        else:
            log_message(f"❌ {script_name} failed with return code {result.returncode}", log_file)
            if result.stderr:
                log_message(f"📄 Error: {result.stderr.strip()}", log_file)
            return False
            
    except subprocess.TimeoutExpired:
        log_message(f"⏰ {script_name} timed out after 30 minutes", log_file)
        return False
    except Exception as e:
        log_message(f"❌ Error running {script_name}: {str(e)}", log_file)
        return False

def run_complete_pipeline(test_mode=False):
    """Run the complete job processing pipeline."""
    log_file = setup_logging()
    
    log_message("=" * 50, log_file)
    if test_mode:
        log_message("🔄 STARTING AUTOMATED JOB PIPELINE (TEST MODE)", log_file)
    else:
        log_message("🔄 STARTING AUTOMATED JOB PIPELINE (LIVE MODE)", log_file)
    log_message("=" * 50, log_file)
    
    pipeline_steps = ["scraper", "condenser", "filter", "analyzer"]
    success_count = 0
    
    for step in pipeline_steps:
        # Pass the test_mode flag to the run_script function
        if run_script(step, log_file, test_mode):
            success_count += 1
        else:
            log_message(f"🛑 Pipeline stopped at {step} due to failure", log_file)
            break
        time.sleep(2) # Short delay
    
    log_message("=" * 50, log_file)
    if success_count == len(pipeline_steps):
        log_message("🎉 PIPELINE COMPLETED SUCCESSFULLY!", log_file)
    else:
        log_message(f"⚠️ PIPELINE PARTIALLY COMPLETED ({success_count}/{len(pipeline_steps)} steps)", log_file)
    log_message("=" * 50, log_file)
    
    log_file.close()

def main():
    """Main scheduler function that accepts command-line arguments."""
    # === CHANGE: Add argument parser ===
    parser = argparse.ArgumentParser(description="Run the job processing pipeline.")
    parser.add_argument('--test', action='store_true', help='Run the pipeline in test mode.')
    args = parser.parse_args()

    if args.test:
        print("🧪 Pipeline starting in TEST mode.")
    else:
        print("🚀 Pipeline starting in LIVE mode.")
        
    print("🔧 Running pipeline once manually...")
    print()
    
    # Pass the test flag to the pipeline runner
    run_complete_pipeline(test_mode=args.test)

if __name__ == "__main__":
    main()