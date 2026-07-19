"""
CLI entry point: run the research crew on a topic.

Usage:
    python main.py "workload identity AI agent security"
    python main.py --verbose "workload identity AI agent security"

Writes the raw research and finding to raw_research.md, and saves the
structured finding to Supabase if SUPABASE_URL/SUPABASE_KEY are set in
.env (requires schema.sql to have been run once), or to a local
findings.json file otherwise.
"""
import argparse
from pathlib import Path
from typing import cast

from dotenv import load_dotenv

from research_agents import build_crew, Finding
from db import save_finding


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the research crew on a topic.")
    parser.add_argument("topic", help="Topic to research")
    parser.add_argument(
        "--verbose", dest="verbose", action="store_true", default=False,
        help="Print agent/task progress as it runs",
    )
    parser.add_argument(
        "--quiet", dest="verbose", action="store_false",
        help="Suppress agent/task progress output (default)",
    )
    return parser.parse_args()


def main():
    # Load the shared top-level .env first, then load this project's own .env with
    # override=True, so any key defined here wins over the shared base;
    # anything not redefined here just keeps whatever the shared .env
    # already set.
    load_dotenv(Path(__file__).parent.parent / ".env")
    load_dotenv(override=True)

    args = parse_args()

    crew = build_crew(args.topic, verbose=args.verbose)
    result = crew.kickoff()

    # Same thing that came up with content-transform-agent: str(result)
    # only returns the LAST task's output. tasks_output is what's
    # needed to get both the raw research and the synthesized finding.
    research_output, synthesize_output = result.tasks_output

    sections = [
        f"## Raw Research\n\n{research_output.raw}",
        f"## Finding\n\n{synthesize_output.raw}",
    ]
    output_path = Path("raw_research.md")
    output_path.write_text("\n\n---\n\n".join(sections), encoding="utf-8")
    print(f"Wrote {output_path}")

    # synthesize_output.pydantic is populated because the task was
    # built with output_pydantic=Finding. It's the same result as
    # .raw, just already validated and structured instead of needing
    # to be parsed back apart.
    if synthesize_output.pydantic is None:
        print("Warning: no structured finding was returned. Skipping Supabase save.")
        return
    finding = cast(Finding, synthesize_output.pydantic)

    if not finding.found:
        print(f"No specific finding this run: {finding.why_it_matters}")
        return

    saved_row, backend = save_finding(finding, args.topic)
    destination = "Supabase" if backend == "supabase" else "local findings.json"
    print(f"Saved to {destination}: {saved_row.get('id', '(no id returned)')}")


if __name__ == "__main__":
    main()
