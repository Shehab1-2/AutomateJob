# scrape_apify_jobs.py

import http.client
import json
import os
from datetime import datetime
import argparse # For command-line flags
from dotenv import load_dotenv

load_dotenv()

# === ARGUMENT PARSER FOR TEST FLAG ===
parser = argparse.ArgumentParser(description="Scrape jobs from LinkedIn using Apify.")
parser.add_argument(
    '--test', 
    action='store_true', 
    help='Run in test mode without calling the API, using dummy data instead.'
)
args = parser.parse_args()

# === CONFIG ===
API_TOKEN = os.getenv("APIFY_API_TOKEN", "YOUR_API_TOKEN_HERE") # Best practice to use env variables
ACTOR_ID = "hKByXkMQaC5Qt9UMN"

SOFTWARE_URL = "https://www.linkedin.com/jobs/search/?currentJobId=4286542388&f_E=2%2C3&f_JT=F&f_TPR=r604800&f_WT=3%2C2&geoId=103644278&keywords=software%20engineer%20NOT%20Dice%20NOT%20Jobright.ai%20NOT%20Canonical%20NOT%20Randstad%20NOT%20Insight%20Global%20NOT%20Robert%20Half%20NOT%20Kforce%20NOT%20TEKsystems%20NOT%20Apex%20Systems%20NOT%20Cognizant&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&sortBy=R"
IMPLEMENTATION_URL = "https://www.linkedin.com/jobs/search/?f_E=2%2C3&f_JT=F&f_TPR=r604800&f_WT=3%2C2&geoId=103644278&keywords=Implementation%20Specialist%20NOT%20Dice%20NOT%20Jobright%20NOT%20Jobright.ai%20NOT%20Canonical%20NOT%20Randstad%20NOT%20Insight%20Global%20NOT%20Robert%20Half%20NOT%20Kforce%20NOT%20TEKsystems%20NOT%20Apex%20Systems%20NOT%20Cognizant&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&sortBy=R&position=1&pageNum=0"
Solutions_Engineer_URl = "https://www.linkedin.com/jobs/search/?f_E=2%2C3&f_JT=F&f_TPR=r604800&f_WT=3%2C2&geoId=103644278&keywords=Solutions%20Engineer%20NOT%20Dice%20NOT%20Jobright%20NOT%20Jobright.ai%20NOT%20Canonical%20NOT%20Randstad%20NOT%20Insight%20Global%20NOT%20Robert%20Half%20NOT%20Kforce%20NOT%20TEKsystems%20NOT%20Apex%20Systems%20NOT%20Cognizant&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&sortBy=R"
Integration_Specialist_URL = "https://www.linkedin.com/jobs/search/?f_E=2%2C3&f_JT=F&f_TPR=r604800&f_WT=3%2C2&geoId=103644278&keywords=Integration%20Specialist%20NOT%20Dice%20NOT%20Jobright%20NOT%20Jobright.ai%20NOT%20Canonical%20NOT%20Randstad%20NOT%20Insight%20Global%20NOT%20Robert%20Half%20NOT%20Kforce%20NOT%20TEKsystems%20NOT%20Apex%20Systems%20NOT%20Cognizant&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&sortBy=R"
Automation_URL = "https://www.linkedin.com/jobs/search/?currentJobId=4287310518&f_E=2%2C3&f_JT=F&f_TPR=r604800&f_WT=2%2C3&geoId=103644278&keywords=automation%20NOT%20Dice%20NOT%20Jobright.ai%20NOT%20Lensa%20NOT%20Tietalent&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&sortBy=R"

