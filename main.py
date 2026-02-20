import argparse
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from pipeline import run_pipeline

# Load environment variables from .env file
load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Agentic Job Application Pipeline")
    parser.add_argument(
        "--url", 
        required=True, 
        help="Job posting URL or path to .txt/.md file with job description (for sites that block scraping)"
    )
    parser.add_argument("--resume", required=True, help="Path to your LaTeX résumé (.tex)")
    parser.add_argument("--output-dir", default="output", help="Directory for output files")
    parser.add_argument("--cover-letter", action="store_true", help="Also generate a cover letter")
    parser.add_argument("--verbose", action="store_true", help="Print agent reasoning steps")
    args = parser.parse_args()

    resume_path = Path(args.resume)
    if not resume_path.exists():
        print(f"Resume file not found: {resume_path}")
        return

    print("\nStarting Job Application Pipeline\n")
    print(f"Job URL  : {args.url}")
    print(f"Resume   : {args.resume}")
    print(f"Output   : {args.output_dir}")
    print(f"Cover Letter: {'Yes' if args.cover_letter else 'No'}")
    print("\n" + "─" * 50 + "\n")

    asyncio.run(run_pipeline(
        job_url=args.url,
        resume_path=str(resume_path),
        output_dir=args.output_dir,
        generate_cover_letter=args.cover_letter,
        verbose=args.verbose,
    ))


if __name__ == "__main__":
    main()
