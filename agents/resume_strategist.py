import json
import re

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


SYSTEM_PROMPT = """You are an expert résumé strategist and career coach. 
You analyze job requirements and résumés to produce a precise, actionable edit plan.
Focus on: keyword alignment, impact quantification, relevance ordering, and tone.
Always respond with a single valid JSON object. No markdown, no extra text.
"""

STRATEGY_PROMPT = """You are tailoring a candidate's résumé for a specific job.

JOB PROFILE:
{job_profile_json}

COMPANY BRIEF:
{company_brief_json}

CURRENT LATEX RÉSUMÉ:
{resume_latex}

Produce a detailed edit plan as JSON:
{{
  "overall_strategy": "2-3 sentence summary of the tailoring approach",
  "tone_notes": "how to adjust language to match company tone",

  "sections_to_emphasize": ["section names to move up or expand"],
  "sections_to_de_emphasize": ["section names to trim or remove"],
  "section_reorder": ["new ordered list of section names"],

  "summary_rewrite": {{
    "original_hint": "first few words of original summary",
    "new_summary": "full rewritten professional summary (2-3 sentences)"
  }},

  "bullet_rewrites": [
    {{
      "original": "exact original bullet point text (or first 60 chars)",
      "rewritten": "improved version that mirrors job language",
      "reason": "why this change"
    }}
  ],

  "keywords_to_inject": ["keyword1", "keyword2", ...],
  "skills_to_add": ["skill1", "skill2", ...],
  "skills_to_remove": ["skill1", "skill2", ...],

  "experience_notes": [
    {{
      "company_or_role": "...",
      "action": "emphasize | trim | remove | reorder",
      "note": "what to do specifically"
    }}
  ],

  "ats_optimizations": ["specific ATS tip 1", ...]
}}

Be specific and surgical. Only suggest changes that genuinely improve fit for this job.
Return only valid JSON.
"""


class ResumeStrategistAgent:
    def __init__(self, llm: BaseChatModel, verbose: bool = False):
        self.llm = llm
        self.verbose = verbose

        self.chain = (
            ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("human", STRATEGY_PROMPT),
            ])
            | self.llm
            | StrOutputParser()
        )

    def _parse_json(self, raw: str) -> dict:
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)

    def run(self, job_profile: dict, company_brief: dict, resume_latex: str) -> dict:
        if self.verbose:
            print(f"   Analyzing {len(job_profile.get('required_skills', []))} required skills...")
            print(f"   Résumé length: {len(resume_latex)} chars")

        raw_response = self.chain.invoke({
            "job_profile_json": json.dumps(job_profile, indent=2),
            "company_brief_json": json.dumps(company_brief, indent=2),
            "resume_latex": resume_latex,
        })

        if self.verbose:
            print(f"   Edit plan raw response preview:\n{raw_response[:300]}...")

        return self._parse_json(raw_response)
