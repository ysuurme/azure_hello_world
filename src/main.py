from __future__ import annotations

import base64
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from pydantic import BaseModel

import src.utils.m_ai_client as m_ai_client
from src.agents.workflow_dispatcher import WorkflowDispatcher
from src.utils.m_log import setup_logging

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    cm = m_ai_client.ClientManager()
    app.state.dispatcher = WorkflowDispatcher(client_manager=cm)
    yield


app = FastAPI(title="Hello Architect API", version="1.0.0", lifespan=lifespan)


class DispatchRequest(BaseModel):
    query: str
    session_state: dict[str, Any] = {}


class ArtifactsModel(BaseModel):
    svg: str | None = None
    d2: str | None = None


class DispatchResponse(BaseModel):
    response_text: str
    updated_state: dict[str, Any]
    artifacts: ArtifactsModel
    status: str


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/dispatch", response_model=DispatchResponse)
async def dispatch_endpoint(body: DispatchRequest, request: Request) -> DispatchResponse:
    dispatcher: WorkflowDispatcher = request.app.state.dispatcher
    result = dispatcher.dispatch(body.query, body.session_state)

    svg_b64: str | None = None
    raw_svg = result.artifacts.get("svg")
    if raw_svg is not None:
        svg_b64 = base64.b64encode(raw_svg).decode("utf-8") if isinstance(raw_svg, bytes) else str(raw_svg)

    return DispatchResponse(
        response_text=result.response_text,
        updated_state=result.updated_state,
        artifacts=ArtifactsModel(svg=svg_b64, d2=result.artifacts.get("d2")),
        status=result.status,
    )
