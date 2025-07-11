import json
from pathlib import Path

# Use this code to condese Apilfy Outputed Data
# === CONFIG ===
INPUT_FILE = "jobs.json"               # Your scraped data
OUTPUT_FILE = "condensed_jobs.json"    # Your condensed output

# === Condense the job data ===
def condense_job(job):
    return {
        "id": job.get("id"),
        "postedAt": job.get("postedAt"),
        "title": job.get("title"),
        "company": job.get("companyName"),
        "location": job.get("location"),
        "companyEmployeesCount": job.get("companyEmployeesCount"),
        "link": job.get("link"),
        "rating": 0,  # Default
        "explanation": (
            f"Without the candidate's resume, it's impossible to evaluate their fit for the "
            f"{job.get('title')} role at {job.get('companyName')}. The resume should list skills, "
            "projects, tech stack, and other relevant experiences."
        ),
        "description": job.get("descriptionText", "")[:500] + "...",
        "seniorityLevel": job.get("seniorityLevel"),
        "employmentType": job.get("employmentType"),
        "jobFunction": job.get("jobFunction"),
        "industries": job.get("industries")
    }

def condense_jobs(input_path, output_path):
    with open(input_path, "r", encoding="utf-8") as f:
        raw_jobs = json.load(f)

    condensed = [condense_job(job) for job in raw_jobs]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(condensed, f, indent=2)

    print(f"✅ Condensed {len(condensed)} jobs into: {output_path}")

# === Run it ===
if __name__ == "__main__":
    if not Path(INPUT_FILE).exists():
        print(f"❌ File not found: {INPUT_FILE}")
    else:
        condense_jobs(INPUT_FILE, OUTPUT_FILE)
