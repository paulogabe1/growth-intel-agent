"""
Persistence layer for findings. Uses Supabase instead of a local file
so results accumulate across multiple runs instead of one run's
output overwriting the last one.

Run schema.sql in the Supabase project's SQL editor once before using
this. It expects a `findings` table matching that schema.
"""
import os

from supabase import create_client, Client

from research_agents import Finding


def get_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be set in .env. "
            "See schema.sql for the table this expects."
        )
    return create_client(url, key)


def save_finding(finding: Finding, topic: str) -> dict:
    client = get_client()
    row = {
        "topic": topic,
        "found": finding.found,
        "headline": finding.headline,
        "category": finding.category,
        "why_it_matters": finding.why_it_matters,
        "source_url": finding.source_url,
    }
    response = client.table("findings").insert(row).execute()
    return response.data[0] if response.data else {}
