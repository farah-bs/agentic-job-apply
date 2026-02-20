import json
import os
from pathlib import Path
from typing import TypedDict, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END

from agents.job_analyzer import JobAnalyzerAgent
from agents.company_researcher import CompanyResearcherAgent
from agents.resume_strategist import ResumeStrategistAgent
from agents.latex_refactorer import LaTeXRefactorerAgent
from agents.cover_letter_writer import CoverLetterWriterAgent
from utils.llm_factory import get_llm
from utils.printer import print_step, print_result
from utils.pdf_compiler import compile_with_retry


# ─── Pipeline State ────────────────────────────────────────────────────────────

class PipelineState(TypedDict):
    # Inputs
    job_url: str
    resume_latex: str
    output_dir: str
    generate_cover_letter: bool
    verbose: bool

    # Agent outputs
    job_profile: Optional[dict]          # From JobAnalyzer
    company_brief: Optional[dict]        # From CompanyResearcher
    edit_plan: Optional[dict]            # From ResumeStrategist
    tailored_resume_latex: Optional[str] # From LaTeXRefactorer
    cover_letter_latex: Optional[str]    # From CoverLetterWriter

    # Metadata
    errors: list[str]
    completed_steps: list[str]


# ─── Node Functions ─────────────────────────────────────────────────────────────

def run_job_analyzer(state: PipelineState) -> PipelineState:
    print_step("1/5", "Job Analyzer", "Fetching and analyzing job posting...")
    try:
        llm = get_llm()
        agent = JobAnalyzerAgent(llm=llm, verbose=state["verbose"])
        job_profile = agent.run(job_url=state["job_url"])
        print_result("Job analyzed", f"{job_profile.get('job_title', 'Unknown')} @ {job_profile.get('company_name', 'Unknown')}")
        return {**state, "job_profile": job_profile, "completed_steps": state["completed_steps"] + ["job_analyzer"]}
    except Exception as e:
        print(f"\nCRITICAL ERROR: Job Analyzer failed: {e}")
        print("\nPipeline cannot continue without job analysis. Exiting...")
        raise SystemExit(1)


def run_company_researcher(state: PipelineState) -> PipelineState:
    if state.get('job_profile') is None:
        print("\nCRITICAL ERROR: Cannot run Company Researcher without job_profile")
        raise SystemExit(1)
    
    print_step("2/5", "Company Researcher", f"Researching {state['job_profile'].get('company_name', 'company')}...")
    try:
        llm = get_llm()
        agent = CompanyResearcherAgent(llm=llm, verbose=state["verbose"])
        company_brief = agent.run(
            company_name=state["job_profile"].get("company_name", ""),
            company_website=state["job_profile"].get("company_website", ""),
        )
        print_result("Company researched", company_brief.get("summary", "")[:80] + "...")
        return {**state, "company_brief": company_brief, "completed_steps": state["completed_steps"] + ["company_researcher"]}
    except Exception as e:
        print(f"\nCRITICAL ERROR: Company Researcher failed: {e}")
        print("\nPipeline cannot continue without company research. Exiting...")
        raise SystemExit(1)


def run_resume_strategist(state: PipelineState) -> PipelineState:
    if state.get('job_profile') is None:
        print("\nCRITICAL ERROR: Cannot run Résumé Strategist without job_profile")
        raise SystemExit(1)
    
    print_step("3/5", "Résumé Strategist", "Planning tailoring strategy...")
    try:
        llm = get_llm()
        agent = ResumeStrategistAgent(llm=llm, verbose=state["verbose"])
        edit_plan = agent.run(
            job_profile=state["job_profile"],
            company_brief=state.get("company_brief", {}),
            resume_latex=state["resume_latex"],
        )
        n_changes = len(edit_plan.get("bullet_rewrites", [])) + len(edit_plan.get("section_changes", []))
        print_result("Strategy ready", f"{n_changes} planned changes")
        return {**state, "edit_plan": edit_plan, "completed_steps": state["completed_steps"] + ["resume_strategist"]}
    except Exception as e:
        print(f"\nCRITICAL ERROR: Résumé Strategist failed: {e}")
        print("\nPipeline cannot continue without edit plan. Exiting...")
        raise SystemExit(1)


def run_latex_refactorer(state: PipelineState) -> PipelineState:
    if state.get('edit_plan') is None or state.get('job_profile') is None:
        print("\nCRITICAL ERROR: Cannot run LaTeX Refactorer without edit_plan or job_profile")
        raise SystemExit(1)
    
    print_step("4/5", "LaTeX Refactorer", "Rewriting résumé LaTeX...")
    try:
        llm = get_llm()
        agent = LaTeXRefactorerAgent(llm=llm, verbose=state["verbose"])
        tailored_latex = agent.run(
            resume_latex=state["resume_latex"],
            edit_plan=state["edit_plan"],
            job_profile=state["job_profile"],
        )
        print_result("Résumé rewritten", f"{len(tailored_latex)} characters of LaTeX")
        return {**state, "tailored_resume_latex": tailored_latex, "completed_steps": state["completed_steps"] + ["latex_refactorer"]}
    except Exception as e:
        print(f"\nCRITICAL ERROR: LaTeX Refactorer failed: {e}")
        print("\nPipeline cannot continue without tailored résumé. Exiting...")
        raise SystemExit(1)


