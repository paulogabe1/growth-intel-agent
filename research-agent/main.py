"""
CLI entry point: run the research crew on a topic.

Usage:
    python main.py "workload identity AI agent security"

Writes the raw research and finding to findings.md, and saves the
structured finding to Supabase (requires schema.sql to have been run
once, and SUPABASE_URL/SUPABASE_KEY set in .env).
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

from research_agents import build_crew
from db import save_finding


def main():
    # Load the shared top-level .env first, then load this project's own .env with
    # override=True, so any key defined here wins over the shared base;
    # anything not redefined here just keeps whatever the shared .env
    # already set.
    load_dotenv(Path(__file__).parent.parent / ".env")
    load_dotenv(override=True)

    if len(sys.argv) != 2:
        print('Usage: python main.py "<topic to research>"')
        sys.exit(1)

    topic = sys.argv[1]

    crew = build_crew(topic)
    result = crew.kickoff()

    # Same thing that came up with content-transform-agent: str(result)
    # only returns the LAST task's output. tasks_output is what's
    # needed to get both the raw research and the synthesized finding.
    research_output, synthesize_output = result.tasks_output

    sections = [
        f"## Raw Research\n\n{research_output.raw}",
        f"## Finding\n\n{synthesize_output.raw}",
    ]
    output_path = Path("findings.md")
    output_path.write_text("\n\n---\n\n".join(sections), encoding="utf-8")
    print(f"Wrote {output_path}")

    # synthesize_output.pydantic is populated because the task was
    # built with output_pydantic=Finding. It's the same result as
    # .raw, just already validated and structured instead of needing
    # to be parsed back apart.
    finding = synthesize_output.pydantic
    if finding is None:
        print("Warning: no structured finding was returned. Skipping Supabase save.")
        return

    if not finding.found:
        print(f"No specific finding this run: {finding.why_it_matters}")
        return

    try:
        saved_row = save_finding(finding, topic)
        print(f"Saved to Supabase: {saved_row.get('id', '(no id returned)')}")
    except ValueError as e:
        print(f"Skipped Supabase save: {e}")


if __name__ == "__main__":
    main()
