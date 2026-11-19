import os
import random
import uuid
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
default_output = os.path.join(root_dir, "storage", "raw")

def generate_data(num_shipments=50000, output_dir=None):
    if output_dir is None:
        output_dir = default_output
    os.makedirs(f"{output_dir}/shipments", exist_ok=True)
    os.makedirs(f"{output_dir}/tracking_events", exist_ok=True)

    cities = ["Bengaluru", "Mumbai", "Delhi", "Kolkata", "Chennai", "Hyderabad", "Pune", "Ahmedabad", "Jaipur", "Lucknow"]
    carriers = ["Delhivery", "BlueDart", "DTDC", "Ecom Express", "XpressBees", "Shadowfax"]
    warehouses = [f"WH-{c[:3].upper()}-1" for c in cities[:6]]  # First 6 have warehouses
    weather_conds = ["Clear", "Cloudy", "Rainy", "Foggy", "Storm"]
    traffic_levels = ["LOW", "MEDIUM", "HIGH"]
    shipment_types = ["STANDARD", "EXPRESS", "ECONOMY", "FRAGILE"]

    shipments = []
    events = []

    start_date = datetime.now() - timedelta(days=180)  # Last 6 months

    print(f"Generating {num_shipments} shipments...")

    for i in range(num_shipments):
        origin = random.choice(cities)
        dest = random.choice([c for c in cities if c != origin])
        distance = random.uniform(50, 2500)
        
        # Base expected time based on distance (approx 40km/h average speed)
        expected_hours = distance / 40.0
        
        # Create timestamp
        created_at = start_date + timedelta(days=random.uniform(0, 180))
        
        carrier = random.choice(carriers)
        weather = random.choices(weather_conds, weights=[0.5, 0.2, 0.15, 0.1, 0.05])[0]
        traffic = random.choices(traffic_levels, weights=[0.4, 0.4, 0.2])[0]
        
        # Simulate delay
        delay_prob = 0.1
        if distance > 1000: delay_prob += 0.1
        if weather in ["Rainy", "Storm"]: delay_prob += 0.2
        if weather == "Foggy": delay_prob += 0.15
        if traffic == "HIGH": delay_prob += 0.1
        if carrier in ["DTDC", "Shadowfax"]: delay_prob += 0.05
        
        is_delayed = random.random() < delay_prob
        
        delay_hours = random.uniform(12, 72) if is_delayed else random.uniform(-12, 0)
        actual_hours = expected_hours + delay_hours
        
        expected_delivery = created_at + timedelta(hours=expected_hours)
        actual_delivery = created_at + timedelta(hours=actual_hours) if created_at + timedelta(hours=actual_hours) < datetime.now() else None

        status = "DELIVERED" if actual_delivery else random.choice(["IN_TRANSIT", "DELAYED", "AT_WAREHOUSE"])
        
        # If not delivered, determine current status based on time passed
        if not actual_delivery:
            time_passed = (datetime.now() - created_at).total_seconds() / 3600
            if time_passed > expected_hours and is_delayed:
                status = "DELAYED"
            elif time_passed < 24:
                status = "CREATED" if time_passed < 2 else "PICKED_UP"

        tracking_num = f"SH{uuid.uuid4().hex[:8].upper()}"

        shipments.append({
            "tracking_number": tracking_num,
            "origin": origin,
            "destination": dest,
            "distance_km": round(distance, 2),
            "carrier": carrier,
            "warehouse": random.choice(warehouses) if random.random() > 0.3 else None,
            "package_weight": round(random.uniform(0.5, 50.0), 2),
            "shipment_type": random.choice(shipment_types),
            "created_at": created_at.isoformat(),
            "expected_delivery": expected_delivery.isoformat(),
            "actual_delivery": actual_delivery.isoformat() if actual_delivery else None,
            "status": status,
            "weather_condition": weather,
            "traffic_level": traffic,
            "rainfall": round(random.uniform(0, 100), 2) if weather in ["Rainy", "Storm"] else 0.0,
            "temperature": round(random.uniform(10, 45), 1)
        })

    df_shipments = pd.DataFrame(shipments)
    df_shipments.to_csv(f"{output_dir}/shipments/synthetic_shipments.csv", index=False)
    
    print(f"Generated data saved to {output_dir}")

if __name__ == "__main__":
    generate_data(10000) # generating 10k initially to be fast
