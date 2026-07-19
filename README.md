# Growth Intel Agent

Two previously-independent projects, bridged together:

- **[`content-transform-agent`](https://github.com/paulogabe1/content-transform-agent)** (git submodule) — turns text (pasted, a file, or a YouTube URL) into a blog draft + social posts. Runs standalone.
- **`research-agent/`** — searches the web for developments on a topic, produces one structured finding, saves it to Supabase. Runs standalone.
- **`bridge.py`** — runs research-agent, reads the finding back from Supabase, feeds it into content-transform-agent.

## Setup

### 1. Clone with submodules

```bash
git clone --recurse-submodules https://github.com/paulogabe1/growth-intel-agent.git
cd growth-intel-agent
```

Already cloned without `--recurse-submodules`? Run `git submodule update --init --recursive`.

### 2. Check your Python version

CrewAI requires a specific version range and fails silently outside it — it installs a stale, broken version instead of erroring. Check the current requirement and your own version before creating a venv:

**bash**
```bash
curl -s https://pypi.org/pypi/crewai/json | python3 -c "import json,sys; print(json.load(sys.stdin)['info']['requires_python'])"
python3 --version
```

**PowerShell**
```powershell
(Invoke-RestMethod https://pypi.org/pypi/crewai/json).info.requires_python
python --version
```

### 3. If your Python isn't in range

Two options:

1. **Install a matching version directly** (e.g. 3.12) from [python.org](https://www.python.org/downloads/), then point the venv at it explicitly in step 4.
OR
2. **Use [uv](https://astral.sh/uv/)** to install an isolated Python version without touching your system install:

    **bash**
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    uv python install 3.12
    ```

    **PowerShell**
    ```powershell
    irm https://astral.sh/uv/install.ps1 | iex
    uv python install 3.12
    ```

### 4. Create the venv and install dependencies

Pick whichever path you took in step 3.

**Standard venv (system Python, or a version installed directly)**

bash:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r research-agent/requirements.txt -r content-transform-agent/requirements.txt
```

PowerShell (use `py -3.12` instead of `python` if you installed a second version alongside your system one):
```powershell
py -3.12 -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt -r research-agent/requirements.txt -r content-transform-agent/requirements.txt
```

**With uv**

bash:
```bash
uv venv --python 3.12 venv
source venv/bin/activate
uv pip install -r requirements.txt -r research-agent/requirements.txt -r content-transform-agent/requirements.txt
```

PowerShell:
```powershell
uv venv --python 3.12 venv
venv\Scripts\Activate.ps1
uv pip install -r requirements.txt -r research-agent/requirements.txt -r content-transform-agent/requirements.txt
```

### 5. Configure environment variables

Same command in bash and PowerShell:
```bash
cp .env.example .env
```
Fill in `GROQ_API_KEY`, `GROQ_MODEL`, `SUPABASE_URL`, `SUPABASE_KEY`.

### 6. Set up Supabase and run

Run `research-agent/schema.sql` once in Supabase's SQL editor. Then, same command in bash and PowerShell:
```bash
python bridge.py "workload identity AI agent security"
```
Draft lands at `content-transform-agent/output.md`.

## What's next

Phase 4-5 (FastAPI layer + dashboard), Phase 6 (n8n scheduling trigger).
