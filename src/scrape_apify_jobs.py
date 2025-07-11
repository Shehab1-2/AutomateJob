import http.client
import json
import os
from datetime import datetime

# === CONFIG ===
API_TOKEN = "apify_api_q8A3hHqvSIfmQduYb6qLbBE8grEacz2ZPfB3"
ACTOR_ID = "hKByXkMQaC5Qt9UMN"
LINKEDIN_URL = "https://www.linkedin.com/jobs/search/?currentJobId=4262323437&f_E=2%2C3&f_TPR=r604800&geoId=105080838&keywords=software%20engineer&origin=JOB_SEARCH_PAGE_LOCATION_AUTOCOMPLETE&refresh=true"

# Prepare output folder
os.makedirs("scraped", exist_ok=True)

# === Apify API Call ===
conn = http.client.HTTPSConnection("api.apify.com")

payload = json.dumps({
    "urls": [LINKEDIN_URL],  # ✅ root-level "urls", NOT inside "input"
    "maxItems": 10,
    "maxConcurrency": 10,
    "extendOutputFunction": "",
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

print(f"✅ Saved {len(jobs)} jobs to {output_path}")
