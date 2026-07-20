"""
CLI entry point: run the research crew on a topic.

Usage:
    python main.py "workload identity AI agent security"
    python main.py --verbose "workload identity AI agent security"

Writes raw_research.md, and saves the structured finding to Supabase
(configured? run schema.sql once first) or a local findings.json.
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
    # Load the shared .env first, then this project's own on top
    # (override=True), so local values win and everything else inherits.
    load_dotenv(Path(__file__).parent.parent / ".env")
    load_dotenv(override=True)

    args = parse_args()

    crew = build_crew(args.topic, verbose=args.verbose)
    result = crew.kickoff()

    # str(result) only gives the last task's output -- tasks_output has both.
    research_output, synthesize_output = result.tasks_output

    sections = [
        f"## Raw Research\n\n{research_output.raw}",
        f"## Finding\n\n{synthesize_output.raw}",
    ]
    output_path = Path("raw_research.md")
    output_path.write_text("\n\n---\n\n".join(sections), encoding="utf-8")
    print(f"Wrote {output_path}")

    # output_pydantic=Finding means .pydantic is already validated and
    # structured -- same data as .raw, no re-parsing needed.
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
