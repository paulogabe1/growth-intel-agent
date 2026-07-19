# Growth Intel Agent (Phase 3)

Two previously-independent projects I built separately, now bridged
together:

- **[`content-transform-agent`](https://github.com/paulogabe1/content-transform-agent)**
  (included as a git submodule, see setup below): takes text (pasted,
  a file, or a YouTube URL) and turns it into a blog draft plus social
  posts. Runs standalone.
- **`research_agent/`** (in this repo): searches the web for
  developments on a topic and turns them into one structured finding,
  saved to Supabase. Runs standalone.
- **`bridge.py`** (in this repo): runs research_agent on a topic,
  reads back whatever finding it just saved to Supabase, and feeds
  that finding straight into content-transform-agent. Turns "here's
  something worth writing about" into an actual draft, automatically.

## Setup: this repo uses a git submodule

`content-transform-agent` is included here as a **git submodule**, not
copied files. A submodule is a real, separate git repo (with its own
full commit history) referenced by this one at a specific commit --
so there's still exactly one source of truth for its code, it just
lives nested inside this repo's folder instead of alongside it.

**Cloning this repo for the first time:**

```bash
git clone --recurse-submodules https://github.com/paulogabe1/growth-intel-agent.git
cd growth-intel-agent
```

**If it's already cloned without that flag** (a plain `git clone` with
no submodule flag leaves the `content-transform-agent/` folder empty,
with no warning that anything's missing):

```bash
git submodule update --init --recursive
```

**Setting this up for the first time, from scratch** (this is how the
submodule reference itself gets created and committed). `-b main`
explicitly tracks that branch, which is what makes the auto-update
below unambiguous about which branch counts as "latest":

```bash
git submodule add -b main https://github.com/paulogabe1/content-transform-agent.git content-transform-agent
git commit -m "Add content-transform-agent as a submodule"
git push
```

## Keeping the submodule current automatically

A submodule is pinned to one specific commit by design, on purpose --
that's what makes it reproducible rather than silently changing under
you. `.github/workflows/update-submodule.yml` handles the "actually
keep it current" part without needing that pin managed by hand every
time content-transform-agent changes:

- Runs once a day (06:00 UTC) automatically
- Can also be triggered on demand from the Actions tab on GitHub, any
  time, without waiting for the schedule
- Pulls whatever the latest commit on content-transform-agent's main
  branch is, and only commits and pushes an update to this repo if
  something actually changed. A day with no new commits over there
  produces no noise here

No setup needed beyond the workflow file already being in this repo --
GitHub Actions provides its own token automatically for pushing back
to the same repository, nothing to configure by hand.

**A plain manual alternative**, for updating immediately from a local
clone without touching GitHub at all:

```bash
git submodule update --remote --merge
git add content-transform-agent
git commit -m "Update content-transform-agent submodule"
git push
```

Resulting folder layout:

```
growth-intel-agent/
|-- .github/workflows/update-submodule.yml   <- the auto-update workflow
|-- bridge.py
|-- research_agent/
`-- content-transform-agent/    <- the submodule, nested here
```

## Why the bridge doesn't import either project's code directly

Each project keeps running exactly the way it did on its own: its own
`main.py`, its own `.env`, its own dependencies. `bridge.py` doesn't
reach into either one's internals. It calls each one's existing CLI
as a subprocess and hands data between them via Supabase and a small
temp file. Two real reasons for this, not just caution:

1. Both projects define their own `build_crew()` function and both
   have their own `main.py`. Importing them directly into one
   namespace means picking which one wins on every name collision.
   Treating each as its own process sidesteps that entirely.
2. It keeps content-transform-agent as a genuinely single source of
   truth even though it's nested in this repo's folder. The submodule
   only stores a reference to a specific commit in its own separate
   history, not a copy of the files, so a fix there only ever needs to
   happen in that repo, never in two places that could quietly drift
   apart.
3. It's arguably the more honest representation of what's actually
   happening: two separate agent systems, handing off data to each
   other, not one merged codebase pretending to be a single thing.
   It's the same shape as the n8n workflow from earlier: call one
   thing, take its result, feed it to the next thing.

## Running it

**Check this first, before creating a venv:** CrewAI only supports a
specific Python version range, and it changes over time as new
releases come out. Installing on an unsupported version (Python 3.14,
for example) doesn't fail loudly. It silently installs an ancient,
broken CrewAI release instead, which is a confusing thing to debug if
you don't know to look for it. Check the current requirement first:

```powershell
(Invoke-RestMethod https://pypi.org/pypi/crewai/json).info.requires_python
```

This queries PyPI directly for CrewAI's real, current constraint (as
of when this was written: `>=3.10,<3.14`), rather than trusting a
number that might already be stale by the time this is read. Check
your own version against it:

```powershell
python --version
```

If your version already falls in that range, just create the venv
normally:

```powershell
python -m venv venv
```

**If it doesn't, two ways to fix it:**

**1. Install a compatible Python version directly**, then point the
venv at it specifically rather than your system default:

```powershell
py -3.12 -m venv venv
```

**2. Or use `uv`**, which can install and manage a specific Python
version scoped to just this project, without touching your system
Python at all:

```powershell
irm https://astral.sh/uv/install.ps1 | iex
uv python install 3.12
uv venv --python 3.12 venv
```

Either way, once the venv exists, activate it and install both
projects' dependencies into it. `bridge.py` calls both as subprocesses
using the same Python interpreter it's running under, so both
requirement sets need to live in this one shared environment:

```bash
source venv/bin/activate   # or venv\Scripts\activate on Windows

pip install -r requirements.txt
pip install -r research_agent/requirements.txt
pip install -r content-transform-agent/requirements.txt
```

`.env` setup is a single shared file now, not three separate ones.
`GROQ_API_KEY`, `GROQ_MODEL`, `SUPABASE_URL`, and `SUPABASE_KEY` all
go in the top-level `.env` once, and both subfolder scripts pick them
up automatically:

```bash
cp .env.example .env
```

`research_agent/.env` and `content-transform-agent/.env` are both
optional. Only create one if a specific project needs a *different*
value than what's in the shared `.env` (see the comments in each
project's own `.env.example` for exactly how that override works).

Run `research_agent/schema.sql` once in the Supabase project's SQL
editor if that hasn't happened already (see research_agent/README.md),
then:

```bash
python bridge.py "workload identity AI agent security"
```


This runs research_agent (prints its own progress), reads the finding
back from Supabase, and runs content-transform-agent on it. The
generated draft ends up at `content-transform-agent/output.md`, same
as running that project on its own.

## What's next (not built yet)

- Phase 4-5: a FastAPI layer and dashboard tying both projects together
  properly, instead of a CLI script
- Phase 6: an n8n trigger to run this on a schedule

## Notes

- I verified the bridge mechanism itself directly by running it end
  to end: writing the temp file, invoking content-transform-agent's
  CLI via subprocess with the right working directory, cleaning up
  afterward even on failure. The one thing I couldn't test in the
  environment I built this in is a real LLM call succeeding (that
  sandbox can't reach api.groq.com, duckduckgo.com, or supabase.co).
  The actual live run is the real test, on my own machine, with real
  credentials.