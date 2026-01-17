#!/usr/bin/env python3
"""
Test script to verify all API keys are valid before running main scripts.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_openai_key():
    """Test OpenAI API key"""
    print("\n🔑 Testing OpenAI API Key...")
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # Make a minimal API call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'API key works'"}],
            max_tokens=10
        )

        print("✅ OpenAI API key is valid")
        print(f"   Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ OpenAI API key failed: {str(e)}")
        return False

def test_notion_key():
    """Test Notion API key"""
    print("\n🔑 Testing Notion API Key...")
    try:
        import requests

        headers = {
            "Authorization": f"Bearer {os.getenv('NOTION_API_KEY')}",
            "Notion-Version": "2022-06-28"
        }

        # Test by listing databases (or getting user info)
        response = requests.get("https://api.notion.com/v1/users/me", headers=headers)

        if response.status_code == 200:
            print("✅ Notion API key is valid")
            data = response.json()
            print(f"   Bot name: {data.get('name', 'N/A')}")
            return True
        else:
            print(f"❌ Notion API key failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Notion API key failed: {str(e)}")
        return False

def test_notion_database():
    """Test Notion Database access"""
    print("\n🔑 Testing Notion Database Access...")
    try:
        import requests

        db_id = os.getenv('NOTION_DB_ID')
        if not db_id:
            print("⚠️  NOTION_DB_ID not set")
            return False

        headers = {
            "Authorization": f"Bearer {os.getenv('NOTION_API_KEY')}",
            "Notion-Version": "2022-06-28"
        }

        response = requests.get(f"https://api.notion.com/v1/databases/{db_id}", headers=headers)

        if response.status_code == 200:
            print("✅ Notion database is accessible")
            data = response.json()
            print(f"   Database: {data.get('title', [{}])[0].get('plain_text', 'N/A')}")
            return True
        else:
            print(f"❌ Notion database access failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Notion database access failed: {str(e)}")
        return False

def test_apify_key():
    """Test Apify API token"""
    print("\n🔑 Testing Apify API Token...")
    try:
        import requests

        token = os.getenv('APIFY_API_TOKEN')

        # Test by getting user info
        response = requests.get(f"https://api.apify.com/v2/users/me?token={token}")

        if response.status_code == 200:
            print("✅ Apify API token is valid")
            data = response.json()
            username = data.get('data', {}).get('username', 'N/A')
            print(f"   Username: {username}")
            return True
        else:
            print(f"❌ Apify API token failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Apify API token failed: {str(e)}")
        return False

def main():
    """Run all API key tests"""
    print("=" * 50)
    print("🧪 API Key Validation Test")
    print("=" * 50)

    results = {
        "OpenAI": test_openai_key(),
        "Notion": test_notion_key(),
        "Notion Database": test_notion_database(),
        "Apify": test_apify_key()
    }

    print("\n" + "=" * 50)
    print("📊 Summary")
    print("=" * 50)

    for service, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {service}: {'Valid' if status else 'Invalid'}")

    all_passed = all(results.values())

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All API keys are valid! You're ready to run your main scripts.")
    else:
        print("⚠️  Some API keys failed. Please check your .env file.")
    print("=" * 50)

    return all_passed

if __name__ == "__main__":
    main()
