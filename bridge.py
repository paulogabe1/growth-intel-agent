"""
Phase 3: bridges research_agent and content-transform-agent together.

Runs the research crew on a topic. If it surfaces a real finding
(found=True, saved to Supabase if configured or a local findings.json
otherwise), that finding gets fed straight into content-transform-agent's
existing pipeline to produce a blog draft plus social posts from it.
Turns "something worth writing about was found" into an actual draft,
automatically.

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
    python bridge.py --verbose "workload identity AI agent security"
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

BASE_DIR = Path(__file__).parent
RESEARCH_DIR = BASE_DIR / "research-agent"
CONTENT_DIR = BASE_DIR / "content-transform-agent"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run research_agent on a topic, then feed any finding into content-transform-agent."
    )
    parser.add_argument("topic", help="Topic to research")
    parser.add_argument(
        "--verbose", dest="verbose", action="store_true", default=False,
        help="Print agent/task progress from both subprocesses as they run",
    )
    parser.add_argument(
        "--quiet", dest="verbose", action="store_false",
        help="Suppress agent/task progress output from both subprocesses (default)",
    )
    return parser.parse_args()


def run_research(topic: str, verbose: bool) -> None:
    """Runs research_agent's own CLI, in its own directory."""
    flag = "--verbose" if verbose else "--quiet"
    subprocess.run(
        [sys.executable, "main.py", flag, topic],
        cwd=str(RESEARCH_DIR),
        check=True,
    )


def get_latest_finding() -> dict | None:
    """
    Reads the most recent finding straight from wherever research_agent
    saved it: Supabase if SUPABASE_URL/SUPABASE_KEY are set and reachable,
    otherwise the local findings.json file research_agent falls back to.
    Reads the data directly rather than importing research_agent's db
    module -- the two projects only ever talk through data, never
    through shared code.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if url and key:
        try:
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
        except Exception as e:
            # Broad on purpose: bad URL, bad key, and a network outage
            # all raise different exception types, and all of them
            # should fall back the same way rather than crash the run.
            print(f"Supabase read failed ({e}); falling back to local findings.json")

    local_db = RESEARCH_DIR / "findings.json"
    if not local_db.exists():
        return None
    records = json.loads(local_db.read_text(encoding="utf-8"))
    matches = [r for r in records if r.get("found")]
    return matches[-1] if matches else None


def run_content_agent(source_text: str, verbose: bool) -> None:
    """
    content-transform-agent's CLI takes a file path or YouTube URL, not raw
    text directly. So the finding gets written to a small temp file
    first, matching how it's actually meant to be called, and cleaned
    up afterward since it was only ever meant to be transient.
    """
    temp_input = CONTENT_DIR / "sample_input" / "_bridge_input.txt"
    temp_input.write_text(source_text, encoding="utf-8")

    flag = "--verbose" if verbose else "--quiet"
    try:
        subprocess.run(
            [sys.executable, "main.py", flag, str(temp_input)],
            cwd=str(CONTENT_DIR),
            check=True,
        )
    finally:
        temp_input.unlink(missing_ok=True)


def main():
    load_dotenv()

    args = parse_args()

    print(f"Researching: {args.topic}")
    run_research(args.topic, args.verbose)

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
    run_content_agent(source_text, args.verbose)
    print(f"Done. See {CONTENT_DIR / 'output.md'} for the generated draft.")


if __name__ == "__main__":
    main()
