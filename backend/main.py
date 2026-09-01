"""Starlette web application — serves the frontend and API endpoints.

Endpoints:
    ``GET  /``               — Serves ``frontend/index.html``.
    ``POST /api/demo``       — Runs both modes, returns combined JSON.
    ``POST /api/demo/stream`` — Runs both modes, streams results via SSE.
    ``GET  /<static>``       — Serves static frontend assets.

The application is started via ``python -m backend.main`` and listens on
``BACKEND_HOST:BACKEND_PORT`` (default ``127.0.0.1:8080``).
"""

import json
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse, FileResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles

from backend.naive_mode import run_naive_mode
from backend.progressive_mode import run_progressive_mode
from backend.config import settings


#: Directory containing the frontend assets (HTML, CSS, JS).
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


async def index(request: Request):
    """Serve the main HTML page."""
    return FileResponse(FRONTEND_DIR / "index.html")


async def run_demo(request: Request):
    """Run both naive and progressive modes and return the combined result.

    Expects a JSON body with a ``message`` field.
    """
    body = await request.json()
    user_message = body.get("message", "")

    naive_result = await run_naive_mode(user_message)
    progressive_result = await run_progressive_mode(user_message)

    return JSONResponse({
        "naive": naive_result,
        "progressive": progressive_result,
    })


async def run_demo_stream(request: Request):
    """Run both modes and stream results via Server-Sent Events.

    Expects a JSON body with a ``message`` field.  Emits two SSE events
    (``naive`` and ``progressive``) followed by a final ``done`` event.
    """
    body = await request.json()
    user_message = body.get("message", "")

    async def event_stream():
        import asyncio

        naive_result = await run_naive_mode(user_message)
        yield f"data: {json.dumps({'type': 'naive', 'data': naive_result})}\n\n"

        progressive_result = await run_progressive_mode(user_message)
        yield f"data: {json.dumps({'type': 'progressive', 'data': progressive_result})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


routes = [
    Route("/", index),
    Route("/api/demo", run_demo, methods=["POST"]),
    Route("/api/demo/stream", run_demo_stream, methods=["POST"]),
    Mount("/", app=StaticFiles(directory=str(FRONTEND_DIR))),
]


app = Starlette(routes=routes)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.backend_host,
        port=settings.backend_port,
    )
