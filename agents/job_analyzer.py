import json
import re
import requests
from bs4 import BeautifulSoup
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


SYSTEM_PROMPT = """You are an expert job posting analyst. 
Your job is to parse a raw job posting and extract structured information.
Always respond with a single valid JSON object. No markdown, no extra text.
"""

ANALYSIS_PROMPT = """Analyze this job posting and return a JSON object with these exact keys:

{{
  "job_title": "...",
  "company_name": "...",
  "company_website": "...",
  "location": "...",
  "remote_policy": "remote | hybrid | onsite | unknown",
  "seniority_level": "junior | mid | senior | lead | manager | unknown",
  "salary_range": "... or null",
  "employment_type": "full-time | part-time | contract | unknown",

  "required_skills": ["skill1", "skill2", ...],
  "preferred_skills": ["skill1", "skill2", ...],
  "technologies": ["tech1", "tech2", ...],

  "key_responsibilities": ["responsibility1", ...],
  "must_haves": ["must have 1", ...],
  "nice_to_haves": ["nice to have 1", ...],

  "ats_keywords": ["keyword1", ...],
  "tone": "startup | corporate | academic | nonprofit | unknown",
  "summary": "2-3 sentence summary of the role"
}}

Job Posting Content:
---
{job_content}
---

Return only valid JSON.
"""


class JobAnalyzerAgent:
    def __init__(self, llm: BaseChatModel, verbose: bool = False):
        self.llm = llm
        self.verbose = verbose

        self.chain = (
            ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("human", ANALYSIS_PROMPT),
            ])
            | self.llm
            | StrOutputParser()
        )

    def _fetch_job_page(self, url: str) -> str:
        """Fetch and parse raw text from a job posting URL."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        try:
            response = requests.get(url, headers=headers, timeout=15, verify=False)
            response.raise_for_status()
        except requests.RequestException as e:
            raise RuntimeError(f"Failed to fetch job page: {e}")

        soup = BeautifulSoup(response.text, "html.parser")

        # Remove noise
        for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
            tag.decompose()

        # Try to find main content block
        main = (
            soup.find("main") or
            soup.find(id=re.compile(r"job|content|description", re.I)) or
            soup.find(class_=re.compile(r"job|content|description|posting", re.I)) or
            soup.body
        )

        text = main.get_text(separator="\n") if main else soup.get_text(separator="\n")

        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned = "\n".join(lines)

        # Truncate to ~8000 chars to stay within context limits
        return cleaned[:8000]

    def _parse_json_response(self, raw: str) -> dict:
        """Extract JSON from LLM response, handling markdown fences."""
        raw = raw.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)

    def run(self, job_url: str) -> dict:
        if self.verbose:
            print(f"   Fetching: {job_url}")

        # Check if job_url is actually a file path
        from pathlib import Path
        job_path = Path(job_url)
        if job_path.exists() and job_path.is_file():
            if self.verbose:
                print(f"   Reading job description from file: {job_url}")
            job_content = job_path.read_text()[:8000]  # Truncate to 8000 chars
        else:
            job_content = self._fetch_job_page(job_url)

        if self.verbose:
            print(f"Fetched {len(job_content)} chars of job content")
            print("Sending to LLM for analysis...")

        raw_response = self.chain.invoke({"job_content": job_content})

        if self.verbose:
            print(f"Raw LLM response:\n{raw_response[:300]}...")

        job_profile = self._parse_json_response(raw_response)
        job_profile["source_url"] = job_url  

        return job_profile
