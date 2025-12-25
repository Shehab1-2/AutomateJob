import json

def extract_job_descriptions(file_path: str):
    # Load JSON data from file
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Loop through and print job descriptions
    for job in data:
        job_id = job.get("id", "N/A")
        title = job.get("title", "N/A")
        company = job.get("companyName", "N/A")
        description = job.get("descriptionText", "No description available")

        print("=" * 80)
        print(f"Job ID: {job_id}")
        print(f"Title: {title}")
        print(f"Company: {company}")
        print("\nDescription:\n")
        print(description)
        print("=" * 80)
        print("\n")

if __name__ == "__main__":
    extract_job_descriptions("jobs.json")
