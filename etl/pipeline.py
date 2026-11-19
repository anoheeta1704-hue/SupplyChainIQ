import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

# Add the backend directory to python path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.append(os.path.join(root_dir, "backend"))

from app.core.database import active_sync_url


def init_warehouse_schema(engine, is_postgres: bool):
    """
    Drop and recreate dimensional star-schema tables.
    The ORM may have created them with a different schema (extra NOT NULL columns),
    so we always drop first to guarantee column compatibility with the ETL.
    """
    with engine.begin() as conn:
        if is_postgres:
            conn.execute(text("CREATE SCHEMA IF NOT EXISTS warehouse;"))
            p = "warehouse."
            pk_type = "SERIAL PRIMARY KEY"
        else:
            p = ""
            pk_type = "INTEGER PRIMARY KEY AUTOINCREMENT"

        # Drop in reverse dependency order (fact first, then dims)
        for tbl in [
            "fact_shipment_events", "dim_shipment", "dim_time",
            "dim_weather", "dim_route", "dim_warehouse", "dim_carrier"
        ]:
            conn.execute(text(f"DROP TABLE IF EXISTS {p}{tbl};"))

        conn.execute(text(f"""
            CREATE TABLE {p}dim_carrier (
                carrier_key {pk_type},
                carrier_name VARCHAR(100) NOT NULL UNIQUE,
                carrier_code VARCHAR(10)
            );
        """))

        conn.execute(text(f"""
            CREATE TABLE {p}dim_warehouse (
                warehouse_key {pk_type},
                warehouse_code VARCHAR(50) NOT NULL UNIQUE,
                warehouse_name VARCHAR(100)
            );
        """))

        conn.execute(text(f"""
            CREATE TABLE {p}dim_route (
                route_key {pk_type},
                origin VARCHAR(100) NOT NULL,
                destination VARCHAR(100) NOT NULL,
                distance_km FLOAT,
                UNIQUE(origin, destination)
            );
        """))

        conn.execute(text(f"""
            CREATE TABLE {p}dim_weather (
                weather_key {pk_type},
                condition VARCHAR(50) NOT NULL,
                traffic_level VARCHAR(50) NOT NULL,
                rainfall_level VARCHAR(20),
                temperature_range VARCHAR(20),
                UNIQUE(condition, traffic_level)
            );
        """))

        conn.execute(text(f"""
            CREATE TABLE {p}dim_time (
                time_key {pk_type},
                full_date TIMESTAMP NOT NULL UNIQUE,
                day INT,
                month INT,
                year INT,
                quarter INT,
                day_of_week INT,
                day_name VARCHAR(20),
                month_name VARCHAR(20),
                week_of_year INT,
                is_weekend BOOLEAN,
                season VARCHAR(20)
            );
        """))

        conn.execute(text(f"""
            CREATE TABLE {p}dim_shipment (
                shipment_key {pk_type},
                shipment_id VARCHAR(50) NOT NULL,
                tracking_number VARCHAR(50) NOT NULL UNIQUE,
                shipment_type VARCHAR(50),
                package_weight_category VARCHAR(20)
            );
        """))

        conn.execute(text(f"""
            CREATE TABLE {p}fact_shipment_events (
                fact_id {pk_type},
                shipment_key INT,
                carrier_key INT,
                route_key INT,
                warehouse_key INT,
                time_key INT,
                weather_key INT,
                distance_km FLOAT,
                delivery_duration_hours FLOAT,
                delay_hours FLOAT,
                is_delayed BOOLEAN,
                package_weight FLOAT,
                delay_probability FLOAT,
                risk_level VARCHAR(20)
            );
        """))


def _classify_weight(w):
    if pd.isna(w):
        return "Medium"
    if w < 5:
        return "Light"
    elif w < 20:
        return "Medium"
    return "Heavy"


def _classify_rainfall(r):
    if pd.isna(r) or r == 0:
        return "None"
    elif r < 10:
        return "Light"
    elif r < 40:
        return "Moderate"
    return "Heavy"


def _classify_temperature(t):
    if pd.isna(t):
        return "Mild"
    if t < 15:
        return "Cold"
    elif t < 30:
        return "Mild"
    elif t < 40:
        return "Hot"
    return "Extreme"


def _get_season(month):
    if month in [6, 7, 8, 9]:
        return "Monsoon"
    elif month in [11, 12, 1, 2]:
        return "Winter"
    elif month in [3, 4, 5]:
        return "Summer"
    return "Spring"


