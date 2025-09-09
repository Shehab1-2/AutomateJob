# job_analyzer_lib/config.py
import os
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Config:
    # OpenAI Models
    PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "gpt-5")
    BACKUP_MODEL = os.getenv("BACKUP_MODEL", "gpt-5")
    
    # Cost per 1K tokens ($) - Updated with actual OpenAI pricing
    MODEL_COSTS = {
        "gpt-3.5-turbo": 0.0015,
        "gpt-4": 0.03,
        "gpt-4o": 0.005,      # Updated pricing
        "gpt-4o-mini": 0.00015, # Updated pricing
        "gpt-5": 0.01125,
        "gpt-5-mini": 0.00225,
        "gpt-5-nano": 0.00045,
    }
    
    # Evaluation thresholds
    MIN_EXPLANATION_WORDS = 30
    VAGUE_RATING_RANGE = (4, 6)
    MAX_EXPLANATION_TOKENS = 1000
    MINIMUM_RATING_THRESHOLD = 7  # Only jobs rated 7+ go to Notion database
    
    # File paths
    RESUME_FILE = "resume.txt"
    FILTERED_DIR = Path(__file__).resolve().parents[2] / "filtered" / "filter_data"
    CACHE_FILE = str(Path(__file__).resolve().parents[1] / "rated_jobs.json")
    LOG_DIR = str(Path(__file__).resolve().parents[1] / "log")

    
    # Notion field limits
    NOTION_TEXT_LIMIT = 2000