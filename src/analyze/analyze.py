# analyze.py
from dotenv import load_dotenv
from job_analyzer_lib.evaluator import JobEvaluator

def main():
    """Main entry point for the job evaluation script."""
    # Load environment variables from a .env file
    load_dotenv()
    
    # Initialize and run the job evaluator
    evaluator = JobEvaluator()
    evaluator.run()

if __name__ == "__main__":
    main()