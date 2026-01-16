# pos_monitor/app/websocket.py
"""WebSocket handler for real-time updates"""
import asyncio
import json
import logging
import time
from fastapi import WebSocket, WebSocketDisconnect
from .database import get_cash_balance, get_buffer_status
from .alerts import check_alerts, get_kkt_status
from .config import WEBSOCKET_UPDATE_INTERVAL

logger = logging.getLogger(__name__)


async def websocket_handler(websocket: WebSocket):
    """
    WebSocket endpoint for real-time POS status updates

    Sends status updates every WEBSOCKET_UPDATE_INTERVAL seconds
    Only sends when status changes (to reduce bandwidth)

    Args:
        websocket: WebSocket connection
    """
    await websocket.accept()
    logger.info("WebSocket client connected")

    last_status = None
    consecutive_errors = 0
    max_errors = 5

    try:
        while True:
            try:
                # Fetch current status
                cash, card = get_cash_balance()
                buffer = get_buffer_status()
                alerts = check_alerts()
                kkt_status = get_kkt_status()

                current_status = {
                    "cash_balance": cash,
                    "card_balance": card,
                    "buffer": buffer,
                    "alerts": [alert.dict() for alert in alerts],
                    "kkt_status": kkt_status,
                    "timestamp": int(time.time())
                }

                # Send only if status changed (or first send)
                if current_status != last_status:
                    await websocket.send_text(json.dumps(current_status))
                    last_status = current_status
                    consecutive_errors = 0  # Reset error counter on success
                    logger.debug(f"Sent status update: {len(alerts)} alerts")

                # Wait for next update interval
                await asyncio.sleep(WEBSOCKET_UPDATE_INTERVAL)

            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Error fetching status data: {e}")

                if consecutive_errors >= max_errors:
                    logger.error(f"Too many consecutive errors ({max_errors}), closing WebSocket")
                    break

                await asyncio.sleep(WEBSOCKET_UPDATE_INTERVAL)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")

    except Exception as e:
        logger.error(f"WebSocket error: {e}")

    finally:
        try:
            await websocket.close()
        except:
            pass
        logger.info("WebSocket connection closed")


class ConnectionManager:
    """
    Manage multiple WebSocket connections (for future multi-client support)
    """
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """
        Broadcast message to all connected clients

        Args:
            message: JSON string to broadcast
        """
        disconnected = []

        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


# Global connection manager instance
manager = ConnectionManager()
