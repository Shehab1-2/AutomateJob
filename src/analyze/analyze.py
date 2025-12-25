# analyze.py
import argparse
from dotenv import load_dotenv
from job_analyzer_lib.evaluator import JobEvaluator

def main():
    """Main entry point for the job evaluation script."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run job analysis and evaluation.")
    parser.add_argument('--no-explanation', action='store_true', 
                       help='Skip AI-generated explanations and use placeholder text')
    args = parser.parse_args()
    
    # Load environment variables from a .env file
    load_dotenv()
    
    # Initialize and run the job evaluator
    evaluator = JobEvaluator(skip_explanations=args.no_explanation)
    evaluator.run()

if __name__ == "__main__":
    main()