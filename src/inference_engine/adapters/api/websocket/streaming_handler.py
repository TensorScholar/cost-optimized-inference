from fastapi import APIRouter, WebSocket

router = APIRouter()


@router.websocket("/v1/stream")
async def stream(ws: WebSocket) -> None:
    await ws.accept()
    await ws.send_text("stream-start")
    await ws.close()
