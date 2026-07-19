# Research Agent

Searches the web for recent developments on a topic and turns them into one structured finding, saved so findings accumulate across runs — to Supabase if configured, otherwise to a local file. No external database required to run this.

Two agents: a Researcher (coverage) and an Analyst (judgment) — same split as content-transform-agent's Analyst/Writer. Search is DuckDuckGo via `ddgs` (free, no API key; unofficial, and rate-limited around 30 requests/minute from one IP). Output is a strict Pydantic schema (`Finding`) with a `found: bool` field so an empty search doesn't force the model to invent a result.

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env   # GROQ_API_KEY required; SUPABASE_URL/SUPABASE_KEY optional
```
Using Supabase? Run `schema.sql` once in its SQL editor first. Then:
```bash
python main.py "workload identity AI agent security"
```
Runs quietly by default. Add `--verbose` (before or after the topic) to print agent/task progress as it runs.

## Outputs

- **`raw_research.md`** — overwritten every run. The Researcher's raw search results plus whatever the Analyst concluded (a real finding, or its explanation for why there wasn't one). Useful for seeing what happened on your last run.
- **`findings.json`** — appended to, but only when a run actually finds something (`found: true`). This is the accumulating record of real findings, saved locally here unless `SUPABASE_URL`/`SUPABASE_KEY` are set, in which case it goes to Supabase's `findings` table instead.

## What's next

Bridge into content-transform-agent is built (see `../bridge.py`). Next: a FastAPI layer/dashboard, then an n8n scheduling trigger.
