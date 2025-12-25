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
import re
import glob

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

def run_script(script_name, log_file, test_mode=False, no_explanation=False):
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
    if script_name == "analyzer" and no_explanation:
        command.append('--no-explanation')
        log_message("   -> Running analyzer with no explanations.", log_file)
    
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

def get_latest_log_file(log_dir, pattern):
    """Get the most recent log file from a directory."""
    try:
        log_path = Path(log_dir)
        if not log_path.exists():
            return None
        
        log_files = list(log_path.glob(pattern))
        if not log_files:
            return None
            
        return max(log_files, key=os.path.getmtime)
    except Exception:
        return None

def extract_component_summary(component_name, log_file_path):
    """Extract comprehensive metrics from component log files."""
    if not log_file_path or not log_file_path.exists():
        return f"   ❌ {component_name}: No log file found"
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        summary_lines = []
        
        if component_name == "condenser":
            # Extract comprehensive condenser info
            lines = log_content.split('\n')
            input_file = None
            output_file = None
            jobs_processed = None
            errors = []
            
            for line in lines:
                if "Reading jobs from:" in line:
                    input_file = line.split("Reading jobs from:")[-1].strip()
                elif "Writing" in line and "jobs to:" in line:
                    match = re.search(r"Writing (\d+) jobs to: (.+)", line)
                    if match:
                        jobs_processed = match.group(1)
                        output_file = match.group(2)
                elif "Successfully condensed" in line:
                    match = re.search(r"Successfully condensed (\d+) jobs", line)
                    if match:
                        jobs_processed = match.group(1)
                elif "ERROR" in line or "Error" in line:
                    errors.append(line.strip())
            
            if input_file:
                summary_lines.append(f"📖 Input: {Path(input_file).name}")
            if jobs_processed:
                summary_lines.append(f"📦 Jobs processed: {jobs_processed}")
            if output_file:
                summary_lines.append(f"💾 Output: {Path(output_file).name}")
            if errors:
                summary_lines.append(f"⚠️ Errors: {len(errors)} found")
                for error in errors[:2]:  # Show first 2 errors
                    summary_lines.append(f"   {error[:80]}...")
            
        elif component_name == "filter":
            # Extract comprehensive filtering statistics
            lines = log_content.split('\n')
            stats = {}
            duplicate_ids = []
            
            for line in lines:
                if "Total jobs:" in line:
                    stats["total"] = re.search(r"(\d+)", line).group(1) if re.search(r"(\d+)", line) else "0"
                elif "Already exists:" in line:
                    stats["duplicates"] = re.search(r"(\d+)", line).group(1) if re.search(r"(\d+)", line) else "0"
                elif "Bad company:" in line:
                    stats["bad_company"] = re.search(r"(\d+)", line).group(1) if re.search(r"(\d+)", line) else "0"
                elif "Aggregator:" in line:
                    stats["aggregator"] = re.search(r"(\d+)", line).group(1) if re.search(r"(\d+)", line) else "0"
                elif "Excluded keyword:" in line:
                    stats["excluded"] = re.search(r"(\d+)", line).group(1) if re.search(r"(\d+)", line) else "0"
                elif "Senior role:" in line:
                    stats["senior"] = re.search(r"(\d+)", line).group(1) if re.search(r"(\d+)", line) else "0"
                elif "Location mismatch:" in line:
                    stats["location"] = re.search(r"(\d+)", line).group(1) if re.search(r"(\d+)", line) else "0"
                elif "Too old:" in line:
                    stats["old"] = re.search(r"(\d+)", line).group(1) if re.search(r"(\d+)", line) else "0"
                elif "Passed filters:" in line:
                    stats["passed"] = re.search(r"(\d+)", line).group(1) if re.search(r"(\d+)", line) else "0"
                elif "Duplicate Job IDs:" in line:
                    ids_text = line.split("Duplicate Job IDs:")[-1].strip()
                    duplicate_ids = [id.strip() for id in ids_text.split(",") if id.strip()]
            
            if stats.get("total"):
                summary_lines.append(f"📊 Total jobs processed: {stats['total']}")
            if stats.get("passed"):
                summary_lines.append(f"✅ Jobs passed filters: {stats['passed']}")
            if stats.get("duplicates"):
                summary_lines.append(f"⏩ Already in database: {stats['duplicates']}")
                if duplicate_ids:
                    summary_lines.append(f"   Duplicate IDs: {', '.join(duplicate_ids[:3])}{'...' if len(duplicate_ids) > 3 else ''}")
            
            # Show rejection reasons
            rejections = []
            if int(stats.get("bad_company", 0)) > 0:
                rejections.append(f"Bad companies: {stats['bad_company']}")
            if int(stats.get("aggregator", 0)) > 0:
                rejections.append(f"Aggregators: {stats['aggregator']}")
            if int(stats.get("excluded", 0)) > 0:
                rejections.append(f"Excluded keywords: {stats['excluded']}")
            if int(stats.get("senior", 0)) > 0:
                rejections.append(f"Senior roles: {stats['senior']}")
            if int(stats.get("location", 0)) > 0:
                rejections.append(f"Location mismatch: {stats['location']}")
            if int(stats.get("old", 0)) > 0:
                rejections.append(f"Too old: {stats['old']}")
                
            if rejections:
                summary_lines.append(f"🚫 Filtered out - {', '.join(rejections)}")
                    
        elif component_name == "analyzer":
            # Extract comprehensive analysis metrics
            lines = log_content.split('\n')
            stats = {}
            job_ratings = []
            
            for line in lines:
                # Main summary stats
                if "Jobs Added to Notion:" in line:
                    stats["added"] = re.search(r"(\d+)", line).group(1) if re.search(r"(\d+)", line) else "0"
                elif "Below Threshold (Cached Only):" in line:
                    stats["below_threshold"] = re.search(r"(\d+)", line).group(1) if re.search(r"(\d+)", line) else "0"
                elif "Skipped (Previously Cached):" in line:
                    stats["cached"] = re.search(r"(\d+)", line).group(1) if re.search(r"(\d+)", line) else "0"
                elif "Failed:" in line and "INFO" in line:
                    stats["failed"] = re.search(r"(\d+)", line).group(1) if re.search(r"(\d+)", line) else "0"
                elif "Rating Threshold:" in line:
                    stats["threshold"] = re.search(r"(\d+)", line).group(1) if re.search(r"(\d+)", line) else "7"
                elif "Backup Model Calls:" in line:
                    stats["backup_calls"] = re.search(r"(\d+)", line).group(1) if re.search(r"(\d+)", line) else "0"
                elif "Total Tokens:" in line:
                    match = re.search(r"Total Tokens: ([\d,]+)", line)
                    stats["tokens"] = match.group(1) if match else "0"
                elif "Total Cost:" in line:
                    match = re.search(r"Total Cost: \$([0-9.]+)", line)
                    stats["cost"] = match.group(1) if match else "0.00"
                
                # Extract individual job ratings
                if "RATING:" in line:
                    match = re.search(r"RATING: ([0-9.]+)/10", line)
                    if match:
                        job_ratings.append(float(match.group(1)))
            
            # Build detailed summary
            if stats.get("added"):
                summary_lines.append(f"✅ Jobs added to Notion: {stats['added']}")
            if stats.get("below_threshold"):
                summary_lines.append(f"⏸️ Below threshold (rating < {stats.get('threshold', '7')}): {stats['below_threshold']}")
            if stats.get("cached"):
                summary_lines.append(f"⏩ Previously cached (skipped): {stats['cached']}")
            if stats.get("failed"):
                summary_lines.append(f"❌ Failed evaluations: {stats['failed']}")
            
            # Rating analysis
            if job_ratings:
                avg_rating = sum(job_ratings) / len(job_ratings)
                max_rating = max(job_ratings)
                min_rating = min(job_ratings)
                summary_lines.append(f"📈 Ratings: Avg {avg_rating:.1f}, Range {min_rating}-{max_rating}")
            
            # API usage
            if stats.get("tokens"):
                summary_lines.append(f"🎯 API tokens used: {stats['tokens']}")
            if stats.get("cost"):
                summary_lines.append(f"💰 API cost: ${stats['cost']}")
            if stats.get("backup_calls"):
                summary_lines.append(f"🤖 Backup model calls: {stats['backup_calls']}")
        
        if summary_lines:
            return f"   📋 {component_name.upper()}:\n" + "\n".join(f"      {line}" for line in summary_lines)
        else:
            return f"   ✅ {component_name}: Completed (no detailed metrics found)"
            
    except Exception as e:
        return f"   ❌ {component_name}: Error reading logs - {e}"

