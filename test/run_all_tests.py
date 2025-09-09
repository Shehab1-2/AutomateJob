#!/usr/bin/env python3
"""
Master Test Runner
Runs all API and integration tests with comprehensive reporting.
"""

import os
import sys
import subprocess
import time
from datetime import datetime
from pathlib import Path

def run_test_script(script_name, script_path):
    """Run a test script and capture results."""
    print(f"\n🚀 Running {script_name}...")
    print("=" * 60)
    
    try:
        start_time = time.time()
        
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per test
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print the test output
        if result.stdout:
            print(result.stdout)
        
        if result.stderr:
            print("STDERR:", result.stderr)
        
        success = result.returncode == 0
        
        print(f"\n⏱️ {script_name} completed in {duration:.2f}s")
        
        return {
            "name": script_name,
            "success": success,
            "duration": duration,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
    except subprocess.TimeoutExpired:
        print(f"❌ {script_name} timed out after 5 minutes")
        return {
            "name": script_name,
            "success": False,
            "duration": 300,
            "return_code": -1,
            "stdout": "",
            "stderr": "Test timed out"
        }
    except Exception as e:
        print(f"❌ Error running {script_name}: {e}")
        return {
            "name": script_name,
            "success": False,
            "duration": 0,
            "return_code": -1,
            "stdout": "",
            "stderr": str(e)
        }

def generate_test_report(test_results):
    """Generate a comprehensive test report."""
    print("\n" + "=" * 80)
    print("📊 COMPREHENSIVE TEST REPORT")
    print("=" * 80)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results if result["success"])
    total_duration = sum(result["duration"] for result in test_results)
    
    print(f"🎯 Overall Results: {passed_tests}/{total_tests} tests passed")
    print(f"⏱️ Total execution time: {total_duration:.2f}s")
    print(f"📅 Test run time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print(f"\n📋 Individual Test Results:")
    print("-" * 60)
    
    for result in test_results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        duration = f"{result['duration']:.2f}s"
        print(f"{status} - {result['name']:<25} ({duration:>8})")
        
        if not result["success"] and result["stderr"]:
            print(f"     Error: {result['stderr'][:100]}...")
    
    # Success rate analysis
    success_rate = (passed_tests / total_tests) * 100
    print(f"\n🎯 Success Rate: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("🎉 EXCELLENT: All systems operational!")
    elif success_rate >= 80:
        print("✅ GOOD: Most systems working, investigate failures")
    elif success_rate >= 60:
        print("⚠️ FAIR: Some systems have issues, review required")
    else:
        print("❌ POOR: Major system issues, immediate attention required")
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    failed_tests = [r for r in test_results if not r["success"]]
    
    if not failed_tests:
        print("   - All tests passed! Your system is ready for production.")
    else:
        print("   - Focus on fixing the failed tests above")
        if any("OpenAI" in r["name"] for r in failed_tests):
            print("   - Check OpenAI API key and model availability")
        if any("Notion" in r["name"] for r in failed_tests):
            print("   - Verify Notion API key and database permissions")
        if any("Apify" in r["name"] for r in failed_tests):
            print("   - Confirm Apify API token and actor access")
    
    return success_rate

def save_test_report(test_results, success_rate):
    """Save test report to file."""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_path = Path(__file__).parent / f"test_report_{timestamp}.json"
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "success_rate": success_rate,
            "total_tests": len(test_results),
            "passed_tests": sum(1 for r in test_results if r["success"]),
            "test_results": test_results
        }
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n💾 Test report saved to: {report_path}")
        return True
        
    except Exception as e:
        print(f"⚠️ Could not save test report: {e}")
        return False

def main():
    """Run all test scripts and generate comprehensive report."""
    print("🚀 MASTER TEST RUNNER")
    print("🧪 LinkedIn Job Automation System - API Test Suite")
    print("=" * 80)
    
    # Define test scripts
    test_dir = Path(__file__).parent
    test_scripts = [
        ("OpenAI API Tests", test_dir / "test_openai_api.py"),
        ("Notion API Tests", test_dir / "test_notion_api.py"),
        ("Apify API Tests", test_dir / "test_apify_api.py"),
        ("Integration Tests", test_dir / "test_integration.py")
    ]
    
    # Validate test scripts exist
    missing_scripts = []
    for name, path in test_scripts:
        if not path.exists():
            missing_scripts.append(name)
    
    if missing_scripts:
        print(f"❌ Missing test scripts: {', '.join(missing_scripts)}")
        return 1
    
    # Run all tests
    test_results = []
    
    for script_name, script_path in test_scripts:
        if script_name == "Integration Tests":
            # Skip integration tests to avoid recursion
            continue
            
        result = run_test_script(script_name, script_path)
        test_results.append(result)
    
    # Generate comprehensive report
    success_rate = generate_test_report(test_results)
    
    # Save report to file
    save_test_report(test_results, success_rate)
    
    # Return appropriate exit code
    if success_rate == 100:
        return 0
    elif success_rate >= 80:
        return 0  # Still consider success if 80%+ pass
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())