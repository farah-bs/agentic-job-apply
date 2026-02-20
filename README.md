# Agentic Job Application Pipeline

A LangGraph-powered multi-agent system that analyzes a job posting, researches the company, and rewrites your LaTeX résumé to fit automatically.

## Architecture

```
Job URL + LaTeX Résumé
        │
        ▼
┌─────────────────────┐
│  Agent 1            │  Fetches job posting URL, extracts structured
│  Job Analyzer       │  job profile: skills, responsibilities, keywords
└────────┬────────────┘
         │ job_profile.json
         ▼
┌─────────────────────┐
│  Agent 2            │  Searches Tavily for company info: mission,
│  Company Researcher │  tech stack, culture, recent news
└────────┬────────────┘
         │ company_brief.json
         ▼
┌─────────────────────┐
│  Agent 3            │  Compares résumé vs job, produces surgical
│  Résumé Strategist  │  edit plan: bullet rewrites, keyword injections
└────────┬────────────┘
         │ edit_plan.json
         ▼
┌─────────────────────┐
│  Agent 4            │  Applies all changes to your .tex file while
│  LaTeX Refactorer   │  preserving LaTeX structure and formatting
└────────┬────────────┘
         │ tailored_resume.tex
         ▼
┌─────────────────────┐  (optional, --cover-letter flag)
│  Agent 5            │  Writes a personalized cover letter in LaTeX
│  Cover Letter Writer│  using all gathered context
└────────┬────────────┘
         │
         ▼
    output/ directory
```

## Setup (with uv virtual environment)

1. **Install [uv](https://github.com/astral-sh/uv) if you don't have it:**
        ```
        pip install uv
        ```

2. **Create and activate a uv virtual environment:**
        ```
        uv venv .venv
        source .venv/bin/activate
        ```

3. **Install dependencies from requirements.txt:**
        ```
        uv pip install -r requirements.txt
        ```
