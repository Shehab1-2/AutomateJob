# job_analyzer_lib/services.py
import json
import os
import time
from typing import Dict, Tuple, Any

import tiktoken
from notion_client import Client as NotionClient
from openai import OpenAI

from .config import Config
from .utils import Logger, JobEvaluationError, ApplicationTypeDetector

class OpenAIClient:
    """Enhanced OpenAI client with better error handling and token management."""
    
    def __init__(self, logger: Logger):
        self.client = OpenAI()
        self.logger = logger
        self.encoding = tiktoken.get_encoding("cl100k_base")
        self.cumulative_tokens = 0
        self.cumulative_cost = 0.0
        self.gpt4_usage_count = 0

    def _calculate_cost(self, tokens: int, model: str) -> float:
        """Calculate API cost based on token usage."""
        cost_per_1k = Config.MODEL_COSTS.get(model, 0.01)
        return (tokens / 1000) * cost_per_1k

    # --- CHANGE 1: This method now accepts separate system and user prompts ---
    def _make_api_call(self, system_prompt: str, user_prompt: str, model: str, max_retries: int = 3) -> Tuple[str, int, float]:
        """Make OpenAI API call with retry logic using system and user roles."""
        for attempt in range(max_retries):
            try:
                completion_params = {
                    "model": model,
                    # --- CHANGE 2: Use both a system and user message ---
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.7,
                    "timeout": 30
                }
                if model in ["gpt-5", "gpt-5-mini", "gpt-5-nano"]:
                    completion_params["max_completion_tokens"] = 400
                else:
                    completion_params["max_tokens"] = 400

                response = self.client.chat.completions.create(**completion_params)
                usage = response.usage
                tokens = usage.total_tokens
                cost = self._calculate_cost(tokens, model)
                
                # Get response content and validate it's not empty
                content = response.choices[0].message.content
                if not content or content.strip() == "":
                    raise ValueError(f"Empty response from OpenAI model {model}")
                
                return content, tokens, cost
            except Exception as e:
                if attempt == max_retries - 1:
                    raise JobEvaluationError(f"OpenAI API call failed after {max_retries} attempts: {e}")
                wait_time = 2 ** attempt
                self.logger.warning(f"API call attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
        raise JobEvaluationError("API call failed after all retries.")

    def _clean_json_response(self, content: str) -> str:
        """Clean OpenAI response by removing markdown code blocks and extra text."""
        # Remove markdown code blocks
        if "```json" in content:
            # Extract content between ```json and ```
            start = content.find("```json") + 7
            end = content.find("```", start)
            if end != -1:
                content = content[start:end].strip()
        elif "```" in content:
            # Handle plain ``` blocks
            start = content.find("```") + 3
            end = content.find("```", start)
            if end != -1:
                content = content[start:end].strip()
        
        return content.strip()

    def _needs_gpt4_evaluation(self, result: Dict[str, Any], explanation: str) -> bool:
        """Determine if GPT-4 evaluation is needed based on quality metrics."""
        rating = result.get("rating", 0)
        word_count = len(explanation.split())
        is_vague_rating = Config.VAGUE_RATING_RANGE[0] <= rating <= Config.VAGUE_RATING_RANGE[1]
        is_insufficient_explanation = word_count < Config.MIN_EXPLANATION_WORDS
        generic_phrases = ["good fit", "aligns well", "strong background", "relevant experience", "would be suitable", "meets requirements", "has experience"]
        has_generic_language = any(phrase in explanation.lower() for phrase in generic_phrases)
        return is_vague_rating or is_insufficient_explanation or has_generic_language

    def evaluate_job_fit(self, job: Dict[str, Any], resume_text: str) -> Dict[str, Any]:
        """Evaluate job fit using enhanced prompt and model selection logic."""
        # --- CHANGE 3: Get both prompts and pass them to the API call ---
        system_prompt, user_prompt = self._create_evaluation_prompt(job, resume_text)
        content, tokens_primary, cost_primary = self._make_api_call(system_prompt, user_prompt, Config.PRIMARY_MODEL)

        try:
            # Log the raw response for debugging
            self.logger.info(f"📋 Raw OpenAI response (first 200 chars): {content[:200]}")
            
            # Clean the response - remove markdown code blocks if present
            cleaned_content = self._clean_json_response(content)
            
            result = json.loads(cleaned_content)
            self._validate_evaluation_result(result)
            explanation = result.get("explanation", "")
            
            if self._needs_gpt4_evaluation(result, explanation):
                self.logger.info("🔁 Using backup model for higher quality evaluation")
                self.gpt4_usage_count += 1
                content, tokens_backup, cost_backup = self._make_api_call(system_prompt, user_prompt, Config.BACKUP_MODEL)
                cleaned_content = self._clean_json_response(content)
                result = json.loads(cleaned_content)
                self._validate_evaluation_result(result)
                total_tokens = tokens_primary + tokens_backup
                total_cost = cost_primary + cost_backup
            else:
                total_tokens = tokens_primary
                total_cost = cost_primary
            
            explanation_tokens = len(self.encoding.encode(result["explanation"]))
            self.cumulative_tokens += total_tokens
            self.cumulative_cost += total_cost
            self._log_evaluation_summary(job, result, explanation_tokens, total_tokens, total_cost)
            return result
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}\nRaw content: {content}")
            raise JobEvaluationError(f"Failed to parse OpenAI response: {e}")

    # --- CHANGE 4: This method now returns two separate strings ---
    def _create_evaluation_prompt(self, job: Dict[str, Any], resume_text: str) -> Tuple[str, str]:
        """Create enhanced structured evaluation prompt with system and user messages."""
        
        system_prompt = """You are a precise, analytical technical recruiter with 15+ years of experience. Your sole task is to evaluate a candidate's job fit based on the provided resume and job details.

EVALUATION FRAMEWORK:
Rate 1-10 based on these weighted criteria:
• Technical Skills Match (40%): Stack, languages, frameworks, tools
• Experience Level (25%): Years, seniority, scope of responsibility
• Domain Relevance (20%): Industry, business model, problem space
• Soft Skills Alignment (15%): Client-facing, teamwork, communication

REQUIREMENTS:
- Be precise and specific about skill gaps or overlaps.
- Reference concrete resume evidence.
- Consider learning curve and ramp-up time.
- Avoid generic phrases like "good fit" or "strong background".
- Stay under 300 tokens in the explanation.
- Use direct, factual language.

Your entire response MUST be a single, valid JSON object. Do NOT include any introductory text, conversation, apologies, or explanations outside of the JSON structure.

OUTPUT FORMAT:
{"rating": [1-10 number], "explanation": "[specific reasoning]"}
"""
        
        user_prompt = f"""CANDIDATE RESUME:
{resume_text}

JOB DETAILS:
Title: {job.get('title', 'N/A')}
Company: {job.get('company', 'N/A')}
Location: {job.get('location', 'N/A')}
Seniority: {job.get('seniorityLevel', 'N/A')}
Description: {job.get('description', 'N/A')}
"""
        return system_prompt, user_prompt

    def _validate_evaluation_result(self, result: Dict[str, Any]):
        """Validate the evaluation result structure."""
        if not isinstance(result, dict):
            raise JobEvaluationError("Evaluation result must be a dictionary")
        if "rating" not in result:
            raise JobEvaluationError("Evaluation result missing 'rating' field")
        if "explanation" not in result:
            raise JobEvaluationError("Evaluation result missing 'explanation' field")
        rating = result["rating"]
        if not isinstance(rating, (int, float)) or not 1 <= rating <= 10:
            raise JobEvaluationError(f"Rating must be a number between 1-10, got: {rating}")

    def _log_evaluation_summary(self, job: Dict[str, Any], result: Dict[str, Any], explanation_tokens: int, total_tokens: int, total_cost: float):
        """Log structured evaluation summary."""
        self.logger.info("═" * 50)
        self.logger.info(f"JOB: {job.get('title', 'Unknown')} at {job.get('company', 'Unknown')}")
        self.logger.info(f"RATING: {result['rating']}/10")
        self.logger.info(f"EXPLANATION: {result['explanation'][:100]}...")
        self.logger.info(f"TOKENS: {explanation_tokens} explanation | {total_tokens} total")
        self.logger.info(f"COST: ${total_cost:.4f} | CUMULATIVE: ${self.cumulative_cost:.4f}")
        self.logger.info("═" * 50)

    def get_usage_summary(self) -> Dict[str, Any]:
        """Get usage summary for final reporting."""
        return {"total_tokens": self.cumulative_tokens, "total_cost": self.cumulative_cost, "gpt4_calls": self.gpt4_usage_count}


