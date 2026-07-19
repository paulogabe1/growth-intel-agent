"""
Phase 1 of the research/competitive-intel agent. One agent searches
the web for recent developments on a topic or company, and a second
agent turns those raw results into a structured finding with a
category and a single line "why this matters" note.

This deliberately uses the same structure as the content-transform-agent
(build_llm / build_agents / build_tasks / build_crew), carrying over
the same modifs: the cache_breakpoint patch, timeout and retries 
on the LLM, UTF-8 everywhere. This will eventually bridge
into content-transform-agent (a flagged finding becomes the
source_text for that pipeline), but for now it's self-contained and
independently testable.
"""
import os
from typing import Literal

from pydantic import BaseModel
from crewai import Agent, Task, Crew, Process, LLM

# Same known CrewAI bug as content-transform-agent (issue #5886).
# See that project's agents.py for the full explanation. Safe to
# delete once https://github.com/crewAIInc/crewAI/issues/5886 is
# fixed upstream.
import crewai.llms.cache as _crewai_cache

_crewai_cache.mark_cache_breakpoint = lambda msg: msg

from search_tool import DuckDuckGoSearchTool


class Finding(BaseModel):
    """
    Structured output for the synthesize task, so a finding can go
    straight into a database (Supabase) row instead of getting converted from
    free-form text later. The `found` field exists specifically
    to force the model to declare if it found nothing worth reporting.
    Without it, the model would be forced to invent a
    finding even when the research came back empty or too generic,
    since every field is technically required.
    """

    found: bool
    headline: str
    category: Literal["competitor move", "industry trend", "content angle", "none"]
    why_it_matters: str
    source_url: str


def build_llm() -> LLM:
    model = os.getenv("GROQ_MODEL", "groq/llama-3.3-70b-versatile")
    return LLM(model=model, temperature=0.4, timeout=60, max_retries=5)


def build_agents(llm: LLM):
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
        verbose=True,
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
        verbose=True,
    )

    return researcher, analyst


def build_tasks(researcher: Agent, analyst: Agent, topic: str):
    """
    Defining the research tasks
    'Do not invent results if seatch comes back empty' because
    the agent could produce a plausible answer even when the tool
    returned nothing useful. Better to specify this upfront than debug
    confidently wrong outputs later.
    """
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


def build_crew(topic: str) -> Crew:
    llm = build_llm()
    researcher, analyst = build_agents(llm)
    tasks = build_tasks(researcher, analyst, topic)
    return Crew(
        agents=[researcher, analyst],
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )
