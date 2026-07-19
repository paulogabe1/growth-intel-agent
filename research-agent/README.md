# Research Agent (Phase 1-2)

Phase 1-2 of a larger system I'm building. One agent searches the web
for recent developments on a topic, a second agent turns raw results
into one structured finding (a headline, a category, and why it
matters), and I persist that to Supabase so findings accumulate
across runs instead of one run overwriting the last.

## Why two agents instead of one

Same reasoning as content-transform-agent's Analyst/Writer split.
Separating "go find things" from "decide what's actually worth
reporting" produces a sharper result than one agent trying to do both
at once. The Researcher's job is coverage. The Analyst's job is
judgment.

## Why DuckDuckGo instead of Serper/Tavily/Brave

Every "standard" CrewAI search tool needs its own account and API key.
DuckDuckGo (via the `ddgs` package) needs neither, which keeps things
consistent with the rest of this stack (Groq, Gemini,
youtube-transcript-api) and gives me one less quota to manage.
Tradeoff, stated plainly: it's an unofficial library scraping
DuckDuckGo's own site, not a sanctioned API, so it can break if
DuckDuckGo changes something, and it has no published rate limit
(community reports suggest bot detection kicks in well before 30
requests per minute from one IP). Fine for occasional research
queries, not something to run in a tight loop.

## Why a strict Pydantic schema instead of parsing text back apart

`Finding` (in `research_agents.py`) is set as the synthesize task's
`output_pydantic`, so the Analyst's result comes back already
validated and structured, ready to insert as a database row, instead
of a text blob I'd need regex or string-splitting to turn into
columns. The `found: bool` field exists specifically because a strict
schema has no natural way to express "nothing worth reporting."
Without it, the model would be forced to invent a finding even when
research came back empty, since every other field is required.

## Running it

```bash
pip install -r requirements.txt
cp .env.example .env   # add GROQ_API_KEY, SUPABASE_URL, SUPABASE_KEY
```

Then, in my Supabase project's SQL editor, run `schema.sql` once to
create the `findings` table. After that:

```bash
python main.py "workload identity AI agent security"
```

Writes `findings.md` locally, and inserts the structured finding as a
row in Supabase (skipped with a clear message if Supabase env vars
aren't set, rather than crashing).

## What's next (not built yet)

- Phase 3: bridge. A flagged finding becomes the source_text fed into
  content-transform-agent's existing pipeline, so a research result
  can turn directly into a blog draft
- Phase 4-5: a FastAPI layer and dashboard tying both projects together
- Phase 6: an n8n trigger to run this on a schedule, plus polish

## Notes

- The one thing I couldn't test in the environment I built this in:
  an actual live DuckDuckGo search or a live Supabase insert (that
  sandbox can't reach duckduckgo.com or supabase.co). Everything else
  (the tool class, the Pydantic schema, the crew assembling correctly,
  both modules importing without error) I verified directly. The real
  end-to-end test is the first run on my own machine, with real
  credentials.
- No API key is included anywhere in this repo. `.env` is gitignored.