def run_cover_letter_writer(state: PipelineState) -> PipelineState:
    if not state.get("generate_cover_letter"):
        return state
    
    if state.get('job_profile') is None:
        print("\nCRITICAL ERROR: Cannot write cover letter without job_profile")
        raise SystemExit(1)
    
    print_step("5/5", "Cover Letter Writer", "Drafting tailored cover letter...")
    try:
        llm = get_llm()
        agent = CoverLetterWriterAgent(llm=llm, verbose=state["verbose"])
        cover_letter = agent.run(
            job_profile=state["job_profile"],
            company_brief=state.get("company_brief", {}),
            resume_latex=state["resume_latex"],
        )
        print_result("Cover letter ready", f"{len(cover_letter)} characters")
        return {**state, "cover_letter_latex": cover_letter, "completed_steps": state["completed_steps"] + ["cover_letter_writer"]}
    except Exception as e:
        print(f"\nCRITICAL ERROR: Cover Letter Writer failed: {e}")
        print("\nCover letter generation failed. Exiting...")
        raise SystemExit(1)


def save_outputs(state: PipelineState) -> PipelineState:
    if not state.get("tailored_resume_latex"):
        print("\nCRITICAL ERROR: No tailored résumé to save")
        raise SystemExit(1)
    
    print_step("✓", "Saving Outputs", "Writing files to disk...")
    output_dir = Path(state["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    company = state.get("job_profile", {}).get("company_name", "company").replace(" ", "_")
    role = state.get("job_profile", {}).get("job_title", "role").replace(" ", "_")
    base_name = f"{company}_{role}_{timestamp}"

    saved = []

    # Tailored résumé
    if state.get("tailored_resume_latex"):
        resume_path = output_dir / f"{base_name}_resume.tex"
        resume_path.write_text(state["tailored_resume_latex"])
        saved.append(str(resume_path))
        # Compile to PDF via LaTeX.Online
        try:
            pdf_path = compile_with_retry(str(resume_path))
            saved.append(pdf_path)
        except Exception as e:
            print(f"PDF compilation failed (your .tex is still saved): {e}")

    # Cover letter
    if state.get("cover_letter_latex"):
        cl_path = output_dir / f"{base_name}_cover_letter.tex"
        cl_path.write_text(state["cover_letter_latex"])
        saved.append(str(cl_path))
        # Compile to PDF via LaTeX.Online
        try:
            pdf_path = compile_with_retry(str(cl_path))
            saved.append(pdf_path)
        except Exception as e:
            print(f"Cover letter PDF compilation failed: {e}")

    # Job profile JSON (for reference)
    if state.get("job_profile"):
        jp_path = output_dir / f"{base_name}_job_profile.json"
        jp_path.write_text(json.dumps(state["job_profile"], indent=2))
        saved.append(str(jp_path))

    # Company brief JSON
    if state.get("company_brief"):
        cb_path = output_dir / f"{base_name}_company_brief.json"
        cb_path.write_text(json.dumps(state["company_brief"], indent=2))
        saved.append(str(cb_path))

    # Edit plan JSON
    if state.get("edit_plan"):
        ep_path = output_dir / f"{base_name}_edit_plan.json"
        ep_path.write_text(json.dumps(state["edit_plan"], indent=2))
        saved.append(str(ep_path))

    print("\nPipeline complete! Files saved:")
    for f in saved:
        print(f"{f}")

    return state


# ─── Routing ────────────────────────────────────────────────────────────────────

def should_write_cover_letter(state: PipelineState) -> str:
    return "cover_letter" if state.get("generate_cover_letter") else "save"


# ─── Graph Assembly ─────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(PipelineState)

    graph.add_node("job_analyzer",        run_job_analyzer)
    graph.add_node("company_researcher",  run_company_researcher)
    graph.add_node("resume_strategist",   run_resume_strategist)
    graph.add_node("latex_refactorer",    run_latex_refactorer)
    graph.add_node("cover_letter",        run_cover_letter_writer)
    graph.add_node("save",                save_outputs)

    graph.set_entry_point("job_analyzer")
    graph.add_edge("job_analyzer",       "company_researcher")
    graph.add_edge("company_researcher", "resume_strategist")
    graph.add_edge("resume_strategist",  "latex_refactorer")
    graph.add_conditional_edges("latex_refactorer", should_write_cover_letter, {
        "cover_letter": "cover_letter",
        "save":         "save",
    })
    graph.add_edge("cover_letter", "save")
    graph.add_edge("save", END)

    return graph.compile()


# ─── Runner ─────────────────────────────────────────────────────────────────────

async def run_pipeline(
    job_url: str,
    resume_path: str,
    output_dir: str = "output",
    generate_cover_letter: bool = False,
    verbose: bool = False,
):
    resume_latex = Path(resume_path).read_text()

    initial_state: PipelineState = {
        "job_url": job_url,
        "resume_latex": resume_latex,
        "output_dir": output_dir,
        "generate_cover_letter": generate_cover_letter,
        "verbose": verbose,
        "job_profile": None,
        "company_brief": None,
        "edit_plan": None,
        "tailored_resume_latex": None,
        "cover_letter_latex": None,
        "errors": [],
        "completed_steps": [],
    }

    graph = build_graph()
    await graph.ainvoke(initial_state)
