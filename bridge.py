"""
Phase 3: bridges research_agent and content-transform-agent together.

Runs the research crew on a topic. If it surfaces a real finding
(found=True in Supabase), that finding gets fed straight into
content-transform-agent's existing pipeline to produce a blog draft
plus social posts from it. Turns "something worth writing about was
found" into an actual draft, automatically.

This deliberately does NOT merge the two projects' internals or import
across them. content-transform-agent is included as a git submodule
(see README), not duplicated as plain copied files, so there's still
only one real source of truth for its code even though it's nested
inside this repo. Each keeps running exactly the way it did standalone
(own main.py, own dependencies, own .env). This script just calls
each one's existing CLI as a subprocess and hands data between them
via Supabase and a small temp file. That's the same shape as the n8n
workflow from earlier: call one thing, take its result, feed it to
the next thing, just in Python instead of a visual canvas.

Usage:
    python bridge.py "workload identity AI agent security"
"""
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

BASE_DIR = Path(__file__).parent
RESEARCH_DIR = BASE_DIR / "research-agent"
CONTENT_DIR = BASE_DIR / "content-transform-agent"


def run_research(topic: str) -> None:
    """Runs research_agent's own CLI, in its own directory."""
    subprocess.run(
        [sys.executable, "main.py", topic],
        cwd=str(RESEARCH_DIR),
        check=True,
    )


def get_latest_finding() -> dict | None:
    """
    Reads the most recent finding straight from Supabase. That row is
    already the structured, validated version of whatever
    research_agent just produced, so there's nothing left to re-parse.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

    client = create_client(url, key)
    response = (
        client.table("findings")
        .select("*")
        .eq("found", True)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def run_content_agent(source_text: str) -> None:
    """
    content-transform-agent's CLI takes a file path or YouTube URL, not raw
    text directly. So the finding gets written to a small temp file
    first, matching how it's actually meant to be called, and cleaned
    up afterward since it was only ever meant to be transient.
    """
    temp_input = CONTENT_DIR / "sample_input" / "_bridge_input.txt"
    temp_input.write_text(source_text, encoding="utf-8")

    try:
        subprocess.run(
            [sys.executable, "main.py", str(temp_input)],
            cwd=str(CONTENT_DIR),
            check=True,
        )
    finally:
        temp_input.unlink(missing_ok=True)


def main():
    load_dotenv()

    if len(sys.argv) != 2:
        print('Usage: python bridge.py "<topic to research>"')
        sys.exit(1)

    topic = sys.argv[1]

    print(f"Researching: {topic}")
    run_research(topic)

    finding = get_latest_finding()
    if finding is None:
        print("No finding was returned. Nothing to bridge into content.")
        return

    print(f"Finding: {finding['headline']}")

    source_text = (
        f"{finding['headline']}\n\n"
        f"{finding['why_it_matters']}\n\n"
        f"Source: {finding['source_url']}"
    )

    print("Feeding the finding into content-transform-agent...")
    run_content_agent(source_text)
    print(f"Done. See {CONTENT_DIR / 'output.md'} for the generated draft.")


if __name__ == "__main__":
    main()
