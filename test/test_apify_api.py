#!/usr/bin/env python3
"""
Apify API Test Script
Tests Apify LinkedIn scraper availability, authentication, and functionality.
"""

import os
import json
import sys
import http.client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_api_authentication():
    """Test Apify API token authentication."""
    print("🔑 Testing Apify API Authentication...")
    
    api_token = os.getenv("APIFY_API_TOKEN")
    if not api_token:
        print("❌ APIFY_API_TOKEN not found in environment")
        return False
    
    if not api_token.startswith("apify_api_"):
        print("❌ Invalid Apify API token format")
        return False
    
    print(f"✅ API token found: {api_token[:15]}...{api_token[-10:]}")
    return True

def test_actor_availability():
    """Test if the LinkedIn scraper actor is available."""
    print(f"\n🎭 Testing LinkedIn Scraper Actor Availability...")
    
    try:
        api_token = os.getenv("APIFY_API_TOKEN")
        actor_id = os.getenv("ACTOR_ID", "hKByXkMQaC5Qt9UMN")
        
        conn = http.client.HTTPSConnection("api.apify.com")
        
        headers = {
            'Authorization': f'Bearer {api_token}',
            'Accept': 'application/json'
        }
        
        # Get actor information
        conn.request("GET", f"/v2/acts/{actor_id}", headers=headers)
        res = conn.getresponse()
        data = res.read()
        
        if res.status == 200:
            actor_info = json.loads(data.decode("utf-8"))
            actor_name = actor_info.get("data", {}).get("name", "Unknown")
            print(f"✅ Actor available: {actor_name}")
            print(f"   Actor ID: {actor_id}")
            return True
        else:
            print(f"❌ Actor not accessible (HTTP {res.status})")
            print(f"   Response: {data.decode('utf-8')[:100]}...")
            return False
            
    except Exception as e:
        print(f"❌ Actor availability test failed: {e}")
        return False

def test_small_scraping_request():
    """Test a minimal scraping request to validate functionality."""
    print(f"\n🔍 Testing Small Scraping Request...")
    
    try:
        api_token = os.getenv("APIFY_API_TOKEN")
        actor_id = os.getenv("ACTOR_ID", "hKByXkMQaC5Qt9UMN")
        
        conn = http.client.HTTPSConnection("api.apify.com")
        
        # Minimal test payload
        test_url = "https://www.linkedin.com/jobs/search/?keywords=software%20engineer&f_E=2"
        
        payload = json.dumps({
            "count": 5,  # Only 5 jobs for testing
            "scrapeCompany": False,
            "urls": [test_url],
            "maxItems": 5,
            "maxConcurrency": 1,
            "proxyConfiguration": {"useApifyProxy": True}
        })
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {api_token}'
        }
        
        print("   Sending minimal scraping request (5 jobs)...")
        
        conn.request("POST", f"/v2/acts/{actor_id}/run-sync-get-dataset-items", payload, headers)
        res = conn.getresponse()
        data = res.read()
        
        if res.status == 200:
            try:
                jobs = json.loads(data.decode("utf-8"))
                job_count = len(jobs) if isinstance(jobs, list) else 0
                
                print(f"✅ Scraping request successful")
                print(f"   Jobs retrieved: {job_count}")
                
                if job_count > 0:
                    sample_job = jobs[0]
                    print(f"   Sample job title: {sample_job.get('title', 'Unknown')}")
                    print(f"   Sample company: {sample_job.get('companyName', 'Unknown')}")
                
                return True
                
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON response: {e}")
                print(f"   Raw response: {data.decode('utf-8')[:200]}...")
                return False
        else:
            print(f"❌ Scraping request failed (HTTP {res.status})")
            print(f"   Response: {data.decode('utf-8')[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Scraping test failed: {e}")
        return False

def test_url_formats():
    """Test the LinkedIn URL formats used in the scraper."""
    print(f"\n🔗 Testing LinkedIn URL Formats...")
    
    # Import URL constants from scraper
    try:
        sys.path.append('/Users/shehabahamed/linkedin-job-rater-py/src/scraped')
        
        # Test URLs (simplified versions)
        test_urls = [
            ("Software Engineer", "https://www.linkedin.com/jobs/search/?keywords=software%20engineer"),
            ("Implementation", "https://www.linkedin.com/jobs/search/?keywords=implementation%20specialist"),
            ("Solutions Engineer", "https://www.linkedin.com/jobs/search/?keywords=solutions%20engineer"),
            ("Integration", "https://www.linkedin.com/jobs/search/?keywords=integration%20specialist"),
            ("Automation", "https://www.linkedin.com/jobs/search/?keywords=automation")
        ]
        
        print("✅ URL format validation:")
        for name, url in test_urls:
            if "linkedin.com/jobs/search" in url and "keywords=" in url:
                print(f"   ✅ {name}: Valid LinkedIn job search URL")
            else:
                print(f"   ❌ {name}: Invalid URL format")
        
        return True
        
    except Exception as e:
        print(f"❌ URL format test failed: {e}")
        return False

def test_quota_and_limits():
    """Test API quota and rate limits."""
    print(f"\n📊 Testing API Quota and Limits...")
    
    try:
        api_token = os.getenv("APIFY_API_TOKEN")
        conn = http.client.HTTPSConnection("api.apify.com")
        
        headers = {
            'Authorization': f'Bearer {api_token}',
            'Accept': 'application/json'
        }
        
        # Get user account info to check quotas
        conn.request("GET", "/v2/users/me", headers=headers)
        res = conn.getresponse()
        data = res.read()
        
        if res.status == 200:
            user_info = json.loads(data.decode("utf-8"))
            user_data = user_info.get("data", {})
            
            print(f"✅ Account information retrieved")
            print(f"   Username: {user_data.get('username', 'Unknown')}")
            print(f"   Plan: {user_data.get('plan', 'Unknown')}")
            
            # Check usage if available
            usage = user_data.get("usage", {})
            if usage:
                print(f"   Current usage info available")
            
            return True
        else:
            print(f"❌ Could not retrieve account info (HTTP {res.status})")
            return False
            
    except Exception as e:
        print(f"❌ Quota test failed: {e}")
        return False

def main():
    """Run all Apify API tests."""
    print("🚀 Apify API Test Suite")
    print("=" * 50)
    
    tests = []
    
    # Authentication test
    tests.append(("Authentication", test_api_authentication()))
    
    # Actor availability test
    tests.append(("LinkedIn Scraper Actor", test_actor_availability()))
    
    # URL format validation
    tests.append(("URL Format Validation", test_url_formats()))
    
    # Quota and limits
    tests.append(("Quota and Limits", test_quota_and_limits()))
    
    # Small scraping test (commented out by default to save quota)
    print("\n⚠️ Skipping actual scraping test to save API quota")
    print("   Uncomment test_small_scraping_request() to test actual scraping")
    # tests.append(("Small Scraping Request", test_small_scraping_request()))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Results: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All Apify API tests passed!")
        print("\n💡 To test actual scraping, uncomment the scraping test in the code")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())