# === DUMMY DATA FOR TEST MODE ===
DUMMY_JOB_DATA = [
  {
    "id": "12345213",
    "trackingId": "entryTest123",
    "refId": "refEntry001",
    "link": "https://www.linkedin.com/jobs/view/junior-data-analyst-at-dummycorp-5001002001",
    "title": "Junior Data Analyst",
    "companyName": "DummyCorp",
    "companyLinkedinUrl": "https://www.linkedin.com/company/dummycorp",
    "companyLogo": "https://via.placeholder.com/100",
    "location": "Boston, MA",
    "salaryInfo": ["$55,000.00", "$65,000.00"],
    "postedAt": "2025-08-15",
    "benefits": ["Health Insurance", "401k", "Remote Option"],
    "descriptionHtml": "<p>We are seeking an <strong>Entry Level Data Analyst</strong> to join our analytics team. You will clean and prepare datasets, create dashboards, and provide reporting support under the guidance of senior analysts.</p>",
    "applicantsCount": "45",
    "applyUrl": "https://example.com/apply/junior-data-analyst",
    "salary": "",
    "descriptionText": "We are seeking an Entry Level Data Analyst to join our analytics team. Responsibilities include cleaning and preparing datasets, creating dashboards, and providing reporting support.",
    "seniorityLevel": "Entry level",
    "employmentType": "Full-time",
    "jobFunction": "Data Analysis",
    "industries": "Information Technology & Services",
    "inputUrl": "https://www.linkedin.com/jobs/search/?keywords=junior%20data%20analyst"
  },
  {
    "id": "4283525513",
    "trackingId": "entryTest124",
    "refId": "refEntry002",
    "link": "https://www.linkedin.com/jobs/view/software-engineer-intern-at-faketech-5001002002",
    "title": "Software Engineer Intern",
    "companyName": "FakeTech",
    "companyLinkedinUrl": "https://www.linkedin.com/company/faketech",
    "companyLogo": "https://via.placeholder.com/100",
    "location": "Remote (US)",
    "salaryInfo": [""],
    "postedAt": "2025-08-16",
    "benefits": ["Mentorship Program", "Flexible Hours"],
    "descriptionHtml": "<p><strong>Software Engineer Intern</strong> opportunity for students or recent graduates. Work alongside experienced developers to build web applications using Python and React.</p>",
    "applicantsCount": "120",
    "applyUrl": "https://example.com/apply/software-engineer-intern",
    "salary": "",
    "descriptionText": "Software Engineer Intern opportunity for students or recent graduates. Work alongside experienced developers to build web applications using Python and React.",
    "seniorityLevel": "Internship",
    "employmentType": "Internship",
    "jobFunction": "Engineering",
    "industries": "Computer Software",
    "inputUrl": "https://www.linkedin.com/jobs/search/?keywords=software%20engineer%20intern"
  }
]


# === SCRAPER SETTINGS ===
REQUESTED_COUNT = 100
SCRAPE_COMPANY = False

# Prepare output folder
os.makedirs("scraped/scraped", exist_ok=True)


jobs = []
# === Main Logic: Switch between LIVE and TEST mode ===
if args.test:
    print("🧪 Running in TEST mode. Skipping Apify API call.")
    jobs = DUMMY_JOB_DATA
else:
    print("🚀 Running in LIVE mode. Calling Apify API...")
    conn = http.client.HTTPSConnection("api.apify.com")

    payload = json.dumps({
        "count": REQUESTED_COUNT,
        "scrapeCompany": SCRAPE_COMPANY,
        "urls": [Automation_URL],
        "maxItems": 100,
        "maxConcurrency": 10,
        "proxyConfiguration": { "useApifyProxy": True }
    })

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {API_TOKEN}'
    }

    conn.request("POST", f"/v2/acts/{ACTOR_ID}/run-sync-get-dataset-items", payload, headers)
    res = conn.getresponse()
    data = res.read()
    decoded = data.decode("utf-8")

    try:
        jobs = json.loads(decoded)
    except json.JSONDecodeError as e:
        print("❌ Failed to decode JSON:", e)
        print("Raw response:", decoded)
        exit(1)

# This part of the script now runs for both LIVE and TEST modes
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
output_path = f"scraped/scraped/jobs_{timestamp}.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(jobs, f, indent=2)

# === Summary Log ===
scraped_count = len(jobs)

if args.test:
    print(f"✅ Saved {scraped_count} dummy jobs to {output_path}")
    print("🎉 Test mode finished successfully.")
else:
    print(f"✅ Saved {scraped_count} jobs to {output_path}")
    if scraped_count < REQUESTED_COUNT:
        print(f"⚠️ Requested {REQUESTED_COUNT}, but only scraped {scraped_count}.")
        print("   LinkedIn may have throttled or limited results.")
    else:
        print("🎉 All requested jobs scraped successfully.")