"""
Phase 3: bridges research_agent and content-transform-agent.

Runs the research crew on a topic, then feeds any real finding into
content-transform-agent to produce a blog draft and social posts.

Doesn't import either project's code -- just calls each one's CLI as
a subprocess and passes data through Supabase/findings.json and a temp
file. Keeps both fully independent, same shape as the n8n workflow:
call one thing, take the result, feed it to the next.

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
    Reads the latest finding from Supabase if reachable, else the local
    findings.json fallback -- a direct data read, not an import, same
    as everywhere else in this script.
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
            # Broad on purpose: any failure here should fall back, not crash.
            print(f"Supabase read failed ({e}); falling back to local findings.json")

    local_db = RESEARCH_DIR / "findings.json"
    if not local_db.exists():
        return None
    records = json.loads(local_db.read_text(encoding="utf-8"))
    matches = [r for r in records if r.get("found")]
    return matches[-1] if matches else None


def run_content_agent(source_text: str, verbose: bool) -> None:
    """content-transform-agent's CLI wants a file path or URL, not raw
    text, so we write the finding to a temp file first and clean it up
    after."""
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
