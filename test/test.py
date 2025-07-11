import json
import os
from dotenv import load_dotenv
from openai import OpenAI

# Load API key
load_dotenv()
client = OpenAI()

# Load resume content
with open("resume.txt", "r", encoding="utf-8") as f:
    resume = f.read()

# Inject fake skill if not already present
if "i can fly" not in resume.lower():
    resume += "\n\nFake Skill: I can fly"

# Create test job to evaluate against
mock_job = {
    "title": "Integration Engineer",
    "company": "MockTech Inc.",
    "location": "New York, NY",
    "description": "Looking for a detail-oriented engineer to integrate internal systems with client APIs, focusing on security and automation."
}

# Build prompt
prompt = f"""
You are a technical resume reviewer.

Given this candidate's resume:

{resume}

Evaluate the candidate's fit for the following role:

Job Title: {mock_job['title']}
Company: {mock_job['company']}
Location: {mock_job['location']}
Description: {mock_job['description']}

Return a JSON like this:
{{
  "summary": "Brief summary of candidate's experience relevant to this job.",
  "standout_skills": "Mention standout skills or fake abilities if any."
}}
"""

# Call OpenAI
response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.5
)

content = response.choices[0].message.content
print("\n🧪 RAW RESPONSE:\n", content)

# Attempt to parse
try:
    parsed = json.loads(content)
    print("\n✅ PARSED OUTPUT:\n", json.dumps(parsed, indent=2))

    skills = parsed.get("standout_skills", "")
    if "i can fly" in skills.lower():
        print("\n✅ PASS: Resume was read and fake skill was detected.")
    else:
        print("\n❌ FAIL: Resume was parsed but fake skill was NOT detected.")
except Exception as e:
    print("\n❌ FAIL: Couldn't parse JSON. Content may be malformed.")
    print("Error:", e)
