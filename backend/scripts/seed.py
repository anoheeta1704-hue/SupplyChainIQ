import asyncio
import os
import sys

# Add the backend directory to python path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.database import async_engine, Base
from app.models import User, Carrier, Warehouse, RouteData, Customer
from app.core.security import hash_password
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker

async def seed():
    print("Starting database seed...")
    
    # Create tables (just in case they don't exist)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created/verified.")

    async_session = sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as db:
        # Seed Admin User
        admin_email = "admin@supplychainiq.com"
        from sqlalchemy import select
        res = await db.execute(select(User).where(User.email == admin_email))
        if not res.scalar_one_or_none():
            admin = User(
                name="Admin User",
                email=admin_email,
                password_hash=hash_password("admin123"),
                role="admin"
            )
            db.add(admin)
            print("Added admin user.")
            
        manager_email = "manager@supplychainiq.com"
        res = await db.execute(select(User).where(User.email == manager_email))
        if not res.scalar_one_or_none():
            manager = User(
                name="Logistics Manager",
                email=manager_email,
                password_hash=hash_password("manager123"),
                role="logistics_manager"
            )
            db.add(manager)
            print("Added logistics manager.")

        # Seed Carriers
        carriers_data = [
            {"name": "Delhivery", "code": "DLV", "service_type": "Express", "rating": 4.5},
            {"name": "BlueDart", "code": "BD", "service_type": "Premium", "rating": 4.8},
            {"name": "Ecom Express", "code": "ECOM", "service_type": "Standard", "rating": 4.2},
            {"name": "XpressBees", "code": "XB", "service_type": "Economy", "rating": 4.0},
        ]
        
        for cd in carriers_data:
            res = await db.execute(select(Carrier).where(Carrier.code == cd["code"]))
            if not res.scalar_one_or_none():
                c = Carrier(**cd)
                db.add(c)
        print("Added carriers.")

        # Seed Warehouses
        warehouses_data = [
            {"name": "Bengaluru Main Hub", "code": "WH-BLR-1", "city": "Bengaluru", "state": "Karnataka", "latitude": 12.9716, "longitude": 77.5946, "capacity": 50000},
            {"name": "Mumbai Distribution Center", "code": "WH-BOM-1", "city": "Mumbai", "state": "Maharashtra", "latitude": 19.0760, "longitude": 72.8777, "capacity": 40000},
            {"name": "Delhi NCR Fulfillment", "code": "WH-DEL-1", "city": "Delhi", "state": "Delhi", "latitude": 28.7041, "longitude": 77.1025, "capacity": 60000},
            {"name": "Kolkata Regional Center", "code": "WH-CCU-1", "city": "Kolkata", "state": "West Bengal", "latitude": 22.5726, "longitude": 88.3639, "capacity": 30000},
            {"name": "Chennai Port Hub", "code": "WH-MAA-1", "city": "Chennai", "state": "Tamil Nadu", "latitude": 13.0827, "longitude": 80.2707, "capacity": 35000},
            {"name": "Hyderabad Tech Park WH", "code": "WH-HYD-1", "city": "Hyderabad", "state": "Telangana", "latitude": 17.3850, "longitude": 78.4867, "capacity": 45000},
        ]
        
        for wd in warehouses_data:
            res = await db.execute(select(Warehouse).where(Warehouse.code == wd["code"]))
            if not res.scalar_one_or_none():
                w = Warehouse(**wd)
                db.add(w)
        print("Added warehouses.")

        await db.commit()
        print("Database seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed())
