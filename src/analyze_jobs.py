import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm
from notion_client import Client as NotionClient
from datetime import datetime
import tiktoken

format_example = """
Here are two examples of the expected JSON output:

✅ Good fit:
{
  "rating": 8.5,
  "explanation": "You meet the role’s requirements with a CS degree and hands-on experience in full-stack development, API integrations, and automation. His resume shows strong technical skills across languages, frameworks, and DevOps tools. He has worked in client-facing environments and supported onboarding, which adds value in cross-functional teams. The role may be slightly junior given his background, but he aligns well with the core responsibilities. Rating: 8.5/10."
}

❌ Poor fit:
{
  "rating": 3,
  "explanation": "You lack direct experience with embedded systems and low-level C/C++ development required for this role. While he has strong full-stack and integration skills, they are not aligned with the job’s focus on firmware and hardware interfacing. His resume doesn't show relevant experience with real-time systems or device-level testing. This role would require a significant learning curve. Rating: 3/10."
}
"""

load_dotenv()
openai_client = OpenAI()
notion = NotionClient(auth=os.getenv("NOTION_API_KEY"))
DATABASE_ID = os.getenv("NOTION_DB_ID")

encoding_35 = tiktoken.encoding_for_model("gpt-3.5-turbo")
encoding_4 = tiktoken.encoding_for_model("gpt-4")

os.makedirs("logs", exist_ok=True)
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file_path = f"logs/run_log_{timestamp}.txt"
log_file = open(log_file_path, "w", encoding="utf-8")

def log(message: str):
    print(message)
    log_file.write(message + "\n")
    log_file.flush()

with open("resume.txt", "r", encoding="utf-8") as f:
    resume = f.read()

with open("condensed_jobs.json", "r", encoding="utf-8") as f:
    jobs = json.load(f)

if os.path.exists("rated_jobs.json"):
    with open("rated_jobs.json", "r", encoding="utf-8") as f:
        cached_results = json.load(f)
        seen_ids = set(job["id"] for job in cached_results)
else:
    cached_results = []
    seen_ids = set()

cumulative_tokens = 0
cumulative_cost = 0.0
processed_count = 0
used_gpt4_count = 0
skipped_cached_count = 0

def call_openai(prompt, model):
    response = openai_client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    usage = response.usage
    tokens = usage.total_tokens
    cost_per_1k = 0.0015 if model == "gpt-3.5-turbo" else 0.03
    cost = (tokens / 1000) * cost_per_1k
    return response.choices[0].message.content, tokens, cost

def rate_job_fit(job, resume_text):
    prompt = f"""
You are a career coach. Based on the following resume:

{resume}

Evaluate the candidate's fit for the following job:

Job Title: {job.get('title')}
Company: {job.get('company')}
Location: {job.get('location')}
Job Description:
{job.get('description')}

Make sure to keep in mind the year of experience as well as the seniority level of the role. I am an associate and have both technical and client-facing experience.

Do not use any frilly language and be spartan

Respond with a JSON object like:
{{"rating": number from 1 to 10, "explanation": "brief reasoning for the score"}}

Limit your explanation to no more than 300 tokens.

Use this example to format your explanations and adhere to it.

{format_example}
"""
    global cumulative_tokens, cumulative_cost, used_gpt4_count

    content, tokens_35, cost_35 = call_openai(prompt, "gpt-3.5-turbo")
    try:
        result = json.loads(content)
        explanation = result.get("explanation", "")

        if result["rating"] in [4, 5, 6] or len(explanation.split()) < 25:
            log("\U0001f501 Using GPT-4 due to vague/mid result")
            used_gpt4_count += 1
            content, tokens_4, cost_4 = call_openai(prompt, "gpt-4")
            result = json.loads(content)
            tokens_total = tokens_35 + tokens_4
            cost_total = cost_35 + cost_4
            explanation_tokens = len(encoding_4.encode(result["explanation"]))
        else:
            tokens_total = tokens_35
            cost_total = cost_35
            explanation_tokens = len(encoding_35.encode(result["explanation"]))

        cumulative_tokens += tokens_total
        cumulative_cost += cost_total

        log("───────── Job Summary ─────────")
        log(f"Job Title: {job['title']}")
        log(f"Rating: {result['rating']}")
        log(f"Explanation: {result['explanation'][:100]}...")
        log(f"Explanation Tokens: {explanation_tokens}")
        log(f"Tokens Used: {tokens_total} | Cost: ${cost_total:.4f} | Cumulative Cost: ${cumulative_cost:.4f}")
        log("──────────────────────────")
        return result

    except json.JSONDecodeError:
        log("\u26a0\ufe0f JSON decode error. Raw content:")
        log(content)
        raise

def update_notion_entry(job_id, rating, explanation):
    try:
        query_result = notion.databases.query(
            database_id=DATABASE_ID,
            filter={
                "property": "Job ID",
                "rich_text": {"equals": str(job_id)}
            }
        )
        if not query_result["results"]:
            log(f"\u26a0\ufe0f No Notion entry found for Job ID {job_id}")
            return

        page_id = query_result["results"][0]["id"]
        notion.pages.update(
            page_id=page_id,
            properties={
                "Rating": {"number": rating},
                "Explanation": {"rich_text": [{"text": {"content": explanation[:2000]}}]}
            }
        )
        log(f"✅ Updated Notion for Job ID {job_id}")

    except Exception as e:
        log(f"❌ Failed to update Notion for Job ID {job_id}: {e}")

for job in tqdm(jobs, desc="Analyzing and Updating Jobs"):
    if job["id"] in seen_ids:
        log(f"⏩ Skipping cached job ID {job['id']}")
        skipped_cached_count += 1
        continue

    try:
        evaluation = rate_job_fit(job, resume)
        update_notion_entry(job["id"], evaluation["rating"], evaluation["explanation"])
        cached_results.append({
            "id": job["id"],
            "rating": evaluation["rating"],
            "explanation": evaluation["explanation"]
        })
        seen_ids.add(job["id"])
        processed_count += 1
    except Exception as e:
        log(f"❌ Error processing job '{job.get('title')}' at '{job.get('company')}': {e}")
        continue

with open("rated_jobs.json", "w", encoding="utf-8") as f:
    json.dump(cached_results, f, indent=2)

log(f"✅ Total Jobs Processed: {processed_count}")
log(f"⏩ Skipped from Cache: {skipped_cached_count}")
log(f"🫠 GPT-4 Used for: {used_gpt4_count} jobs")
log(f"✅ All jobs processed and updated in Notion.")
log_file.close()
