"""
WebSocket Router
================
Real-time execution tracing for the BrandPulse dashboard.
"""

import logging
import asyncio
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ws", tags=["WebSockets"])

# Simple in-memory connection manager for WebSockets
class ConnectionManager:
    def __init__(self):
        # Maps company_id to a set of active WebSockets
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, company_id: int):
        await websocket.accept()
        if company_id not in self.active_connections:
            self.active_connections[company_id] = set()
        self.active_connections[company_id].add(websocket)
        logger.info(f"Client connected to WS for company {company_id}. Total: {len(self.active_connections[company_id])}")

    def disconnect(self, websocket: WebSocket, company_id: int):
        if company_id in self.active_connections:
            self.active_connections[company_id].discard(websocket)
            logger.info(f"Client disconnected from WS for company {company_id}. Total: {len(self.active_connections[company_id])}")
            if not self.active_connections[company_id]:
                del self.active_connections[company_id]

    async def broadcast(self, company_id: int, message: dict):
        if company_id in self.active_connections:
            # Create a copy to iterate safely
            connections = list(self.active_connections[company_id])
            for connection in connections:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Error sending message to websocket: {e}")
                    self.disconnect(connection, company_id)

manager = ConnectionManager()

@router.websocket("/trace/{company_id}")
async def websocket_trace_endpoint(websocket: WebSocket, company_id: int):
    """WebSocket endpoint for receiving live execution traces for a specific company."""
    await manager.connect(websocket, company_id)
    try:
        # Keep connection open and listen for pings/disconnects
        while True:
            data = await websocket.receive_text()
            # We don't expect client to send much, maybe ping/pong
            pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, company_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, company_id)
