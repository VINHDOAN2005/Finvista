# -*- coding: utf-8 -*-
"""WebSocket connection manager and real-time event broadcaster."""

import asyncio
from datetime import datetime
from typing import List

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """Manages active WebSockets connections to stream real-time events to the SaaS Frontend."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(
            f"🔌 [WebSocket] New client connected. Total connections: {len(self.active_connections)}"
        )

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(
                f"🔌 [WebSocket] Client disconnected. "
                f"Remaining connections: {len(self.active_connections)}"
            )

    async def broadcast(self, message: dict):
        """Broadcast live updates to all connected web clients asynchronously."""
        if not self.active_connections:
            return

        tasks = [connection.send_json(message) for connection in self.active_connections]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    """Real-time WebSocket event broadcaster for portfolio NAV and market scanning states."""
    await manager.connect(websocket)
    try:
        await websocket.send_json({
            "event": "connected",
            "message": "Successfully connected to Finvista Quantitative WebSocket stream.",
            "timestamp": datetime.now().isoformat(),
        })
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"🔌 [WebSocket] Error: {e}")
        manager.disconnect(websocket)
