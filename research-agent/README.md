# Research Agent

Searches the web for recent developments on a topic and turns them into one structured finding, saved to Supabase so findings accumulate across runs.

Two agents: a Researcher (coverage) and an Analyst (judgment) — same split as content-transform-agent's Analyst/Writer. Search is DuckDuckGo via `ddgs` (free, no API key; unofficial, and rate-limited around 30 requests/minute from one IP). Output is a strict Pydantic schema (`Finding`) with a `found: bool` field so an empty search doesn't force the model to invent a result.

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env   # GROQ_API_KEY, SUPABASE_URL, SUPABASE_KEY
```
Run `schema.sql` once in Supabase's SQL editor, then:
```bash
python main.py "workload identity AI agent security"
```
Writes `findings.md` locally; inserts into Supabase (skipped with a message if Supabase env vars aren't set).

## What's next

Bridge into content-transform-agent is built (see `../bridge.py`). Next: a FastAPI layer/dashboard, then an n8n scheduling trigger.
