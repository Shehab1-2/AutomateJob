# pipeline_scheduler.py

import schedule
import time
import subprocess
import sys
import os
from datetime import datetime
from pathlib import Path

# === CONFIGURATION ===
SCRIPT_NAMES = {
    "scraper": "../src/scraped/scrape_apify_jobs.py",
    "condenser": "../src/condensed/condense_jobs.py",
    "filter": "../src/filtered/filter_condensed_jobs.py",
    "analyzer": "../src/analyze/analyze_jobs.py"
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

def run_script(script_name, log_file):
    """Run a Python script and capture its output"""
    script_path = SCRIPT_NAMES[script_name]
    
    if not os.path.exists(script_path):
        log_message(f"❌ Script {script_path} not found!", log_file)
        return False
    
    log_message(f"🚀 Starting {script_name} ({script_path})...", log_file)
    
    try:
        # Run the script and capture output
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout per script
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

def run_complete_pipeline():
    """Run the complete job processing pipeline"""
    log_file = setup_logging()
    
    log_message("=" * 50, log_file)
    log_message("🔄 STARTING AUTOMATED JOB PIPELINE", log_file)
    log_message("=" * 50, log_file)
    
    # Define the pipeline steps in order
    pipeline_steps = ["scraper", "condenser", "filter", "analyzer"]
    
    success_count = 0
    total_steps = len(pipeline_steps)
    
    for step in pipeline_steps:
        if run_script(step, log_file):
            success_count += 1
        else:
            log_message(f"🛑 Pipeline stopped at {step} due to failure", log_file)
            break
        
        # Small delay between steps
        time.sleep(5)
    
    log_message("=" * 50, log_file)
    if success_count == total_steps:
        log_message("🎉 PIPELINE COMPLETED SUCCESSFULLY!", log_file)
    else:
        log_message(f"⚠️ PIPELINE PARTIALLY COMPLETED ({success_count}/{total_steps} steps)", log_file)
    log_message("=" * 50, log_file)
    
    log_file.close()

def run_pipeline_with_error_handling():
    """Wrapper to handle any unexpected errors in the pipeline"""
    try:
        run_complete_pipeline()
    except Exception as e:
        print(f"❌ Unexpected error in pipeline: {e}")
        # Log to a separate error file
        with open("logs/scheduler_errors.txt", "a") as error_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            error_file.write(f"[{timestamp}] Pipeline error: {e}\n")

def main():
    """Main scheduler function"""
    print("🤖 Job Pipeline Scheduler Starting...")
    print("📅 Scheduled to run every 6 hours")
    print("🔧 Press Ctrl+C to stop the scheduler")
    print()
    
    # Schedule the pipeline to run every 6 hours
    schedule.every(1).hours.do(run_pipeline_with_error_handling)
    
    # Run once immediately on startup
    print("🚀 Running initial pipeline...")
    run_pipeline_with_error_handling()
    
    # Keep the scheduler running
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\n🛑 Scheduler stopped by user")
            break
        except Exception as e:
            print(f"❌ Scheduler error: {e}")
            time.sleep(60)  # Continue running even if there's an error

if __name__ == "__main__":
    main()