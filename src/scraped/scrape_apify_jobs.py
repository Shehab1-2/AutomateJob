# scrape_apify_jobs.py

import http.client
import json
import os
from datetime import datetime

# === CONFIG ===
API_TOKEN = "apify_api_q8A3hHqvSIfmQduYb6qLbBE8grEacz2ZPfB3"
ACTOR_ID = "hKByXkMQaC5Qt9UMN"
LINKEDIN_URL = ""
SOFTWARE_URL = "https://www.linkedin.com/jobs/search/?currentJobId=4286542388&f_E=2%2C3&f_JT=F&f_TPR=r604800&f_WT=3%2C2&geoId=103644278&keywords=software%20engineer%20NOT%20Dice%20NOT%20Jobright.ai%20NOT%20Canonical%20NOT%20Randstad%20NOT%20Insight%20Global%20NOT%20Robert%20Half%20NOT%20Kforce%20NOT%20TEKsystems%20NOT%20Apex%20Systems%20NOT%20Cognizant&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&sortBy=R"
IMPLEMENTATION_URL = "https://www.linkedin.com/jobs/search/?f_E=2%2C3&f_JT=F&f_TPR=r604800&f_WT=3%2C2&geoId=103644278&keywords=Implementation%20Specialist%20NOT%20Dice%20NOT%20Jobright%20NOT%20Jobright.ai%20NOT%20Canonical%20NOT%20Randstad%20NOT%20Insight%20Global%20NOT%20Robert%20Half%20NOT%20Kforce%20NOT%20TEKsystems%20NOT%20Apex%20Systems%20NOT%20Cognizant&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&sortBy=R&position=1&pageNum=0"
Solutions_Engineer_URl = "https://www.linkedin.com/jobs/search/?f_E=2%2C3&f_JT=F&f_TPR=r604800&f_WT=3%2C2&geoId=103644278&keywords=Solutions%20Engineer%20NOT%20Dice%20NOT%20Jobright%20NOT%20Jobright.ai%20NOT%20Canonical%20NOT%20Randstad%20NOT%20Insight%20Global%20NOT%20Robert%20Half%20NOT%20Kforce%20NOT%20TEKsystems%20NOT%20Apex%20Systems%20NOT%20Cognizant&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&sortBy=R"
Integration_Specialist_URL = "https://www.linkedin.com/jobs/search/?f_E=2%2C3&f_JT=F&f_TPR=r604800&f_WT=3%2C2&geoId=103644278&keywords=Integration%20Specialist%20NOT%20Dice%20NOT%20Jobright%20NOT%20Jobright.ai%20NOT%20Canonical%20NOT%20Randstad%20NOT%20Insight%20Global%20NOT%20Robert%20Half%20NOT%20Kforce%20NOT%20TEKsystems%20NOT%20Apex%20Systems%20NOT%20Cognizant&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&sortBy=R"
Automation_URL = "https://www.linkedin.com/jobs/search/?currentJobId=4287310518&f_E=2%2C3&f_JT=F&f_TPR=r604800&f_WT=2%2C3&geoId=103644278&keywords=automation%20NOT%20Dice%20NOT%20Jobright.ai%20NOT%20Lensa%20NOT%20Tietalent&origin=JOB_SEARCH_PAGE_JOB_FILTER&refresh=true&sortBy=R"
# === SCRAPER SETTINGS ===
REQUESTED_COUNT = 320  # how many jobs we *want* to scrape
SCRAPE_COMPANY = False  # whether to scrape company pages too

# Prepare output folder
os.makedirs("scraped", exist_ok=True)

# === Apify API Call ===
conn = http.client.HTTPSConnection("api.apify.com")

payload = json.dumps({
    "count": REQUESTED_COUNT,
    "scrapeCompany": SCRAPE_COMPANY,
    "urls": [Automation_URL],
    "maxItems": 320,
    "maxConcurrency": 10,
    "proxyConfiguration": {
        "useApifyProxy": True
    }
})

headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': f'Bearer {API_TOKEN}'
}

# Trigger the actor run and wait for it to complete
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

# Save output with timestamp
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
output_path = f"scraped/jobs_{timestamp}.json"

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(jobs, f, indent=2)

# === Summary Log ===
scraped_count = len(jobs)
print(f"✅ Saved {scraped_count} jobs to {output_path}")

if scraped_count < REQUESTED_COUNT:
    print(f"⚠️ Requested {REQUESTED_COUNT}, but only scraped {scraped_count}.")
    print("   LinkedIn may have throttled or limited results.")
else:
    print("🎉 All requested jobs scraped successfully.")
