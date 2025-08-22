# job_analyzer_lib/utils.py
import logging
from datetime import datetime

class JobEvaluationError(Exception):
    """Custom exception for job evaluation errors."""
    pass

class Logger:
    """Enhanced logging with structured output."""
    
    def __init__(self, log_file_path: str):
        self.log_file = open(log_file_path, "w", encoding="utf-8")
        
        # Configure Python logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file_path),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def info(self, message: str):
        self.logger.info(message)
        self.log_file.write(f"{datetime.now().isoformat()} - INFO - {message}\n")
        self.log_file.flush()
    
    def error(self, message: str):
        self.logger.error(message)
        self.log_file.write(f"{datetime.now().isoformat()} - ERROR - {message}\n")
        self.log_file.flush()
    
    def warning(self, message: str):
        self.logger.warning(message)
        self.log_file.write(f"{datetime.now().isoformat()} - WARNING - {message}\n")
        self.log_file.flush()
    
    def close(self):
        self.log_file.close()

class ApplicationTypeDetector:
    """Detects the type of application system from apply URLs."""
    
    PATTERNS = {
        "Greenhouse": ["greenhouse.io", "boards.greenhouse.io", "app.greenhouse.io"],
        "Workday": ["workday.com", "myworkdayjobs.com", "wd1.myworkdayjobs.com", "wd5.myworkdayjobs.com", "workdayrecruiting.com"],
        "Lever": ["lever.co", "jobs.lever.co"],
        "BambooHR": ["bamboohr.com", "careers.bamboohr.com"],
        "SmartRecruiters": ["smartrecruiters.com", "jobs.smartrecruiters.com"],
        "Jobvite": ["jobvite.com", "app.jobvite.com"],
        "Ashby": ["ashbyhq.com", "jobs.ashbyhq.com"],
        "iCIMS": ["icims.com", "jobs.icims.com"],
        "Taleo": ["taleo.net", "chk.tbe.taleo.net"],
        "JazzHR": ["jazzhr.com", "recruiting.jazzhr.com"],
        "LinkedIn": ["linkedin.com/jobs", "www.linkedin.com/jobs"],
        "Indeed": ["indeed.com", "www.indeed.com"],
        "AngelList": ["angel.co", "www.angel.co", "angellist.com"],
        "ZipRecruiter": ["ziprecruiter.com", "www.ziprecruiter.com"],
        "Glassdoor": ["glassdoor.com", "www.glassdoor.com"]
    }
    
    @classmethod
    def detect_application_type(cls, apply_url: str) -> str:
        """Detect the application system type from the apply URL."""
        if not apply_url or not isinstance(apply_url, str):
            return "Unknown"
        
        apply_url = apply_url.lower().strip()
        
        for app_type, patterns in cls.PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in apply_url:
                    return app_type
        
        if any(indicator in apply_url for indicator in ["/careers", "/jobs", "/career", "/job", "/apply", "/hiring"]):
            return "Company Site"
        
        if any(ats_indicator in apply_url for ats_indicator in ["recruiting", "applicant", "candidate", "talent", "hr"]):
            return "ATS (Other)"
            
        return "Company Site"