import json
import re

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


SYSTEM_PROMPT = """You are an expert cover letter writer. 
You write compelling, personalized cover letters that:
- Open with a strong hook (not "I am applying for...")
- Reference specific company details to show genuine interest
- Connect candidate's experience directly to job requirements
- Have a confident, professional tone matching the company culture
- Are concise (3-4 paragraphs, ~300-400 words)

You will produce a LaTeX cover letter document.
Return ONLY valid LaTeX source code — no markdown fences, no explanation.
"""

COVER_LETTER_PROMPT = """Write a cover letter for this candidate applying to this role.

JOB:
- Title: {job_title}
- Company: {company_name}
- Key Requirements: {required_skills}

COMPANY CONTEXT:
{company_brief_json}

CANDIDATE BACKGROUND (from their résumé):
{resume_summary}

COVER LETTER TONE: {tone}

Produce a complete LaTeX document using this template structure:

\\documentclass[11pt,letterpaper]{{letter}}
\\usepackage[margin=1in]{{geometry}}
\\usepackage{{hyperref}}

\\begin{{document}}

\\begin{{letter}}{{Hiring Manager \\\\ {company_name}}}

\\opening{{Dear Hiring Manager,}}

[3-4 paragraphs of cover letter content]

\\closing{{Sincerely,}}

[Candidate Name]

\\end{{letter}}
\\end{{document}}

Write the full document. Return only LaTeX, no markdown fences.
"""


def _extract_resume_summary(resume_latex: str) -> str:
    """Pull key info from the LaTeX résumé to give the LLM context."""
    # Strip LaTeX commands for a rough text extraction
    text = re.sub(r"\\[a-zA-Z]+\*?(\[.*?\])?\{", " ", resume_latex)
    text = re.sub(r"[{}\\]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:3000]  # First 3000 chars of cleaned text


class CoverLetterWriterAgent:
    def __init__(self, llm: BaseChatModel, verbose: bool = False):
        self.llm = llm
        self.verbose = verbose

        self.chain = (
            ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("human", COVER_LETTER_PROMPT),
            ])
            | self.llm
            | StrOutputParser()
        )

    def _strip_fences(self, text: str) -> str:
        text = re.sub(r"^```(?:latex|tex)?\s*\n?", "", text.strip())
        text = re.sub(r"\n?```\s*$", "", text)
        return text.strip()

    def run(self, job_profile: dict, company_brief: dict, resume_latex: str) -> str:
        tone = company_brief.get("tone", job_profile.get("tone", "professional"))
        required_skills = ", ".join(job_profile.get("required_skills", [])[:8])
        resume_summary = _extract_resume_summary(resume_latex)

        if self.verbose:
            print(f"   Writing cover letter with {tone} tone...")

        raw_output = self.chain.invoke({
            "job_title": job_profile.get("job_title", "the position"),
            "company_name": job_profile.get("company_name", "your company"),
            "required_skills": required_skills,
            "company_brief_json": json.dumps(company_brief, indent=2)[:2000],
            "resume_summary": resume_summary,
            "tone": tone,
        })

        return self._strip_fences(raw_output)
