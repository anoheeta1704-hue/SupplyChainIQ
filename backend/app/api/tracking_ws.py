# ============================================
# SupplyChainIQ — Tracking WebSockets & Simulator API
# ============================================
import json
from typing import List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()
router = APIRouter(tags=["Tracking & Simulator"])


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("websocket_connected", total_clients=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("websocket_disconnected", total_clients=len(self.active_connections))

    async def broadcast(self, message: Dict[str, Any]):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.warning("websocket_send_error", error=str(e))
                self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/api/ws/tracking")
async def websocket_tracking_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    from app.services.simulator import simulator
    # Send initial status
    try:
        await websocket.send_text(json.dumps({
            "type": "INIT",
            "mode": "SIMULATED_TRACKING",
            "is_running": simulator.is_running,
            "speed": simulator.speed,
            "tick": simulator.tick_count
        }))
        while True:
            data = await websocket.receive_text()
            # Handle client commands if sent via WS
            try:
                msg = json.loads(data)
                action = msg.get("action")
                if action == "TICK":
                    await simulator.step()
                elif action == "START":
                    simulator.is_running = True
                elif action == "STOP":
                    simulator.is_running = False
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning("ws_connection_closed", error=str(e))
        manager.disconnect(websocket)


class AnomalyRequest(BaseModel):
    tracking_number: str
    reason: str = "Severe Monsoon Rainfall"


class SpeedRequest(BaseModel):
    speed: int = 1


@router.get("/api/simulator/status")
async def get_simulator_status():
    from app.services.simulator import simulator
    return {
        "mode": "SIMULATED_TRACKING",
        "notice": "Simulated Indian logistics telematics for demonstration. Not actual carrier or GPS hardware.",
        "is_running": simulator.is_running,
        "speed": simulator.speed,
        "tick_count": simulator.tick_count
    }


@router.post("/api/simulator/start")
async def start_simulator():
    from app.services.simulator import simulator
    simulator.is_running = True
    await manager.broadcast({"type": "STATUS_CHANGE", "is_running": True})
    return {"status": "started", "is_running": True}


@router.post("/api/simulator/stop")
async def stop_simulator():
    from app.services.simulator import simulator
    simulator.is_running = False
    await manager.broadcast({"type": "STATUS_CHANGE", "is_running": False})
    return {"status": "stopped", "is_running": False}


@router.post("/api/simulator/step")
async def step_simulator():
    from app.services.simulator import simulator
    payload = await simulator.step()
    return {"status": "stepped", "payload": payload}


@router.post("/api/simulator/speed")
async def set_simulator_speed(req: SpeedRequest):
    from app.services.simulator import simulator
    if req.speed in [1, 2, 5]:
        simulator.speed = req.speed
        await manager.broadcast({"type": "SPEED_CHANGE", "speed": simulator.speed})
        return {"status": "ok", "speed": simulator.speed}
    raise HTTPException(status_code=400, detail="Speed must be 1, 2, or 5")


@router.post("/api/simulator/reset")
async def reset_simulator():
    from app.services.simulator import simulator
    return await simulator.reset()


@router.post("/api/simulator/refresh")
async def refresh_simulator():
    """Generate fresh shipment tracking data, update milestones, and broadcast updates."""
    from app.services.simulator import simulator
    return await simulator.refresh_and_generate()


@router.post("/api/simulator/inject-anomaly")
async def inject_anomaly(req: AnomalyRequest):
    from app.services.simulator import simulator
    res = await simulator.inject_delay(req.tracking_number, req.reason)
    if not res:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return res


@router.get("/api/shipments/routes")
async def get_shipment_routes():
    from app.services.simulator import INDIAN_ROUTES
    return INDIAN_ROUTES
