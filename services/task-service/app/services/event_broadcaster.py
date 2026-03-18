"""Event broadcasting service for WebSocket connections."""
from typing import Dict, Set
from fastapi import WebSocket
import structlog

logger = structlog.get_logger()


class EventBroadcaster:
    """Manages WebSocket connections and broadcasts events."""

    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, run_id: str, websocket: WebSocket):
        await websocket.accept()
        if run_id not in self.connections:
            self.connections[run_id] = set()
        self.connections[run_id].add(websocket)
        logger.info("websocket_connected", run_id=run_id)

    def disconnect(self, run_id: str, websocket: WebSocket):
        if run_id in self.connections:
            self.connections[run_id].discard(websocket)
            if not self.connections[run_id]:
                del self.connections[run_id]
        logger.info("websocket_disconnected", run_id=run_id)

    async def broadcast(self, run_id: str, event: dict):
        if run_id not in self.connections:
            return
        disconnected = set()
        for websocket in self.connections[run_id]:
            try:
                await websocket.send_json(event)
            except Exception as e:
                logger.error("websocket_send_failed", error=str(e))
                disconnected.add(websocket)
        for websocket in disconnected:
            self.disconnect(run_id, websocket)


broadcaster = EventBroadcaster()
