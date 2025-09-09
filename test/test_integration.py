#!/usr/bin/env python3
"""
Integration Test Script
Tests end-to-end pipeline functionality with minimal data.
"""

import os
import sys
import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_environment_variables():
    """Test that all required environment variables are present."""
    print("🔧 Testing Environment Variables...")
    
    required_vars = [
        "OPENAI_API_KEY",
        "NOTION_API_KEY", 
        "NOTION_DB_ID",
        "APIFY_API_TOKEN",
        "PRIMARY_MODEL",
        "BACKUP_MODEL"
    ]
    
    missing_vars = []
    present_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            present_vars.append(var)
        else:
            missing_vars.append(var)
    
    print(f"✅ Environment variables: {len(present_vars)}/{len(required_vars)} present")
    
    if missing_vars:
        print(f"❌ Missing variables: {', '.join(missing_vars)}")
        return False
    else:
        print(f"   All required variables found")
        return True

def test_file_structure():
    """Test that all required files and directories exist."""
    print(f"\n📁 Testing File Structure...")
    
    base_path = Path("/Users/shehabahamed/linkedin-job-rater-py/src")
    
    required_files = [
        "pipeline.py",
        "scraped/scrape_apify_jobs.py",
        "condensed/condense_jobs.py", 
        "filtered/filter_condensed_jobs.py",
        "filtered/config.json",
        "analyze/analyze.py",
        "analyze/resume.txt"
    ]
    
    missing_files = []
    present_files = []
    
    for file_path in required_files:
        full_path = base_path / file_path
        if full_path.exists():
            present_files.append(file_path)
        else:
            missing_files.append(file_path)
    
    print(f"✅ File structure: {len(present_files)}/{len(required_files)} files found")
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False
    else:
        print(f"   All required files present")
        return True

def test_pipeline_test_mode():
    """Test pipeline execution in test mode."""
    print(f"\n🧪 Testing Pipeline in Test Mode...")
    
    try:
        # Change to src directory
        src_dir = "/Users/shehabahamed/linkedin-job-rater-py/src"
        
        # Run pipeline in test mode with timeout
        result = subprocess.run(
            [sys.executable, "pipeline.py", "--test"],
            cwd=src_dir,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode == 0:
            print(f"✅ Pipeline test mode completed successfully")
            
            # Check for key success indicators in output
            output = result.stdout
            if "PIPELINE COMPLETED SUCCESSFULLY" in output:
                print(f"   ✅ Full pipeline completion confirmed")
            if "TEST mode" in output:
                print(f"   ✅ Test mode confirmed")
            if "analyzer completed successfully" in output:
                print(f"   ✅ Analyzer stage completed")
                
            return True
        else:
            print(f"❌ Pipeline test failed (exit code: {result.returncode})")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}...")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Pipeline test timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Pipeline test failed: {e}")
        return False

def test_individual_components():
    """Test individual pipeline components."""
    print(f"\n🔧 Testing Individual Components...")
    
    src_dir = "/Users/shehabahamed/linkedin-job-rater-py/src"
    component_tests = []
    
    # Test scraper
    try:
        result = subprocess.run(
            [sys.executable, "scraped/scrape_apify_jobs.py", "--test"],
            cwd=src_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        component_tests.append(("Scraper", result.returncode == 0))
        if result.returncode == 0:
            print("   ✅ Scraper test passed")
        else:
            print(f"   ❌ Scraper test failed: {result.stderr[:100]}...")
    except Exception as e:
        component_tests.append(("Scraper", False))
        print(f"   ❌ Scraper test error: {e}")
    
    # Test analyzer (if filtered data exists)
    try:
        # Check if we have filtered data to analyze
        filtered_dir = Path(src_dir) / "filtered" / "filter_data"
        if any(filtered_dir.glob("filtered_jobs_*.json")):
            result = subprocess.run(
                [sys.executable, "analyze/analyze.py"],
                cwd=src_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            component_tests.append(("Analyzer", result.returncode == 0))
            if result.returncode == 0:
                print("   ✅ Analyzer test passed")
            else:
                print(f"   ❌ Analyzer test failed: {result.stderr[:100]}...")
        else:
            print("   ⏩ Skipping analyzer test (no filtered data available)")
            
    except Exception as e:
        component_tests.append(("Analyzer", False))
        print(f"   ❌ Analyzer test error: {e}")
    
    # Return overall component test result
    return all(result for _, result in component_tests) if component_tests else True

def test_data_flow():
    """Test data flow between pipeline stages."""
    print(f"\n🔄 Testing Data Flow...")
    
    try:
        src_dir = Path("/Users/shehabahamed/linkedin-job-rater-py/src")
        
        # Check for recent pipeline outputs
        recent_cutoff = datetime.now().timestamp() - (24 * 60 * 60)  # Last 24 hours
        
        stages = {
            "scraped": src_dir / "scraped" / "scraped",
            "condensed": src_dir / "condensed" / "condense_data", 
            "filtered": src_dir / "filtered" / "filter_data"
        }
        
        flow_results = []
        
        for stage_name, stage_dir in stages.items():
            if stage_dir.exists():
                json_files = list(stage_dir.glob("*.json"))
                recent_files = [f for f in json_files if f.stat().st_mtime > recent_cutoff]
                
                if recent_files:
                    latest_file = max(recent_files, key=lambda f: f.stat().st_mtime)
                    print(f"   ✅ {stage_name}: Recent data found ({latest_file.name})")
                    flow_results.append(True)
                else:
                    print(f"   ⚠️ {stage_name}: No recent data (run pipeline to generate)")
                    flow_results.append(False)
            else:
                print(f"   ❌ {stage_name}: Directory not found")
                flow_results.append(False)
        
        success_rate = sum(flow_results) / len(flow_results)
        print(f"\n   Data flow success rate: {success_rate*100:.1f}%")
        
        return success_rate > 0.5  # Pass if more than half the stages have data
        
    except Exception as e:
        print(f"❌ Data flow test failed: {e}")
        return False

def main():
    """Run all integration tests."""
    print("🚀 Integration Test Suite")
    print("=" * 50)
    
    tests = []
    
    # Environment and setup tests
    tests.append(("Environment Variables", test_environment_variables()))
    tests.append(("File Structure", test_file_structure()))
    
    # Component tests
    tests.append(("Individual Components", test_individual_components()))
    
    # Data flow test
    tests.append(("Data Flow", test_data_flow()))
    
    # Full pipeline test (most comprehensive)
    tests.append(("Full Pipeline (Test Mode)", test_pipeline_test_mode()))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 INTEGRATION TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All integration tests passed!")
        print("\n💡 Your pipeline is ready for production use!")
        return 0
    else:
        print("⚠️ Some tests failed. Check individual test outputs above.")
        if passed >= len(tests) * 0.8:  # 80% pass rate
            print("💡 Pipeline is mostly functional - investigate failing tests.")
        return 1

if __name__ == "__main__":
    sys.exit(main())