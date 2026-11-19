import os
import sys
import sqlite3
import json
import asyncio
from datetime import datetime, timedelta, timezone

current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
db_file = os.path.join(backend_dir, "supplychainiq.db")

def sync_seed():
    print(f"Connecting to SQLite database: {db_file}")
    con = sqlite3.connect(db_file)
    cur = con.cursor()

    # Enable foreign keys
    cur.execute("PRAGMA foreign_keys = ON;")

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # 1. Ensure Carriers
    carriers = [
        (1, "Delhivery", "DLV", "Express Cargo", 4.5, 0.88, 1.8, 1, now_iso),
        (2, "BlueDart", "BD", "Air Premium", 4.8, 0.94, 0.8, 1, now_iso),
        (3, "Ecom Express", "ECOM", "Standard Surface", 4.2, 0.82, 3.2, 1, now_iso),
        (4, "XpressBees", "XB", "Economy Freight", 4.0, 0.79, 4.1, 1, now_iso),
    ]
    for cid, name, code, stype, rating, on_time, avg_delay, active, created in carriers:
        cur.execute(
            """INSERT INTO carriers (id, name, code, service_type, rating, on_time_rate, avg_delay_hours, is_active, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, code=excluded.code, service_type=excluded.service_type,
                 rating=excluded.rating, on_time_rate=excluded.on_time_rate, avg_delay_hours=excluded.avg_delay_hours""",
            (cid, name, code, stype, rating, on_time, avg_delay, active, created)
        )

    # 2. Ensure Warehouses
    warehouses = [
        (1, "Bengaluru Main Hub", "WH-BLR-1", "Bengaluru", "Karnataka", 12.9716, 77.5946, 50000, 0.5, 1, now_iso),
        (2, "Mumbai Distribution Center", "WH-BOM-1", "Mumbai", "Maharashtra", 19.0760, 72.8777, 40000, 0.5, 1, now_iso),
        (3, "Delhi NCR Fulfillment", "WH-DEL-1", "Delhi", "Delhi", 28.7041, 77.1025, 60000, 0.5, 1, now_iso),
        (4, "Kolkata Regional Center", "WH-CCU-1", "Kolkata", "West Bengal", 22.5726, 88.3639, 30000, 0.5, 1, now_iso),
        (5, "Chennai Port Hub", "WH-MAA-1", "Chennai", "Tamil Nadu", 13.0827, 80.2707, 35000, 0.5, 1, now_iso),
        (6, "Hyderabad Tech Park WH", "WH-HYD-1", "Hyderabad", "Telangana", 17.3850, 78.4867, 45000, 0.5, 1, now_iso),
        (7, "Pune Logistics Hub", "WH-PUN-1", "Pune", "Maharashtra", 18.5204, 73.8567, 25000, 0.5, 1, now_iso),
    ]
    for wid, name, code, city, state, lat, lng, cap, util, active, created in warehouses:
        cur.execute(
            """INSERT INTO warehouses (id, name, code, city, state, latitude, longitude, capacity, current_utilization, is_active, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 name=excluded.name, code=excluded.code, city=excluded.city, state=excluded.state,
                 latitude=excluded.latitude, longitude=excluded.longitude, capacity=excluded.capacity""",
            (wid, name, code, city, state, lat, lng, cap, util, active, created)
        )

    # 3. Customer
    cur.execute(
        """INSERT OR IGNORE INTO customers (id, name, email, phone, city, state, created_at)
           VALUES (1, 'Tata Electronics Supply Chain', 'enterprise@tata-electronics.com', '+91-9845012345', 'Bengaluru', 'Karnataka', ?)""",
        (now_iso,)
    )

    # 4. Realistic Indian logistics demo shipments
    shipments_data = [
        # 1. Delhi to Mumbai
        {
            "tracking_number": "SH-DEL-BOM-9102",
            "origin": "Delhi",
            "destination": "Mumbai",
            "carrier_id": 1,
            "warehouse_id": 3,
            "shipment_type": "STANDARD",
            "package_weight": 24.5,
            "package_value": 85000.0,
            "distance_km": 1420.0,
            "status": "IN_TRANSIT",
            "current_location": "Jaipur Express WH",
            "current_latitude": 26.9124,
            "current_longitude": 75.7873,
            "delay_probability": 0.28,
            "predicted_delay_hours": 1.5,
            "risk_level": "LOW",
            "expected_delivery": (now + timedelta(hours=32)).isoformat(),
            "events": [
                ("ORDER_CREATED", "Delhi NCR Fulfillment", 28.7041, 77.1025, 16, "Order manifested and vehicle loaded"),
                ("PICKED_UP", "Gurugram NH-48 Gateway", 28.4595, 77.0266, 12, "Departed Delhi NCR on NH-48 linehaul"),
                ("IN_TRANSIT", "Kotputli Checkpoint", 27.7025, 76.2008, 8, "Passed Rajasthan state border checkpost"),
                ("IN_TRANSIT", "Jaipur Express WH", 26.9124, 75.7873, 2, "Scheduled intermediate cross-dock inspection"),
            ]
        },
        # 2. Bengaluru to Kolkata (HIGH RISK / Weather Delay)
        {
            "tracking_number": "SH-BLR-CCU-8921",
            "origin": "Bengaluru",
            "destination": "Kolkata",
            "carrier_id": 2,
            "warehouse_id": 1,
            "shipment_type": "EXPRESS",
            "package_weight": 32.0,
            "package_value": 195000.0,
            "distance_km": 1870.0,
            "status": "IN_TRANSIT",
            "current_location": "Near Visakhapatnam Port Gateway",
            "current_latitude": 17.6868,
            "current_longitude": 83.2185,
            "delay_probability": 0.78,
            "predicted_delay_hours": 14.5,
            "risk_level": "HIGH",
            "expected_delivery": (now + timedelta(hours=36)).isoformat(),
            "events": [
                ("ORDER_CREATED", "Bengaluru Main Hub", 12.9716, 77.5946, 28, "Shipment order booked and manifest generated"),
                ("PICKED_UP", "Anantapur NH-44 Hub", 14.6819, 77.6006, 22, "Transit scan logged on south corridor"),
                ("DEPARTED_WAREHOUSE", "Vijayawada Transit Hub", 16.5062, 80.6480, 12, "Departed Vijayawada heading east along coastal highway"),
                ("WEATHER_DELAY", "Visakhapatnam Port Gateway", 17.6868, 83.2185, 3, "Torrential monsoon rains causing waterlogging and fleet deceleration"),
            ],
            "alert": {
                "severity": "HIGH",
                "title": "High Delay Probability (78%) - Monsoon Warning on NH-16",
                "message": "Shipment SH-BLR-CCU-8921 experiencing coastal weather delay. Projected ETA offset: +14.5 hours.",
                "factors": json.dumps({"weather": "Torrential Rainfall", "route_congestion": "High", "corridor": "NH-16"})
            }
        },
        # 3. Hyderabad to Mumbai
        {
            "tracking_number": "SH-HYD-BOM-6382",
            "origin": "Hyderabad",
            "destination": "Mumbai",
            "carrier_id": 2,
            "warehouse_id": 6,
            "shipment_type": "EXPRESS",
            "package_weight": 21.0,
            "package_value": 145000.0,
            "distance_km": 710.0,
            "status": "IN_TRANSIT",
            "current_location": "Solapur Highway Node",
            "current_latitude": 17.6599,
            "current_longitude": 75.9064,
            "delay_probability": 0.25,
            "predicted_delay_hours": 1.0,
            "risk_level": "LOW",
            "expected_delivery": (now + timedelta(hours=20)).isoformat(),
            "events": [
                ("ORDER_CREATED", "Hyderabad Tech Park WH", 17.3850, 78.4867, 14, "High-priority enterprise manifest dispatched"),
                ("PICKED_UP", "Zaheerabad Junction", 17.6815, 77.6017, 10, "Border customs and e-way bill verification completed"),
                ("IN_TRANSIT", "Solapur Highway Node", 17.6599, 75.9064, 3, "Passing Maharashtra border node on schedule"),
            ]
        },
        # 4. Chennai to Hyderabad
        {
            "tracking_number": "SH-MAA-HYD-7105",
            "origin": "Chennai",
            "destination": "Hyderabad",
            "carrier_id": 3,
            "warehouse_id": 5,
            "shipment_type": "STANDARD",
            "package_weight": 16.5,
            "package_value": 52000.0,
            "distance_km": 630.0,
            "status": "AT_WAREHOUSE",
            "current_location": "Nellore Transit Hub",
            "current_latitude": 14.4426,
            "current_longitude": 79.9865,
            "delay_probability": 0.38,
            "predicted_delay_hours": 2.5,
            "risk_level": "MEDIUM",
            "expected_delivery": (now + timedelta(hours=24)).isoformat(),
            "events": [
                ("ORDER_CREATED", "Chennai Port Hub", 13.0827, 80.2707, 12, "Port container clearance verified"),
                ("PICKED_UP", "Gummidipoondi Industrial Node", 13.4072, 80.1265, 8, "Dispatched on coastal route NH-16"),
                ("ARRIVED_WAREHOUSE", "Nellore Transit Hub", 14.4426, 79.9865, 2, "Consolidation and sorting for Telangana distribution"),
            ]
        },
        # 5. Mumbai to Pune
        {
            "tracking_number": "SH-BOM-PUN-2201",
            "origin": "Mumbai",
            "destination": "Pune",
            "carrier_id": 4,
            "warehouse_id": 2,
            "shipment_type": "EXPRESS",
            "package_weight": 18.0,
            "package_value": 68000.0,
            "distance_km": 150.0,
            "status": "IN_TRANSIT",
            "current_location": "Khopoli Expressway Gate",
            "current_latitude": 18.7872,
            "current_longitude": 73.3434,
            "delay_probability": 0.20,
            "predicted_delay_hours": 0.5,
            "risk_level": "LOW",
            "expected_delivery": (now + timedelta(hours=6)).isoformat(),
            "events": [
                ("ORDER_CREATED", "Mumbai Distribution Center", 19.0760, 72.8777, 4, "Express shipment manifest created"),
                ("PICKED_UP", "Navi Mumbai Hub", 19.0330, 73.0297, 3, "Vehicle departed Navi Mumbai hub towards expressway"),
                ("IN_TRANSIT", "Khopoli Expressway Gate", 18.7872, 73.3434, 1, "Cruising on Mumbai-Pune Yashwantrao Chavan Expressway"),
            ]
        },
        # Additional: Pune to Ahmedabad (DELAYED - Critical Anomaly)
        {
            "tracking_number": "SH-PUN-AMD-5521",
            "origin": "Pune",
            "destination": "Ahmedabad",
            "carrier_id": 4,
            "warehouse_id": 7,
            "shipment_type": "FRAGILE",
            "package_weight": 14.0,
            "package_value": 72000.0,
            "distance_km": 660.0,
            "status": "DELAYED",
            "current_location": "Thane Ghodbunder Node",
            "current_latitude": 19.2608,
            "current_longitude": 72.9772,
            "delay_probability": 0.91,
            "predicted_delay_hours": 18.0,
            "risk_level": "HIGH",
            "expected_delivery": (now - timedelta(hours=4)).isoformat(),
            "events": [
                ("ORDER_CREATED", "Pune Logistics Hub", 18.5204, 73.8567, 30, "Fragile seal and electronic goods inspection logged"),
                ("PICKED_UP", "Lonavala Expressway", 18.7557, 73.4091, 24, "Special secure escort transit"),
                ("TRAFFIC_DELAY", "Thane Ghodbunder Node", 19.2608, 72.9772, 8, "Heavy vehicle breakdown resulting in major 12km bottleneck"),
            ],
            "alert": {
                "severity": "CRITICAL",
                "title": "Severe Bottleneck Delay - Thane Bypass",
                "message": "Shipment SH-PUN-AMD-5521 halted due to freight trailer breakdown. Delay projected: +18 hours.",
                "factors": json.dumps({"traffic": "Critical Gridlock", "incident": "Vehicle Breakdown", "route": "NH-48"})
            }
        },
        # Additional: Delhi to Bengaluru (OUT_FOR_DELIVERY)
        {
            "tracking_number": "SH-DEL-BLR-3098",
            "origin": "Delhi",
            "destination": "Bengaluru",
            "carrier_id": 2,
            "warehouse_id": 3,
            "shipment_type": "EXPRESS",
            "package_weight": 42.0,
            "package_value": 310000.0,
            "distance_km": 2150.0,
            "status": "OUT_FOR_DELIVERY",
            "current_location": "Electronic City Bengaluru Hub",
            "current_latitude": 12.8399,
            "current_longitude": 77.6770,
            "delay_probability": 0.08,
            "predicted_delay_hours": 0.0,
            "risk_level": "LOW",
            "expected_delivery": (now + timedelta(hours=4)).isoformat(),
            "events": [
                ("ORDER_CREATED", "Delhi NCR Fulfillment", 28.7041, 77.1025, 48, "Order dispatched via express priority corridor"),
                ("DEPARTED_WAREHOUSE", "Nagpur Central Hub", 21.1458, 79.0882, 22, "Midway hub transit scan complete"),
                ("ARRIVED_WAREHOUSE", "Bengaluru Main Hub", 12.9716, 77.5946, 5, "Arrived at destination destination hub"),
                ("OUT_FOR_DELIVERY", "Electronic City Delivery Van", 12.8399, 77.6770, 1, "Out for final delivery to enterprise recipient"),
            ]
        }
    ]

    # Clean existing shipments, events, and alerts to reset state cleanly
    cur.execute("DELETE FROM alerts;")
    cur.execute("DELETE FROM shipment_events;")
    cur.execute("DELETE FROM shipments;")

    created_at_val = (now - timedelta(hours=36)).isoformat()

    for s in shipments_data:
        cur.execute(
            """INSERT INTO shipments (
                tracking_number, customer_id, carrier_id, warehouse_id,
                origin, destination, shipment_type, package_weight, package_value,
                distance_km, expected_delivery, status, current_location,
                current_latitude, current_longitude, delay_probability,
                predicted_delay_hours, risk_level, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                s["tracking_number"], 1, s["carrier_id"], s["warehouse_id"],
                s["origin"], s["destination"], s["shipment_type"],
                s["package_weight"], s["package_value"], s["distance_km"],
                s["expected_delivery"], s["status"], s["current_location"],
                s["current_latitude"], s["current_longitude"],
                s["delay_probability"], s["predicted_delay_hours"],
                s["risk_level"], created_at_val, now_iso
            )
        )
        shipment_id = cur.lastrowid

        for ev_type, ev_loc, ev_lat, ev_lng, hrs_ago, ev_desc in s["events"]:
            ev_time = (now - timedelta(hours=hrs_ago)).isoformat()
            cur.execute(
                """INSERT INTO shipment_events (
                    shipment_id, event_type, location, latitude, longitude,
                    timestamp, description, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (shipment_id, ev_type, ev_loc, ev_lat, ev_lng, ev_time, ev_desc, "simulated_telematics")
            )

        if "alert" in s:
            al = s["alert"]
            al_time = (now - timedelta(hours=4)).isoformat()
            cur.execute(
                """INSERT INTO alerts (
                    shipment_id, severity, title, message, delay_probability,
                    predicted_delay_hours, contributing_factors, is_read, is_resolved, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    shipment_id, al["severity"], al["title"], al["message"],
                    s["delay_probability"], s["predicted_delay_hours"],
                    al["factors"], 0, 0, al_time
                )
            )

    con.commit()
    print(f"Successfully seeded {len(shipments_data)} demo shipments with realistic Indian logistics routes!")
    con.close()

async def seed_all():
    """Async wrapper used by simulator.reset() or backend lifespan."""
    return await asyncio.to_thread(sync_seed)

if __name__ == "__main__":
    sync_seed()