def generate_pipeline_summary(log_file):
    """Generate comprehensive pipeline summary with component details."""
    log_message("\n" + "=" * 60, log_file)
    log_message("📊 DETAILED PIPELINE SUMMARY", log_file)
    log_message("=" * 60, log_file)
    
    # Component log locations
    component_logs = {
        "condenser": ("condensed/log", "log_*.txt"),
        "filter": ("filtered/log", "log_*.txt"),
        "analyzer": ("analyze/log", "enhanced_run_*.log")
    }
    
    # Extract summaries from each component
    for component, (log_dir, pattern) in component_logs.items():
        latest_log = get_latest_log_file(log_dir, pattern)
        summary = extract_component_summary(component, latest_log)
        log_message(summary, log_file)
    
    log_message("=" * 60, log_file)

def run_complete_pipeline(test_mode=False, no_explanation=False):
    """Run the complete job processing pipeline."""
    log_file = setup_logging()
    
    log_message("=" * 50, log_file)
    if test_mode:
        log_message("🔄 STARTING AUTOMATED JOB PIPELINE (TEST MODE)", log_file)
    else:
        log_message("🔄 STARTING AUTOMATED JOB PIPELINE (LIVE MODE)", log_file)
    if no_explanation:
        log_message("   -> Analyzer will skip explanations", log_file)
    log_message("=" * 50, log_file)
    
    pipeline_steps = ["scraper", "condenser", "filter", "analyzer"]
    success_count = 0
    
    for step in pipeline_steps:
        # Pass the test_mode and no_explanation flags to the run_script function
        if run_script(step, log_file, test_mode, no_explanation):
            success_count += 1
        else:
            log_message(f"🛑 Pipeline stopped at {step} due to failure", log_file)
            break
        time.sleep(2) # Short delay
    
    log_message("=" * 50, log_file)
    if success_count == len(pipeline_steps):
        log_message("🎉 PIPELINE COMPLETED SUCCESSFULLY!", log_file)
        
        # Generate detailed component summary
        generate_pipeline_summary(log_file)
    else:
        log_message(f"⚠️ PIPELINE PARTIALLY COMPLETED ({success_count}/{len(pipeline_steps)} steps)", log_file)
    log_message("=" * 50, log_file)
    
    log_file.close()

def main():
    """Main scheduler function that accepts command-line arguments."""
    # === CHANGE: Add argument parser ===
    parser = argparse.ArgumentParser(description="Run the job processing pipeline.")
    parser.add_argument('--test', action='store_true', help='Run the pipeline in test mode.')
    parser.add_argument('--no-explanation', action='store_true', help='Skip AI-generated explanations in analyzer.')
    args = parser.parse_args()

    if args.test:
        print("🧪 Pipeline starting in TEST mode.")
    else:
        print("🚀 Pipeline starting in LIVE mode.")
    
    if args.no_explanation:
        print("📝 Analyzer will skip explanations.")
        
    print("🔧 Running pipeline once manually...")
    print()
    
    # Pass the test and no_explanation flags to the pipeline runner
    run_complete_pipeline(test_mode=args.test, no_explanation=args.no_explanation)

if __name__ == "__main__":
    main()