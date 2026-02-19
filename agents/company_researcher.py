import json
import os
import re

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_community.tools.tavily_search import TavilySearchResults


SYSTEM_PROMPT = """You are a business intelligence researcher. 
Given search results about a company, extract key facts useful for tailoring a job application.
Always respond with a single valid JSON object — no markdown, no extra text.
"""

SYNTHESIS_PROMPT = """Based on the following search results about {company_name}, 
produce a structured company brief in JSON:

{{
  "company_name": "...",
  "industry": "...",
  "company_size": "startup (<50) | small (50-200) | mid (200-1000) | large (1000+) | unknown",
  "stage": "seed | series-a | series-b | growth | public | enterprise | unknown",
  "mission": "1-2 sentence mission statement or description",
  "products_services": ["product/service 1", ...],
  "tech_stack": ["technology 1", ...],
  "engineering_culture": "description of eng culture based on evidence",
  "recent_news": ["news item 1 (year)", ...],
  "values": ["value 1", ...],
  "tone": "startup-casual | professional | academic | mission-driven | enterprise",
  "notable_facts": ["fact useful for application 1", ...],
  "summary": "2-3 sentence paragraph to inform cover letter tone"
}}

Search Results:
---
{search_results}
---

Return only valid JSON.
"""


class CompanyResearcherAgent:
    def __init__(self, llm: BaseChatModel, verbose: bool = False):
        self.llm = llm
        self.verbose = verbose

        # Tavily search tool
        self.search_tool = TavilySearchResults(
            max_results=6,
            search_depth="advanced",
        )

        self.chain = (
            ChatPromptTemplate.from_messages([
                ("system", SYSTEM_PROMPT),
                ("human", SYNTHESIS_PROMPT),
            ])
            | self.llm
            | StrOutputParser()
        )

    def _search(self, query: str) -> list[dict]:
        if self.verbose:
            print(f"   🔍 Searching: {query}")
        results = self.search_tool.invoke(query)
        return results if isinstance(results, list) else []

    def _format_results(self, results: list[dict]) -> str:
        parts = []
        for i, r in enumerate(results, 1):
            url = r.get("url", "")
            content = r.get("content", "")[:600]
            parts.append(f"[{i}] {url}\n{content}")
        return "\n\n".join(parts)

    def _parse_json(self, raw: str) -> dict:
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        return json.loads(raw)

    def run(self, company_name: str, company_website: str = "") -> dict:
        if not company_name:
            return {"summary": "Company name not found — research skipped."}

        # Run multiple targeted searches
        queries = [
            f"{company_name} company overview mission products",
            f"{company_name} engineering culture tech stack",
            f"{company_name} recent news 2025 2026",
        ]
        if company_website:
            queries.append(f"site:{company_website} about")

        all_results = []
        for query in queries:
            results = self._search(query)
            all_results.extend(results)

        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for r in all_results:
            url = r.get("url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique_results.append(r)

        if self.verbose:
            print(f"   Found {len(unique_results)} unique sources")

        search_text = self._format_results(unique_results[:10])

        raw_response = self.chain.invoke({
            "company_name": company_name,
            "search_results": search_text,
        })

        company_brief = self._parse_json(raw_response)
        return company_brief
