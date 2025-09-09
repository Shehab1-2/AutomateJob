#!/usr/bin/env python3
"""
OpenAI API Test Script
Tests GPT model availability, authentication, and job evaluation functionality.
"""

import os
import json
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

def test_api_authentication():
    """Test OpenAI API key authentication."""
    print("🔑 Testing OpenAI API Authentication...")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment")
        return False
    
    if not api_key.startswith("sk-"):
        print("❌ Invalid OpenAI API key format")
        return False
    
    print(f"✅ API key found: {api_key[:10]}...{api_key[-10:]}")
    return True

def test_model_availability(model_name):
    """Test if a specific model is available and responsive."""
    print(f"\n🤖 Testing {model_name} availability...")
    
    try:
        client = OpenAI()
        
        # Simple test prompt
        test_prompt = "Respond with exactly: 'Model test successful'"
        
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": test_prompt}],
            max_tokens=50,
            timeout=30
        )
        
        content = response.choices[0].message.content
        tokens = response.usage.total_tokens
        
        if content and len(content.strip()) > 0:
            print(f"✅ {model_name} is working")
            print(f"   Response: {content[:50]}...")
            print(f"   Tokens used: {tokens}")
            return True
        else:
            print(f"❌ {model_name} returned empty response")
            return False
            
    except Exception as e:
        print(f"❌ {model_name} failed: {e}")
        return False

def test_job_evaluation_prompt():
    """Test the actual job evaluation prompt format."""
    print(f"\n📋 Testing Job Evaluation Prompt...")
    
    try:
        client = OpenAI()
        primary_model = os.getenv("PRIMARY_MODEL", "gpt-4o")
        
        # Sample job evaluation prompt (simplified)
        sample_job = {
            "title": "Software Engineer",
            "company": "TestCorp",
            "location": "Remote",
            "description": "Python developer role with React frontend work"
        }
        
        sample_resume = "Software engineer with 3 years Python and React experience"
        
        prompt = f"""You are a technical recruiter. Evaluate this job fit.

CANDIDATE RESUME:
{sample_resume}

JOB DETAILS:
Title: {sample_job['title']}
Company: {sample_job['company']}
Description: {sample_job['description']}

Rate 1-10 and provide explanation.

OUTPUT FORMAT:
{{"rating": [1-10 number], "explanation": "[specific reasoning]"}}
"""
        
        response = client.chat.completions.create(
            model=primary_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            timeout=30
        )
        
        content = response.choices[0].message.content
        
        # Try to parse as JSON
        try:
            result = json.loads(content)
            if "rating" in result and "explanation" in result:
                rating = result["rating"]
                explanation = result["explanation"]
                print(f"✅ Job evaluation prompt working")
                print(f"   Sample rating: {rating}")
                print(f"   Sample explanation: {explanation[:100]}...")
                return True
            else:
                print(f"❌ Invalid response format: missing rating or explanation")
                return False
        except json.JSONDecodeError:
            print(f"❌ Response is not valid JSON: {content[:100]}...")
            return False
            
    except Exception as e:
        print(f"❌ Job evaluation test failed: {e}")
        return False

def test_token_counting():
    """Test token counting functionality."""
    print(f"\n🔢 Testing Token Counting...")
    
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")
        
        test_text = "This is a test string for token counting."
        tokens = len(encoding.encode(test_text))
        
        print(f"✅ Token counting working")
        print(f"   Test text: '{test_text}'")
        print(f"   Token count: {tokens}")
        return True
        
    except Exception as e:
        print(f"❌ Token counting failed: {e}")
        return False

def main():
    """Run all OpenAI API tests."""
    print("🚀 OpenAI API Test Suite")
    print("=" * 50)
    
    # Test results
    tests = []
    
    # Authentication test
    tests.append(("Authentication", test_api_authentication()))
    
    # Model availability tests
    primary_model = os.getenv("PRIMARY_MODEL", "gpt-4o")
    backup_model = os.getenv("BACKUP_MODEL", "gpt-4o-mini")
    
    tests.append((f"Primary Model ({primary_model})", test_model_availability(primary_model)))
    tests.append((f"Backup Model ({backup_model})", test_model_availability(backup_model)))
    
    # Functionality tests
    tests.append(("Job Evaluation Prompt", test_job_evaluation_prompt()))
    tests.append(("Token Counting", test_token_counting()))
    
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
        print("🎉 All OpenAI API tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())