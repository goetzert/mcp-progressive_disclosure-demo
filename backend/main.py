import json
import os
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse, FileResponse
from starlette.routing import Route

from backend.naive_mode import run_naive_mode
from backend.progressive_mode import run_progressive_mode
from backend.config import settings


FRONTEND_DIR = Path(__file__).parent.parent / "frontend"


async def index(request: Request):
    return FileResponse(FRONTEND_DIR / "index.html")


async def run_demo(request: Request):
    body = await request.json()
    user_message = body.get("message", "")

    naive_result = await run_naive_mode(user_message)
    progressive_result = await run_progressive_mode(user_message)

    return JSONResponse({
        "naive": naive_result,
        "progressive": progressive_result,
    })


async def run_demo_stream(request: Request):
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
]


app = Starlette(routes=routes)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.backend_host,
        port=settings.backend_port,
    )
