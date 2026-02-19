import re
import json

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


SYSTEM_PROMPT = """You are an expert LaTeX editor and résumé writer.
You will receive a LaTeX résumé and a set of edit instructions.
Apply all changes faithfully while:
- Preserving ALL LaTeX structure, commands, packages, and preamble EXACTLY
- Never breaking LaTeX syntax
- Making the résumé read naturally after edits
- Injecting keywords organically, not robotically
- Maintaining consistent tense (past for previous roles, present for current)

Return ONLY the complete, valid, modified LaTeX source. No explanation, no markdown fences.
"""

REFACTOR_PROMPT = """Apply the following edit plan to this LaTeX résumé.

EDIT PLAN:
{edit_plan_json}

JOB CONTEXT (for reference):
- Job Title: {job_title}
- Key Required Skills: {required_skills}
- ATS Keywords: {ats_keywords}

ORIGINAL LATEX RÉSUMÉ:
{resume_latex}

Instructions:
1. Apply all bullet_rewrites — find the original text and replace with the rewritten version
2. Rewrite the professional summary using summary_rewrite.new_summary
3. Update the skills section: add skills_to_add, remove skills_to_remove
4. Adjust section emphasis as directed (reorder, trim, expand)
5. Naturally inject keywords_to_inject throughout (don't just append them)
6. Apply experience_notes guidance for each role
7. Do NOT change: contact info, dates, company names, job titles, education facts
8. Do NOT break any LaTeX commands or environments

Return the complete modified LaTeX file, starting with the first line of the original.
"""


class LaTeXRefactorerAgent:
    def __init__(self, llm: BaseChatModel, verbose: bool = False):
        self.llm = llm
        self.verbose = verbose

        self.chain = (
            ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("human", REFACTOR_PROMPT),
            ])
            | self.llm
            | StrOutputParser()
        )

    def _validate_latex(self, latex: str) -> bool:
        """Basic sanity checks on output."""
        has_begin_doc = r"\begin{document}" in latex
        has_end_doc = r"\end{document}" in latex
        # Count balanced braces
        open_braces = latex.count("{")
        close_braces = latex.count("}")
        balanced = abs(open_braces - close_braces) < 10  # Allow small tolerance

        if self.verbose:
            print(f"   LaTeX validation: begin_doc={has_begin_doc}, end_doc={has_end_doc}, balanced_braces={balanced}")

        return has_begin_doc and has_end_doc and balanced

    def _strip_markdown_fences(self, text: str) -> str:
        """Remove any accidental markdown code fences from LLM output."""
        text = re.sub(r"^```(?:latex|tex)?\s*\n?", "", text.strip())
        text = re.sub(r"\n?```\s*$", "", text)
        return text.strip()

    def run(self, resume_latex: str, edit_plan: dict, job_profile: dict) -> str:
        required_skills = ", ".join(job_profile.get("required_skills", [])[:10])
        ats_keywords = ", ".join(job_profile.get("ats_keywords", [])[:15])

        if self.verbose:
            print(f"   Applying {len(edit_plan.get('bullet_rewrites', []))} bullet rewrites...")
            print(f"   Keywords to inject: {edit_plan.get('keywords_to_inject', [])[:5]}")

        raw_output = self.chain.invoke({
            "edit_plan_json": json.dumps(edit_plan, indent=2),
            "job_title": job_profile.get("job_title", ""),
            "required_skills": required_skills,
            "ats_keywords": ats_keywords,
            "resume_latex": resume_latex,
        })

        tailored_latex = self._strip_markdown_fences(raw_output)

        # Fallback: if output doesn't look like LaTeX, return original with a comment
        if not self._validate_latex(tailored_latex):
            print("   ⚠️  LaTeX validation failed — returning original with edit plan as comments")
            edit_summary = json.dumps(edit_plan.get("overall_strategy", ""), indent=2)
            return f"% EDIT PLAN:\n% {edit_summary}\n\n{resume_latex}"

        return tailored_latex
