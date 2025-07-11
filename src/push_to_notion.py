import json
import os
from dotenv import load_dotenv
from notion_client import Client
from time import sleep

# Load .env variables
load_dotenv()
print("NOTION_API_KEY:", os.getenv("NOTION_API_KEY"))
print("NOTION_DB_ID:", os.getenv("NOTION_DB_ID"))

# Initialize Notion client
notion = Client(auth=os.getenv("NOTION_API_KEY"))
DATABASE_ID = os.getenv("NOTION_DB_ID")

# Check if job with given ID already exists in Notion
def job_already_exists(job_id):
    try:
        response = notion.databases.query(
            **{
                "database_id": DATABASE_ID,
                "filter": {
                    "property": "Job ID",
                    "rich_text": {
                        "equals": str(job_id)
                    }
                }
            }
        )
        print(f"✅ Queried Notion for Job ID {job_id} — {len(response['results'])} matches")  # type: ignore
        return len(response["results"]) > 0  # type: ignore
    except Exception as e:
        print(f"⚠️ Error checking job ID {job_id}: {e}")
        return False

# Add job to Notion database
def add_job_to_notion(job):
    try:
        notion.pages.create(
            parent={"database_id": DATABASE_ID},
            properties={
                "Job Title": {"title": [{"text": {"content": job.get("title", "Untitled")}}]},
                "Company": {"rich_text": [{"text": {"content": job.get("company", "")}}]},
                "Location": {"rich_text": [{"text": {"content": job.get("location", "")}}]},
                "Rating": {"number": job.get("rating", 0)},
                "Explanation": {"rich_text": [{"text": {"content": job.get("explanation", "")[:2000]}}]},
                "Link": {"url": job.get("link", "https://www.linkedin.com")},
                "Date Posted": {"date": {"start": job.get("postedAt", "2025-01-01")}},
                "Job ID": {"rich_text": [{"text": {"content": str(job.get("id", "0"))}}]},
                "Seniority Level": {"select": {"name": job.get("seniorityLevel", "N/A")}},
                "Employment Type": {"select": {"name": job.get("employmentType", "N/A")}},
                "Job Function": {"rich_text": [{"text": {"content": job.get("jobFunction", "")}}]},
                "Industries": {"rich_text": [{"text": {"content": job.get("industries", "")}}]},
                "Company Size": {"number": job.get("companyEmployeesCount", 0)},
                "Company Description": {
                    "rich_text": [{"text": {"content": job.get("companyDescription", "")[:2000]}}]
                }
            }
        )

        print(f"✅ Added: {job['title']} ({job['id']})")
    except Exception as e:
        print(f"❌ Failed to add job {job.get('id', 'unknown')}: {e}")

# Main function
def main():
    with open("condensed_jobs.json", "r", encoding="utf-8") as f:
        jobs = json.load(f)

    for job in jobs:
        if job_already_exists(job["id"]):
            print(f"⏭️ Skipping existing job: {job['title']} ({job['id']})")
        else:
            add_job_to_notion(job)
            sleep(0.5)  # rate limit

if __name__ == "__main__":
    main()
