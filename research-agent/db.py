"""
Persistence layer for findings. Uses Supabase when configured and
reachable, else falls back to a local findings.json file.

Run schema.sql in the Supabase project's SQL editor once before using
Supabase. It expects a `findings` table matching that schema.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import cast

from supabase import create_client, Client

from research_agents import Finding

LOCAL_DB_PATH = Path(__file__).parent / "findings.json"


def is_supabase_configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"))


def get_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be set in .env. "
            "See schema.sql for the table this expects."
        )
    return create_client(url, key)


def _row_for(finding: Finding, topic: str) -> dict:
    return {
        "topic": topic,
        "found": finding.found,
        "headline": finding.headline,
        "category": finding.category,
        "why_it_matters": finding.why_it_matters,
        "source_url": finding.source_url,
    }


def _read_local() -> list[dict]:
    if not LOCAL_DB_PATH.exists():
        return []
    return json.loads(LOCAL_DB_PATH.read_text(encoding="utf-8"))


def _save_local(row: dict) -> dict:
    records = _read_local()
    row = {
        **row,
        "id": len(records) + 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    records.append(row)
    LOCAL_DB_PATH.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return row


def save_finding(finding: Finding, topic: str) -> tuple[dict, str]:
    """Returns (row, backend), where backend is 'supabase' or 'local'."""
    row = _row_for(finding, topic)
    if is_supabase_configured():
        try:
            client = get_client()
            response = client.table("findings").insert(row).execute()
            saved = cast(dict, response.data[0]) if response.data else {}
            return saved, "supabase"
        except Exception as e:
            # Broad on purpose: any failure here should fall back, not crash.
            print(f"Supabase save failed ({e}); falling back to local findings.json")
    return _save_local(row), "local"


def get_latest_finding() -> dict | None:
    """Most recent finding with found=True, from wherever it was saved."""
    if is_supabase_configured():
        try:
            client = get_client()
            response = (
                client.table("findings")
                .select("*")
                .eq("found", True)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            return cast(dict, response.data[0]) if response.data else None
        except Exception as e:
            print(f"Supabase read failed ({e}); falling back to local findings.json")

    matches = [r for r in _read_local() if r.get("found")]
    return matches[-1] if matches else None
