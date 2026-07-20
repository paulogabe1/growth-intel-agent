"""
Two-agent research crew: one searches the web for recent developments
on a topic, the other turns the results into one structured finding.

Same shape as content-transform-agent (build_llm/build_agents/
build_tasks/build_crew), and carries over the same fixes: the
cache_breakpoint patch, LLM timeout/retries, UTF-8 everywhere.
"""
import os
from typing import Literal

from pydantic import BaseModel
from crewai import Agent, Task, Crew, Process, LLM

# Same CrewAI bug as content-transform-agent (crewAIInc/crewAI#5886),
# patched here too. Safe to remove once fixed upstream.
import crewai.llms.cache as _crewai_cache

_crewai_cache.mark_cache_breakpoint = lambda msg: msg

from search_tool import DuckDuckGoSearchTool


class Finding(BaseModel):
    """
    Structured output for the synthesize task -- goes straight into a
    db row, no parsing needed. `found` exists so the model can admit
    it found nothing instead of inventing something to fill required
    fields.
    """

    found: bool
    headline: str
    category: Literal["competitor move", "industry trend", "content angle", "none"]
    why_it_matters: str
    source_url: str


def build_llm() -> LLM:
    model = os.getenv("GROQ_MODEL", "groq/llama-3.3-70b-versatile")
    return LLM(model=model, temperature=0.4, timeout=60, max_retries=5)


def build_agents(llm: LLM, verbose: bool = True):
    researcher = Agent(
        role="Market Researcher",
        goal=(
            "Find genuinely recent, specific developments on a given "
            "topic or company, not generic background information."
        ),
        backstory=(
            "Works competitive intelligence for a security/identity "
            "company. Cares about what changed recently, not textbook "
            "explanations of well-known concepts."
        ),
        tools=[DuckDuckGoSearchTool()],
        llm=llm,
        verbose=verbose,
    )

    analyst = Agent(
        role="Findings Analyst",
        goal=(
            "Turn raw search results into one structured finding: what "
            "happened, why it matters, and what category it falls "
            "into. This is not a restatement of the search results."
        ),
        backstory=(
            "Reads competitive intel the way an editor reads a wire "
            "report: what's the actual news here, and who needs to "
            "know about it."
        ),
        llm=llm,
        verbose=verbose,
    )

    return researcher, analyst


def build_tasks(researcher: Agent, analyst: Agent, topic: str):
    """Tells the agent not to invent results when search comes back
    empty -- easier to say upfront than debug a confidently wrong
    answer later."""
    research = Task(
        description=(
            f"Search for recent news, announcements, or developments "
            f"related to: {topic}\n\n"
            "Run at least two different searches with different "
            "phrasings to avoid missing something behind one specific "
            "wording. Report what you actually found, including "
            "source URLs. Do not invent results if search comes back "
            "empty."
        ),
        expected_output=(
            "A list of the search results found, each with a title, "
            "short summary, and source URL."
        ),
        agent=researcher,
    )

    synthesize = Task(
        description=(
            "Using the research results, produce exactly one finding. "
            "Pick the single most notable item. Do not summarize "
            "everything found.\n\n"
            "If the research results are empty, too generic, or don't "
            "support a real finding, set found to false and explain "
            "why in the headline and why_it_matters fields instead of "
            "inventing something specific-sounding. Do not fabricate "
            "a source_url. If there's nothing real to point to, leave "
            "it as an empty string."
        ),
        expected_output=(
            "A Finding: found (true/false), a one-sentence headline, "
            "a category, why it matters in 1-2 sentences, and the "
            "source URL."
        ),
        agent=analyst,
        context=[research],
        output_pydantic=Finding,
    )

    return [research, synthesize]


def build_crew(topic: str, verbose: bool = True) -> Crew:
    llm = build_llm()
    researcher, analyst = build_agents(llm, verbose=verbose)
    tasks = build_tasks(researcher, analyst, topic)
    return Crew(
        agents=[researcher, analyst],
        tasks=tasks,
        process=Process.sequential,
        verbose=verbose,
    )