def run_etl_pipeline(input_csv: str = None):
    print("=" * 60)
    print("  Starting SupplyChainIQ Data Warehouse ETL Pipeline")
    print("=" * 60)

    if input_csv is None:
        input_csv = os.path.join(root_dir, "storage", "raw", "shipments", "synthetic_shipments.csv")

    # ---- 1. EXTRACT ----
    print(f"\n[EXTRACT] Reading raw data from {input_csv}...")
    if not os.path.exists(input_csv):
        print(f"  File not found. Generating fresh synthetic data...")
        gen_path = os.path.join(root_dir, "data-generator")
        sys.path.insert(0, gen_path)
        from generate_shipments import generate_data
        generate_data(10000)

    df = pd.read_csv(input_csv)
    print(f"  Extracted {len(df)} records.")

    # ---- 2. TRANSFORM ----
    print("\n[TRANSFORM] Cleaning & engineering features...")

    date_cols = ['created_at', 'expected_delivery', 'actual_delivery']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], format='ISO8601', errors='coerce')

    # Delay metrics
    df['is_delayed'] = df['status'].isin(['DELAYED', 'DELIVERED']) & (df['actual_delivery'] > df['expected_delivery'])
    df['delivery_duration_hours'] = (df['actual_delivery'] - df['created_at']).dt.total_seconds() / 3600.0
    df['delay_hours'] = (df['actual_delivery'] - df['expected_delivery']).dt.total_seconds() / 3600.0

    mask_delayed_not_delivered = (df['status'] == 'DELAYED') & df['actual_delivery'].isna()
    now = pd.Timestamp(datetime.now())
    df.loc[mask_delayed_not_delivered, 'delay_hours'] = (
        now - df.loc[mask_delayed_not_delivered, 'expected_delivery']
    ).dt.total_seconds() / 3600.0
    df.loc[mask_delayed_not_delivered, 'is_delayed'] = True

    df['delay_hours'] = df['delay_hours'].fillna(0).apply(lambda x: max(0, x))
    df['is_delayed'] = df['is_delayed'].fillna(False).astype(bool)

    # Enrichments for dimension tables
    df['package_weight_category'] = df['package_weight'].apply(_classify_weight)
    df['rainfall_level'] = df['rainfall'].apply(_classify_rainfall)
    df['temperature_range'] = df['temperature'].apply(_classify_temperature)

    # ---- 3. LOAD ----
    is_postgres = "postgres" in active_sync_url
    db_label = 'PostgreSQL' if is_postgres else 'SQLite'
    print(f"\n[LOAD] Connecting to Data Warehouse ({db_label})...")

    engine_kwargs = {}
    if not is_postgres:
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    engine = create_engine(active_sync_url, **engine_kwargs)
    init_warehouse_schema(engine, is_postgres)
    print("  Star-schema tables created.")

    schema_prefix = "warehouse." if is_postgres else ""
    schema_name = "warehouse" if is_postgres else None

    with engine.begin() as conn:
        # ---- DimCarrier ----
        print("  -> Loading DimCarrier...")
        carriers = df[['carrier']].drop_duplicates().rename(columns={'carrier': 'carrier_name'})
        carriers['carrier_code'] = carriers['carrier_name'].str[:3].str.upper()
        carriers.to_sql('dim_carrier', conn, schema=schema_name, if_exists='append', index=False)
        carrier_map = pd.read_sql(f"SELECT carrier_key, carrier_name FROM {schema_prefix}dim_carrier", conn)
        df = df.merge(carrier_map, left_on='carrier', right_on='carrier_name', how='left')
        print(f"     {len(carrier_map)} carriers loaded.")

        # ---- DimWarehouse ----
        print("  -> Loading DimWarehouse...")
        warehouses = df[['warehouse']].dropna().drop_duplicates().rename(columns={'warehouse': 'warehouse_code'})
        warehouses['warehouse_name'] = warehouses['warehouse_code']
        if not warehouses.empty:
            warehouses.to_sql('dim_warehouse', conn, schema=schema_name, if_exists='append', index=False)
        warehouse_map = pd.read_sql(f"SELECT warehouse_key, warehouse_code FROM {schema_prefix}dim_warehouse", conn)
        df = df.merge(warehouse_map, left_on='warehouse', right_on='warehouse_code', how='left')
        print(f"     {len(warehouse_map)} warehouses loaded.")

        # ---- DimRoute ----
        print("  -> Loading DimRoute...")
        routes = df[['origin', 'destination', 'distance_km']].drop_duplicates(subset=['origin', 'destination'])
        routes.to_sql('dim_route', conn, schema=schema_name, if_exists='append', index=False)
        route_map = pd.read_sql(f"SELECT route_key, origin, destination FROM {schema_prefix}dim_route", conn)
        df = df.merge(route_map, on=['origin', 'destination'], how='left')
        print(f"     {len(route_map)} routes loaded.")

        # ---- DimWeather ----
        print("  -> Loading DimWeather...")
        weather = df[['weather_condition', 'traffic_level', 'rainfall_level', 'temperature_range']].drop_duplicates(
            subset=['weather_condition', 'traffic_level']
        ).rename(columns={'weather_condition': 'condition'})
        weather.to_sql('dim_weather', conn, schema=schema_name, if_exists='append', index=False)
        weather_map = pd.read_sql(f"SELECT weather_key, condition, traffic_level FROM {schema_prefix}dim_weather", conn)
        df = df.merge(weather_map, left_on=['weather_condition', 'traffic_level'],
                      right_on=['condition', 'traffic_level'], how='left')
        print(f"     {len(weather_map)} weather combos loaded.")

        # ---- DimTime ----
        print("  -> Loading DimTime...")
        df['date_only'] = df['created_at'].dt.date
        dates_df = df[['date_only']].drop_duplicates().dropna()
        dates_df['full_date'] = pd.to_datetime(dates_df['date_only'])
        dates_df['day'] = dates_df['full_date'].dt.day
        dates_df['month'] = dates_df['full_date'].dt.month
        dates_df['year'] = dates_df['full_date'].dt.year
        dates_df['quarter'] = dates_df['full_date'].dt.quarter
        dates_df['day_of_week'] = dates_df['full_date'].dt.dayofweek
        dates_df['day_name'] = dates_df['full_date'].dt.day_name()
        dates_df['month_name'] = dates_df['full_date'].dt.month_name()
        dates_df['week_of_year'] = dates_df['full_date'].dt.isocalendar().week.astype(int)
        dates_df['is_weekend'] = dates_df['day_of_week'].isin([5, 6])
        dates_df['season'] = dates_df['month'].apply(_get_season)
        dates_df.drop(columns=['date_only']).to_sql('dim_time', conn, schema=schema_name, if_exists='append', index=False)
        time_map = pd.read_sql(f"SELECT time_key, full_date FROM {schema_prefix}dim_time", conn)
        time_map['full_date'] = pd.to_datetime(time_map['full_date'])
        df['created_date_dt'] = pd.to_datetime(df['date_only'])
        df = df.merge(time_map, left_on='created_date_dt', right_on='full_date', how='left')
        print(f"     {len(time_map)} time entries loaded.")

        # ---- DimShipment + FactShipmentEvents ----
        print("  -> Loading DimShipment + FactShipmentEvents...")
        dim_shipment_data = df[['tracking_number', 'shipment_type', 'package_weight_category']].copy()
        dim_shipment_data['shipment_id'] = dim_shipment_data['tracking_number']
        dim_shipment_data.to_sql('dim_shipment', conn, schema=schema_name, if_exists='append', index=False)

        shipment_map = pd.read_sql(f"SELECT shipment_key, tracking_number FROM {schema_prefix}dim_shipment", conn)
        df = df.merge(shipment_map, on='tracking_number', how='left')

        # Build fact table
        dist_col = 'distance_km_x' if 'distance_km_x' in df.columns else 'distance_km'
        fact_data = pd.DataFrame()
        fact_data['shipment_key'] = df['shipment_key']
        fact_data['carrier_key'] = df['carrier_key']
        fact_data['route_key'] = df['route_key']
        fact_data['warehouse_key'] = df.get('warehouse_key')
        fact_data['time_key'] = df['time_key']
        fact_data['weather_key'] = df['weather_key']
        fact_data['distance_km'] = df[dist_col]
        fact_data['delivery_duration_hours'] = df['delivery_duration_hours']
        fact_data['delay_hours'] = df['delay_hours']
        fact_data['is_delayed'] = df['is_delayed']
        fact_data['package_weight'] = df['package_weight']

        fact_data.to_sql('fact_shipment_events', conn, schema=schema_name, if_exists='append', index=False)
        print(f"     {len(fact_data)} fact rows loaded.")

    # ---- 4. VERIFY ----
    print("\n[VERIFY] Checking row counts...")
    with engine.connect() as conn:
        for tbl in ['dim_carrier', 'dim_warehouse', 'dim_route', 'dim_weather',
                     'dim_time', 'dim_shipment', 'fact_shipment_events']:
            cnt = conn.execute(text(f"SELECT COUNT(*) FROM {schema_prefix}{tbl}")).scalar()
            print(f"  {tbl}: {cnt} rows")

    print("\n" + "=" * 60)
    print("  ETL Pipeline completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    run_etl_pipeline()