class NotionService:
    """Enhanced Notion client with better error handling."""
    
    def __init__(self, database_id: str, logger: Logger):
        self.client = NotionClient(auth=os.getenv("NOTION_API_KEY"))
        self.database_id = database_id
        self.logger = logger
        self.app_detector = ApplicationTypeDetector()

    def create_job_page(self, job: Dict[str, Any], max_retries: int = 3) -> bool:
        """Create a job page in Notion with retry logic."""
        for attempt in range(max_retries):
            try:
                properties = self._build_job_properties(job)
                self.client.pages.create(parent={"database_id": self.database_id}, properties=properties)
                self.logger.info(f"✅ Added job ID {job.get('id', 'unknown')} to Notion")
                return True
            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(f"❌ Failed to add job ID {job.get('id', 'unknown')} to Notion after {max_retries} attempts")
                    self.logger.error(f"❌ Error details: {type(e).__name__}: {e}")
                    self.logger.error(f"❌ Database ID: {self.database_id}")
                    return False
                wait_time = 2 ** attempt
                self.logger.warning(f"Notion API attempt {attempt + 1} failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
        return False

    def _build_job_properties(self, job: Dict[str, Any]) -> Dict[str, Any]:
        """Build Notion properties from job data."""
        def safe_text(value: Any, max_length: int = Config.NOTION_TEXT_LIMIT) -> str:
            if value is None: return ""
            text = str(value)
            return text[:max_length]

        def safe_number(value: Any) -> int:
            try: return int(value) if value is not None else 0
            except (ValueError, TypeError): return 0
        
        def safe_url(value: Any) -> str:
            if value and str(value).startswith(('http://', 'https://')): return str(value)
            return "https://www.linkedin.com"

        application_type = self.app_detector.detect_application_type(job.get("applyUrl", ""))
        
        return {
            "Job Title": {"title": [{"text": {"content": safe_text(job.get("title", "Untitled"))}}]},
            "Company": {"rich_text": [{"text": {"content": safe_text(job.get("company", ""))}}]},
            "Location": {"rich_text": [{"text": {"content": safe_text(job.get("location", ""))}}]},
            "Rating": {"number": job.get("rating", 0)},
            "Explanation": {"rich_text": [{"text": {"content": safe_text(job.get("explanation", ""))}}]},
            "Link": {"url": safe_url(job.get("link"))},
            "Apply URL": {"url": safe_url(job.get("applyUrl"))},
            "Type": {"rich_text": [{"text": {"content": application_type}}]},
            "Date Posted": {"date": {"start": job.get("postedAt", "2025-01-01")}},
            "Job ID": {"rich_text": [{"text": {"content": safe_text(job.get("id", "0"))}}]},
            "Seniority Level": {"select": {"name": safe_text(job.get("seniorityLevel", "N/A"))}},
            "Employment Type": {"select": {"name": safe_text(job.get("employmentType", "N/A"))}},
            "Job Function": {"rich_text": [{"text": {"content": safe_text(job.get("jobFunction", ""))}}]},
            "Industries": {"rich_text": [{"text": {"content": safe_text(job.get("industries", ""))}}]},
            "Company Size": {"number": safe_number(job.get("companyEmployeesCount"))},
            "Company Description": {"rich_text": [{"text": {"content": safe_text(job.get("companyDescription", ""))}}]}
        }