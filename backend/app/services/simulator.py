# ============================================
# SupplyChainIQ — Real-Time Shipment Tracking Simulator
# ============================================
import asyncio
import json
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy import select, update
import structlog

from app.core.database import AsyncSessionLocal
from app.core.redis import RedisCache
from app.models import Shipment, ShipmentEvent, Alert

logger = structlog.get_logger()

# Realistic Indian Logistics Waypoints
INDIAN_ROUTES: Dict[str, List[Dict[str, Any]]] = {
    "Bengaluru->Kolkata": [
        {"name": "Bengaluru Main Hub", "lat": 12.9716, "lng": 77.5946},
        {"name": "Anantapur NH-44 Hub", "lat": 14.6819, "lng": 77.6006},
        {"name": "Kurnool Gateway Checkpoint", "lat": 15.8281, "lng": 78.0373},
        {"name": "Hyderabad Ring Road Interchange", "lat": 17.3850, "lng": 78.4867},
        {"name": "Suryapet NH-65 Corridor", "lat": 17.1439, "lng": 79.6239},
        {"name": "Vijayawada Transit Hub", "lat": 16.5062, "lng": 80.6480},
        {"name": "Rajahmundry Godavari Node", "lat": 17.0005, "lng": 81.8040},
        {"name": "Visakhapatnam Port Gateway", "lat": 17.6868, "lng": 83.2185},
        {"name": "Bhubaneswar Regional WH", "lat": 20.2961, "lng": 85.8245},
        {"name": "Cuttack Transit Depot", "lat": 20.4625, "lng": 85.8828},
        {"name": "Balasore NH-16 Sector", "lat": 21.4934, "lng": 86.9135},
        {"name": "Kharagpur Freight Hub", "lat": 22.3460, "lng": 87.2320},
        {"name": "Kolkata Regional Center", "lat": 22.5726, "lng": 88.3639},
    ],
    "Mumbai->Delhi": [
        {"name": "Mumbai Distribution Center", "lat": 19.0760, "lng": 72.8777},
        {"name": "Bhiwandi Logistics Park", "lat": 19.2967, "lng": 73.0631},
        {"name": "Vapi Gujarat Border", "lat": 20.3893, "lng": 72.9106},
        {"name": "Surat Ring Road Hub", "lat": 21.1702, "lng": 72.8311},
        {"name": "Bharuch Narmada Bridge", "lat": 21.7051, "lng": 72.9959},
        {"name": "Vadodara Transit Facility", "lat": 22.3072, "lng": 73.1812},
        {"name": "Ahmedabad Express Hub", "lat": 23.0225, "lng": 72.5714},
        {"name": "Udaipur Toll Gateway", "lat": 24.5854, "lng": 73.7125},
        {"name": "Ajmer Bypass", "lat": 26.4499, "lng": 74.6399},
        {"name": "Jaipur Express WH", "lat": 26.9124, "lng": 75.7873},
        {"name": "Kotputli Checkpoint", "lat": 27.7025, "lng": 76.2008},
        {"name": "Gurugram NH-48 Gateway", "lat": 28.4595, "lng": 77.0266},
        {"name": "Delhi NCR Fulfillment", "lat": 28.7041, "lng": 77.1025},
    ],
    "Chennai->Hyderabad": [
        {"name": "Chennai Port Hub", "lat": 13.0827, "lng": 80.2707},
        {"name": "Gummidipoondi Industrial Node", "lat": 13.4072, "lng": 80.1265},
        {"name": "Nellore Transit Hub", "lat": 14.4426, "lng": 79.9865},
        {"name": "Ongole Bypass Junction", "lat": 15.5057, "lng": 80.0499},
        {"name": "Guntur Junction WH", "lat": 16.3067, "lng": 80.4365},
        {"name": "Narketpally Toll Way", "lat": 17.1950, "lng": 79.1970},
        {"name": "Hyderabad Tech Park WH", "lat": 17.3850, "lng": 78.4867},
    ],
    "Pune->Ahmedabad": [
        {"name": "Pune Logistics Hub", "lat": 18.5204, "lng": 73.8567},
        {"name": "Lonavala Expressway", "lat": 18.7557, "lng": 73.4091},
        {"name": "Navi Mumbai Hub", "lat": 19.0330, "lng": 73.0297},
        {"name": "Thane Ghodbunder Node", "lat": 19.2608, "lng": 72.9772},
        {"name": "Manor Checkpost", "lat": 19.7431, "lng": 72.9167},
        {"name": "Vapi Industrial Facility", "lat": 20.3893, "lng": 72.9106},
        {"name": "Surat Bypass Depot", "lat": 21.1702, "lng": 72.8311},
        {"name": "Vadodara Transit Node", "lat": 22.3072, "lng": 73.1812},
        {"name": "Ahmedabad Express Hub", "lat": 23.0225, "lng": 72.5714},
    ],
    "Delhi->Bengaluru": [
        {"name": "Delhi NCR Fulfillment", "lat": 28.7041, "lng": 77.1025},
        {"name": "Agra Express Highway", "lat": 27.1767, "lng": 78.0081},
        {"name": "Gwalior Transit Junction", "lat": 26.2183, "lng": 78.1828},
        {"name": "Jhansi Industrial Hub", "lat": 25.4484, "lng": 78.5685},
        {"name": "Nagpur Central Hub", "lat": 21.1458, "lng": 79.0882},
        {"name": "Adilabad Gateway", "lat": 19.6641, "lng": 78.5320},
        {"name": "Hyderabad Ring Road", "lat": 17.3850, "lng": 78.4867},
        {"name": "Kurnool Gateway", "lat": 15.8281, "lng": 78.0373},
        {"name": "Anantapur NH-44", "lat": 14.6819, "lng": 77.6006},
        {"name": "Bengaluru Main Hub", "lat": 12.9716, "lng": 77.5946},
    ],
    "Kolkata->Guwahati": [
        {"name": "Kolkata Regional Center", "lat": 22.5726, "lng": 88.3639},
        {"name": "Malda Transit Hub", "lat": 25.0108, "lng": 88.1411},
        {"name": "Siliguri Corridor WH", "lat": 26.7271, "lng": 88.3953},
        {"name": "Cooch Behar Sector", "lat": 26.3239, "lng": 89.4510},
        {"name": "Bongaigaon Junction", "lat": 26.5019, "lng": 90.5579},
        {"name": "Guwahati Logistics Hub", "lat": 26.1445, "lng": 91.7362},
    ],
    "Delhi->Mumbai": [
        {"name": "Delhi NCR Fulfillment", "lat": 28.7041, "lng": 77.1025},
        {"name": "Gurugram NH-48 Gateway", "lat": 28.4595, "lng": 77.0266},
        {"name": "Kotputli Checkpoint", "lat": 27.7025, "lng": 76.2008},
        {"name": "Jaipur Express WH", "lat": 26.9124, "lng": 75.7873},
        {"name": "Ajmer Bypass", "lat": 26.4499, "lng": 74.6399},
        {"name": "Udaipur Toll Gateway", "lat": 24.5854, "lng": 73.7125},
        {"name": "Ahmedabad Express Hub", "lat": 23.0225, "lng": 72.5714},
        {"name": "Vadodara Transit Facility", "lat": 22.3072, "lng": 73.1812},
        {"name": "Surat Ring Road Hub", "lat": 21.1702, "lng": 72.8311},
        {"name": "Vapi Gujarat Border", "lat": 20.3893, "lng": 72.9106},
        {"name": "Bhiwandi Logistics Park", "lat": 19.2967, "lng": 73.0631},
        {"name": "Mumbai Distribution Center", "lat": 19.0760, "lng": 72.8777},
    ],
    "Hyderabad->Mumbai": [
        {"name": "Hyderabad Tech Park WH", "lat": 17.3850, "lng": 78.4867},
        {"name": "Zaheerabad Junction", "lat": 17.6815, "lng": 77.6017},
        {"name": "Solapur Highway Node", "lat": 17.6599, "lng": 75.9064},
        {"name": "Pune Logistics Hub", "lat": 18.5204, "lng": 73.8567},
        {"name": "Lonavala Expressway", "lat": 18.7557, "lng": 73.4091},
        {"name": "Mumbai Distribution Center", "lat": 19.0760, "lng": 72.8777},
    ],
    "Mumbai->Pune": [
        {"name": "Mumbai Distribution Center", "lat": 19.0760, "lng": 72.8777},
        {"name": "Navi Mumbai Hub", "lat": 19.0330, "lng": 73.0297},
        {"name": "Panvel Junction", "lat": 18.9894, "lng": 73.1175},
        {"name": "Khopoli Expressway Gate", "lat": 18.7872, "lng": 73.3434},
        {"name": "Lonavala Expressway", "lat": 18.7557, "lng": 73.4091},
        {"name": "Talegaon Toll Plaza", "lat": 18.7265, "lng": 73.6753},
        {"name": "Pune Logistics Hub", "lat": 18.5204, "lng": 73.8567},
    ],
}


