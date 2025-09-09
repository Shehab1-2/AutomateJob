#!/usr/bin/env python3
"""
Notion API Test Script
Tests Notion database connectivity, permissions, and page creation functionality.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from notion_client import Client as NotionClient

# Load environment variables
load_dotenv()

def test_api_authentication():
    """Test Notion API key authentication."""
    print("🔑 Testing Notion API Authentication...")
    
    api_key = os.getenv("NOTION_API_KEY")
    if not api_key:
        print("❌ NOTION_API_KEY not found in environment")
        return False
    
    if not api_key.startswith("ntn_"):
        print("❌ Invalid Notion API key format")
        return False
    
    try:
        client = NotionClient(auth=api_key)
        # Test authentication with a simple API call
        user = client.users.me()
        print(f"✅ API key valid - Connected as: {user.get('name', 'Unknown')}")
        return True
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        return False

def test_database_access(database_id, db_name):
    """Test access to a specific Notion database."""
    print(f"\n🗄️ Testing {db_name} Database Access...")
    
    if not database_id:
        print(f"❌ {db_name} database ID not found in environment")
        return False
    
    try:
        client = NotionClient(auth=os.getenv("NOTION_API_KEY"))
        
        # Test database access
        database = client.databases.retrieve(database_id)
        
        print(f"✅ {db_name} database accessible")
        print(f"   Database title: {database.get('title', [{}])[0].get('text', {}).get('content', 'Unknown')}")
        print(f"   Database ID: {database_id}")
        
        # Test query capability
        response = client.databases.query(
            database_id=database_id,
            page_size=1  # Just get one entry to test
        )
        
        entry_count = len(response.get("results", []))
        print(f"   Current entries: {entry_count}+ entries")
        
        return True
        
    except Exception as e:
        print(f"❌ {db_name} database access failed: {e}")
        return False

def test_page_creation(database_id, db_name):
    """Test creating a page in the Notion database."""
    print(f"\n📝 Testing Page Creation in {db_name}...")
    
    if not database_id:
        print(f"❌ {db_name} database ID not found")
        return False
    
    try:
        client = NotionClient(auth=os.getenv("NOTION_API_KEY"))
        
        # Sample job data for testing
        test_job_data = {
            "Job Title": {"title": [{"text": {"content": "TEST - API Validation Job"}}]},
            "Company": {"rich_text": [{"text": {"content": "TestCorp API Validation"}}]},
            "Location": {"rich_text": [{"text": {"content": "Remote"}}]},
            "Rating": {"number": 9.5},
            "Explanation": {"rich_text": [{"text": {"content": "This is a test job created by API validation script. Safe to delete."}}]},
            "Link": {"url": "https://www.linkedin.com"},
            "Apply URL": {"url": "https://www.linkedin.com"},
            "Type": {"rich_text": [{"text": {"content": "API Test"}}]},
            "Date Posted": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
            "Job ID": {"rich_text": [{"text": {"content": "TEST_API_VALIDATION"}}]},
            "Seniority Level": {"select": {"name": "Entry level"}},
            "Employment Type": {"select": {"name": "Full-time"}},
            "Job Function": {"rich_text": [{"text": {"content": "API Testing"}}]},
            "Industries": {"rich_text": [{"text": {"content": "Software Testing"}}]},
            "Company Size": {"number": 100},
            "Applicants": {"number": 0},
            "Company Description": {"rich_text": [{"text": {"content": "Test company for API validation"}}]}
        }
        
        # Create test page
        page = client.pages.create(
            parent={"database_id": database_id},
            properties=test_job_data
        )
        
        page_id = page["id"]
        print(f"✅ Test page created successfully in {db_name}")
        print(f"   Page ID: {page_id}")
        print("   ⚠️ Note: You can safely delete this test entry from Notion")
        
        return True
        
    except Exception as e:
        print(f"❌ Page creation failed in {db_name}: {e}")
        return False

def test_database_schema(database_id, db_name):
    """Test database schema compatibility."""
    print(f"\n📋 Testing {db_name} Database Schema...")
    
    try:
        client = NotionClient(auth=os.getenv("NOTION_API_KEY"))
        database = client.databases.retrieve(database_id)
        
        properties = database.get("properties", {})
        required_fields = [
            "Job Title", "Company", "Location", "Rating", "Explanation",
            "Link", "Apply URL", "Type", "Date Posted", "Job ID",
            "Seniority Level", "Employment Type"
        ]
        
        missing_fields = []
        existing_fields = []
        
        for field in required_fields:
            if field in properties:
                existing_fields.append(field)
            else:
                missing_fields.append(field)
        
        print(f"✅ Schema analysis complete")
        print(f"   Existing fields: {len(existing_fields)}/{len(required_fields)}")
        print(f"   Fields found: {', '.join(existing_fields[:5])}...")
        
        if missing_fields:
            print(f"   ⚠️ Missing fields: {', '.join(missing_fields)}")
            return False
        else:
            print(f"   ✅ All required fields present")
            return True
            
    except Exception as e:
        print(f"❌ Schema test failed for {db_name}: {e}")
        return False

def main():
    """Run all Notion API tests."""
    print("🚀 Notion API Test Suite")
    print("=" * 50)
    
    tests = []
    
    # Authentication test
    tests.append(("Authentication", test_api_authentication()))
    
    # Database access tests
    main_db_id = os.getenv("NOTION_DB_ID")
    test_db_id = os.getenv("NOTION_DB_ID_TEST")
    
    if main_db_id:
        tests.append(("Main Database Access", test_database_access(main_db_id, "Main")))
        tests.append(("Main Database Schema", test_database_schema(main_db_id, "Main")))
        tests.append(("Main Database Page Creation", test_page_creation(main_db_id, "Main")))
    else:
        print("⚠️ NOTION_DB_ID not found - skipping main database tests")
    
    if test_db_id:
        tests.append(("Test Database Access", test_database_access(test_db_id, "Test")))
        tests.append(("Test Database Schema", test_database_schema(test_db_id, "Test")))
        tests.append(("Test Database Page Creation", test_page_creation(test_db_id, "Test")))
    else:
        print("⚠️ NOTION_DB_ID_TEST not found - skipping test database tests")
    
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
        print("🎉 All Notion API tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())