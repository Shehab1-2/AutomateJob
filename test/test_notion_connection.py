import os
import aiohttp
import asyncio
from dotenv import load_dotenv

# Load .env file
load_dotenv()

NOTION_TOKEN = os.getenv('NOTION_API_KEY')
DATABASE_ID = os.getenv('NOTION_DB_ID_TEST')  # or 'NOTION_DB_ID' for prod

async def test_notion():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, json={}) as response:
            print(f"HTTP Status: {response.status}")
            data = await response.json()
            print("\nResponse:\n", data)

            if response.status == 200:
                print(f"\n✅ Success: Retrieved {len(data.get('results', []))} entries.")
            else:
                print("\n❌ Failed to query database.")
                if 'message' in data:
                    print(f"Error message: {data['message']}")

if __name__ == "__main__":
    asyncio.run(test_notion())