class TrackingSimulator:
    def __init__(self):
        self.is_running: bool = False
        self.speed: int = 1  # 1x, 2x, 5x
        self.tick_count: int = 0
        self.listeners = []
        self._task: Optional[asyncio.Task] = None

    def get_route_key(self, origin: str, destination: str) -> Optional[str]:
        direct = f"{origin}->{destination}"
        if direct in INDIAN_ROUTES:
            return direct
        reverse = f"{destination}->{origin}"
        if reverse in INDIAN_ROUTES:
            return reverse
        return None

    def get_route_waypoints(self, origin: str, destination: str) -> List[Dict[str, Any]]:
        direct = f"{origin}->{destination}"
        if direct in INDIAN_ROUTES:
            return INDIAN_ROUTES[direct]
        reverse = f"{destination}->{origin}"
        if reverse in INDIAN_ROUTES:
            # Reverse order of waypoints
            return list(reversed(INDIAN_ROUTES[reverse]))
        # Fallback to straight 2 points
        return [
            {"name": f"{origin} Hub", "lat": 19.0760, "lng": 72.8777},
            {"name": f"{destination} Hub", "lat": 28.7041, "lng": 77.1025},
        ]

    async def step(self) -> Dict[str, Any]:
        """Perform one simulation tick: advance active shipments by one event, persist to DB, and broadcast."""
        self.tick_count += 1
        now = datetime.now(timezone.utc)
        updated_shipments = []
        new_events = []

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Shipment).where(
                    Shipment.status.in_(["IN_TRANSIT", "AT_WAREHOUSE", "DELAYED", "OUT_FOR_DELIVERY", "CREATED", "PICKED_UP"])
                )
            )
            shipments = result.scalars().all()

            # If all shipments have reached DELIVERED, automatically restart demo cycles directly
            if not shipments:
                all_res = await db.execute(select(Shipment))
                all_shipments = all_res.scalars().all()
                for s in all_shipments:
                    waypoints = self.get_route_waypoints(s.origin, s.destination)
                    s.status = "IN_TRANSIT"
                    s.current_latitude = waypoints[1]["lat"] if len(waypoints) > 1 else waypoints[0]["lat"]
                    s.current_longitude = waypoints[1]["lng"] if len(waypoints) > 1 else waypoints[0]["lng"]
                    s.current_location = f"In transit passing {waypoints[1]['name'] if len(waypoints) > 1 else waypoints[0]['name']}"
                    s.delay_probability = 0.25
                    s.risk_level = "LOW"
                await db.commit()
                shipments = all_shipments

            for s in shipments:
                waypoints = self.get_route_waypoints(s.origin, s.destination)
                if not waypoints or len(waypoints) < 2:
                    continue

                if s.status == "CREATED":
                    s.status = "PICKED_UP"
                    s.current_latitude = waypoints[0]["lat"]
                    s.current_longitude = waypoints[0]["lng"]
                    s.current_location = f"{waypoints[0]['name']} - Loaded"
                    ev_type = "PICKED_UP"
                    ev_desc = "Shipment picked up by linehaul carrier vehicle"
                    ev = ShipmentEvent(
                        shipment_id=s.id,
                        event_type=ev_type,
                        location=s.current_location,
                        latitude=s.current_latitude,
                        longitude=s.current_longitude,
                        timestamp=now,
                        description=ev_desc,
                        source="simulated_telematics"
                    )
                    db.add(ev)
                    new_events.append({"tracking_number": s.tracking_number, "event": ev_type, "desc": ev_desc})

                elif s.status == "PICKED_UP":
                    s.status = "IN_TRANSIT"
                    target_wp = waypoints[1] if len(waypoints) > 1 else waypoints[-1]
                    s.current_latitude = target_wp["lat"]
                    s.current_longitude = target_wp["lng"]
                    s.current_location = f"In transit towards {waypoints[2]['name'] if len(waypoints) > 2 else waypoints[-1]['name']}"
                    ev_type = "IN_TRANSIT"
                    ev_desc = f"Departed origin terminal heading towards {target_wp['name']}"
                    ev = ShipmentEvent(
                        shipment_id=s.id,
                        event_type=ev_type,
                        location=s.current_location,
                        latitude=s.current_latitude,
                        longitude=s.current_longitude,
                        timestamp=now,
                        description=ev_desc,
                        source="simulated_telematics"
                    )
                    db.add(ev)
                    new_events.append({"tracking_number": s.tracking_number, "event": ev_type, "desc": ev_desc})

                else:
                    cur_lat = s.current_latitude or waypoints[0]["lat"]
                    cur_lng = s.current_longitude or waypoints[0]["lng"]

                    # Find closest waypoint index
                    closest_idx = 0
                    min_dist = float("inf")
                    for idx, wp in enumerate(waypoints):
                        d = math.hypot(wp["lat"] - cur_lat, wp["lng"] - cur_lng)
                        if d < min_dist:
                            min_dist = d
                            closest_idx = idx

                    # Advance to next waypoint
                    target_idx = min(closest_idx + 1, len(waypoints) - 1)
                    target_wp = waypoints[target_idx]

                    if closest_idx >= len(waypoints) - 1:
                        # Arrived at final destination
                        s.status = "DELIVERED"
                        s.actual_delivery = now
                        s.current_latitude = target_wp["lat"]
                        s.current_longitude = target_wp["lng"]
                        s.current_location = f"Delivered at {target_wp['name']}"
                        s.delay_probability = 0.0
                        s.risk_level = "LOW"
                        ev_type = "DELIVERED"
                        ev_desc = f"Successfully delivered and verified at {target_wp['name']}"
                    elif target_idx == len(waypoints) - 1:
                        # Final delivery leg
                        s.status = "OUT_FOR_DELIVERY"
                        s.current_latitude = target_wp["lat"]
                        s.current_longitude = target_wp["lng"]
                        s.current_location = f"Out for delivery at {target_wp['name']}"
                        ev_type = "OUT_FOR_DELIVERY"
                        ev_desc = f"Out for final delivery from {target_wp['name']}"
                    elif "Hub" in target_wp["name"] or "WH" in target_wp["name"]:
                        s.status = "AT_WAREHOUSE"
                        s.current_latitude = target_wp["lat"]
                        s.current_longitude = target_wp["lng"]
                        s.current_location = f"At {target_wp['name']}"
                        ev_type = "ARRIVED_WAREHOUSE"
                        ev_desc = f"Checkpoint arrival logged at {target_wp['name']}"
                    elif s.status == "DELAYED":
                        s.current_latitude = target_wp["lat"]
                        s.current_longitude = target_wp["lng"]
                        s.current_location = f"Delayed at {target_wp['name']}"
                        ev_type = "TRAFFIC_DELAY"
                        ev_desc = f"Delayed transit scan at {target_wp['name']} — speed restricted"
                    else:
                        s.status = "IN_TRANSIT"
                        s.current_latitude = target_wp["lat"]
                        s.current_longitude = target_wp["lng"]
                        s.current_location = f"Passing {target_wp['name']}"
                        ev_type = "IN_TRANSIT"
                        ev_desc = f"Checkpoint milestone scan logged at {target_wp['name']}"

                    ev = ShipmentEvent(
                        shipment_id=s.id,
                        event_type=ev_type,
                        location=target_wp["name"],
                        latitude=s.current_latitude,
                        longitude=s.current_longitude,
                        timestamp=now,
                        description=ev_desc,
                        source="simulated_telematics"
                    )
                    db.add(ev)
                    new_events.append({"tracking_number": s.tracking_number, "event": ev_type, "desc": ev_desc})

                updated_shipments.append({
                    "id": s.id,
                    "tracking_number": s.tracking_number,
                    "status": s.status,
                    "current_location": s.current_location,
                    "lat": s.current_latitude,
                    "lng": s.current_longitude,
                    "delay_probability": s.delay_probability,
                    "risk_level": s.risk_level
                })

            await db.commit()

        # Invalidate KPI cache
        await RedisCache.delete("dashboard:kpis")

        payload = {
            "type": "TICK_UPDATE",
            "tick": self.tick_count,
            "mode": "SIMULATED_TRACKING",
            "is_running": self.is_running,
            "speed": self.speed,
            "timestamp": now.isoformat(),
            "updated_shipments": updated_shipments,
            "new_events": new_events,
        }

        # Broadcast to active WebSockets
        from app.api.tracking_ws import manager
        await manager.broadcast(payload)
        return payload

    async def inject_delay(self, tracking_number: str, reason: str = "Severe Monsoon Rainfall") -> Optional[Dict[str, Any]]:
        """Inject realistic delay anomaly on a shipment, compute risk, create alert & event, and persist to DB."""
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            res = await db.execute(select(Shipment).where(Shipment.tracking_number == tracking_number))
            s = res.scalar_one_or_none()
            if not s:
                return None

            reason_lower = reason.lower()
            if "rain" in reason_lower or "flood" in reason_lower or "weather" in reason_lower:
                event_type = "WEATHER_DELAY"
                severity = "HIGH"
                new_status = "DELAYED"
                delay_prob = 0.89
                delay_hours = 14.5
                title = "Severe Weather Alert: Monsoon Rainfall & Flooding"
                message = f"Shipment {s.tracking_number} slowed by severe monsoon rainfall and flooding on {s.origin} -> {s.destination}. Projected delay: +{delay_hours} hrs."
                risk_level = "HIGH"
                factors = {"weather": "Torrential Rainfall", "road_condition": "Flooded", "speed_impact": "-60%"}
            elif "traffic" in reason_lower or "congestion" in reason_lower or "bottleneck" in reason_lower:
                event_type = "TRAFFIC_DELAY"
                severity = "HIGH"
                new_status = "DELAYED"
                delay_prob = 0.82
                delay_hours = 7.5
                title = "Traffic Congestion Alert: Major Bottleneck"
                message = f"Shipment {s.tracking_number} caught in severe highway gridlock on {s.origin} -> {s.destination}. Projected delay: +{delay_hours} hrs."
                risk_level = "HIGH"
                factors = {"traffic": "Severe Congestion", "avg_speed": "12 km/h", "incident": "Highway Bottleneck"}
            elif "breakdown" in reason_lower or "vehicle" in reason_lower or "mechanical" in reason_lower:
                event_type = "FAILED_DELIVERY"
                severity = "CRITICAL"
                new_status = "DELAYED"
                delay_prob = 0.94
                delay_hours = 18.0
                title = "Vehicle Breakdown Alert: Mechanical Failure"
                message = f"Shipment {s.tracking_number} linehaul trailer suffered engine breakdown near {s.current_location or 'highway'}. Projected delay: +{delay_hours} hrs."
                risk_level = "HIGH"
                factors = {"vehicle": "Engine Failure", "assistance": "Dispatched", "estimated_repair": "18 hrs"}
            elif "warehouse" in reason_lower or "sorting" in reason_lower or "cross-dock" in reason_lower:
                event_type = "ARRIVED_WAREHOUSE"
                severity = "MEDIUM"
                new_status = "AT_WAREHOUSE"
                delay_prob = 0.74
                delay_hours = 8.0
                title = "Warehouse Delay Alert: Cross-Dock Backlog"
                message = f"Shipment {s.tracking_number} delayed at sorting facility due to intake backlog. Processing delayed +{delay_hours} hrs."
                risk_level = "HIGH"
                factors = {"warehouse": "Capacity Bottleneck", "processing_delay": "+8 hrs", "queue": "High"}
            elif "diversion" in reason_lower or "detour" in reason_lower or "closure" in reason_lower:
                event_type = "TRAFFIC_DELAY"
                severity = "MEDIUM"
                new_status = "IN_TRANSIT"
                delay_prob = 0.68
                delay_hours = 4.5
                title = "Route Diversion Alert: Highway Detour Active"
                message = f"Shipment {s.tracking_number} re-routed via secondary arterial highway due to construction. Projected delay: +{delay_hours} hrs."
                risk_level = "MEDIUM"
                factors = {"diversion": "Highway Closure", "extra_distance": "+45 km", "transit_delay": "+4.5 hrs"}
            else:
                event_type = "TRAFFIC_DELAY"
                severity = "HIGH"
                new_status = "DELAYED"
                delay_prob = 0.85
                delay_hours = 10.0
                title = f"Delay Anomaly Alert: {reason}"
                message = f"Shipment {s.tracking_number} impacted by {reason}. Projected delay: +{delay_hours} hrs."
                risk_level = "HIGH"
                factors = {"reason": reason, "telematics": "SIMULATED_ANOMALY"}

            s.status = new_status
            s.delay_probability = delay_prob
            s.predicted_delay_hours = delay_hours
            s.risk_level = risk_level

            ev = ShipmentEvent(
                shipment_id=s.id,
                event_type=event_type,
                location=s.current_location or f"{s.origin} -> {s.destination} Corridor",
                latitude=s.current_latitude,
                longitude=s.current_longitude,
                timestamp=now,
                description=f"Anomaly Triggered: {title}. {message}",
                source="simulated_telematics"
            )
            db.add(ev)

            al = Alert(
                shipment_id=s.id,
                severity=severity,
                title=title,
                message=message,
                delay_probability=delay_prob,
                predicted_delay_hours=delay_hours,
                contributing_factors=json.dumps(factors),
                created_at=now
            )
            db.add(al)
            await db.commit()

        await RedisCache.delete("dashboard:kpis")
        from app.api.tracking_ws import manager
        await manager.broadcast({
            "type": "ALERT_TRIGGERED",
            "tracking_number": tracking_number,
            "severity": severity,
            "reason": reason,
            "status": new_status,
            "delay_probability": delay_prob,
            "predicted_delay_hours": delay_hours,
            "risk_level": risk_level,
        })
        return {
            "success": True,
            "tracking_number": tracking_number,
            "status": new_status,
            "delay_probability": delay_prob,
            "predicted_delay_hours": delay_hours,
            "risk_level": risk_level,
            "title": title,
            "reason": reason,
            "message": message,
        }

    async def refresh_and_generate(self) -> Dict[str, Any]:
        """Generate fresh shipment tracking data, advance milestones, record new events, and cycle active demo shipments."""
        import random
        now = datetime.now(timezone.utc)
        self.tick_count += 1

        updated_shipments = []
        new_events = []

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Shipment))
            shipments = result.scalars().all()

            if not shipments:
                try:
                    from scripts.seed_tracking_demo import seed_all
                except ImportError:
                    from backend.scripts.seed_tracking_demo import seed_all
                await seed_all()
                result = await db.execute(select(Shipment))
                shipments = result.scalars().all()

            for s in shipments:
                waypoints = self.get_route_waypoints(s.origin, s.destination)
                if not waypoints or len(waypoints) < 2:
                    continue

                cur_lat = s.current_latitude or waypoints[0]["lat"]
                cur_lng = s.current_longitude or waypoints[0]["lng"]

                closest_idx = 0
                min_dist = float("inf")
                for idx, wp in enumerate(waypoints):
                    d = math.hypot(wp["lat"] - cur_lat, wp["lng"] - cur_lng)
                    if d < min_dist:
                        min_dist = d
                        closest_idx = idx

                if closest_idx >= len(waypoints) - 1 or s.status == "DELIVERED":
                    suffix = random.randint(1000, 9999)
                    prefix = s.tracking_number.rsplit("-", 1)[0] if "-" in s.tracking_number else "SH-IND"
                    s.tracking_number = f"{prefix}-{suffix}"
                    s.status = "IN_TRANSIT"
                    target_wp = waypoints[1] if len(waypoints) > 1 else waypoints[0]
                    s.current_latitude = target_wp["lat"]
                    s.current_longitude = target_wp["lng"]
                    s.current_location = f"In transit passing {target_wp['name']}"
                    s.delay_probability = round(random.uniform(0.12, 0.45), 2)
                    s.risk_level = "LOW" if s.delay_probability < 0.3 else "MEDIUM"
                    s.package_weight = round(random.uniform(15.0, 55.0), 1)
                    s.package_value = round(random.uniform(35000.0, 280000.0), 2)
                    ev_type = "IN_TRANSIT"
                    ev_desc = f"Fresh telematics dispatch in transit at {target_wp['name']}"
                else:
                    target_idx = min(closest_idx + 1, len(waypoints) - 1)
                    target_wp = waypoints[target_idx]
                    s.current_latitude = target_wp["lat"]
                    s.current_longitude = target_wp["lng"]

                    if target_idx == len(waypoints) - 1:
                        s.status = "OUT_FOR_DELIVERY"
                        s.current_location = f"Out for delivery at {target_wp['name']}"
                        s.delay_probability = round(random.uniform(0.05, 0.20), 2)
                        s.risk_level = "LOW"
                        ev_type = "OUT_FOR_DELIVERY"
                        ev_desc = f"Out for final distribution from {target_wp['name']}"
                    elif "Hub" in target_wp["name"] or "WH" in target_wp["name"]:
                        s.status = "AT_WAREHOUSE"
                        s.current_location = f"Arrived at {target_wp['name']}"
                        s.delay_probability = round(random.uniform(0.15, 0.50), 2)
                        s.risk_level = "MEDIUM" if s.delay_probability >= 0.3 else "LOW"
                        ev_type = "ARRIVED_WAREHOUSE"
                        ev_desc = f"Telemetry arrival scan at {target_wp['name']}"
                    else:
                        s.status = "IN_TRANSIT"
                        s.current_location = f"Passing {target_wp['name']}"
                        s.delay_probability = round(random.uniform(0.10, 0.40), 2)
                        s.risk_level = "LOW" if s.delay_probability < 0.3 else "MEDIUM"
                        ev_type = "IN_TRANSIT"
                        ev_desc = f"Live GPS telematics milestone scan passing {target_wp['name']}"

                ev = ShipmentEvent(
                    shipment_id=s.id,
                    event_type=ev_type,
                    location=s.current_location,
                    latitude=s.current_latitude,
                    longitude=s.current_longitude,
                    timestamp=now,
                    description=ev_desc,
                    source="simulated_telematics"
                )
                db.add(ev)
                new_events.append({"tracking_number": s.tracking_number, "event": ev_type, "desc": ev_desc})

                updated_shipments.append({
                    "id": s.id,
                    "tracking_number": s.tracking_number,
                    "status": s.status,
                    "current_location": s.current_location,
                    "lat": s.current_latitude,
                    "lng": s.current_longitude,
                    "delay_probability": s.delay_probability,
                    "risk_level": s.risk_level,
                    "package_weight": s.package_weight,
                    "package_value": s.package_value,
                })

            await db.commit()

        await RedisCache.delete("dashboard:kpis")

        payload = {
            "type": "TICK_UPDATE",
            "tick": self.tick_count,
            "mode": "SIMULATED_TRACKING",
            "is_running": self.is_running,
            "speed": self.speed,
            "timestamp": now.isoformat(),
            "updated_shipments": updated_shipments,
            "new_events": new_events,
        }

        from app.api.tracking_ws import manager
        await manager.broadcast(payload)
        return {"status": "refreshed_and_generated", "count": len(updated_shipments), "payload": payload}

    async def reset(self) -> Dict[str, Any]:
        """Reset shipments back to initial seeded demo state."""
        try:
            from scripts.seed_tracking_demo import seed_all
        except ImportError:
            from backend.scripts.seed_tracking_demo import seed_all
        await seed_all()
        self.tick_count = 0
        await RedisCache.delete("dashboard:kpis")
        from app.api.tracking_ws import manager
        await manager.broadcast({"type": "RESET", "message": "Simulation reset to initial state"})
        return {"status": "reset", "tick": 0}

    async def loop(self):
        """Background loop running every 4 seconds when simulation is active."""
        while True:
            try:
                if self.is_running:
                    await self.step()
            except Exception as e:
                logger.error("simulator_loop_error", error=str(e))
            await asyncio.sleep(4.0 / max(1, self.speed))


simulator = TrackingSimulator()
