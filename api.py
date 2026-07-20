"""
FastAPI wrapper around bridge.py, so n8n (or any HTTP caller) can
trigger a research + content run instead of shelling out to the CLI.

Run locally:
    uvicorn api:app --reload --port 8001
Then POST a topic to /research.
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from bridge import run_research, get_latest_finding, run_content_agent, CONTENT_DIR

load_dotenv(Path(__file__).parent / ".env")
app = FastAPI(title="Growth Intel Agent")


class ResearchRequest(BaseModel):
    topic: str


class ResearchResponse(BaseModel):
    headline: str
    why_it_matters: str
    source_url: str
    draft: str


@app.post("/research", response_model=ResearchResponse)
def research(req: ResearchRequest) -> ResearchResponse:
    run_research(req.topic, verbose=False)

    finding = get_latest_finding()
    if finding is None:
        raise HTTPException(
            status_code=404,
            detail=f"No finding was returned for topic: {req.topic}",
        )

    source_text = (
        f"{finding['headline']}\n\n"
        f"{finding['why_it_matters']}\n\n"
        f"Source: {finding['source_url']}"
    )
    run_content_agent(source_text, verbose=False)

    return ResearchResponse(
        headline=finding["headline"],
        why_it_matters=finding["why_it_matters"],
        source_url=finding["source_url"],
        draft=(CONTENT_DIR / "output.md").read_text(encoding="utf-8"),
    )


@app.get("/health")
def health():
    return {"status": "ok"}
