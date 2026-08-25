# ไฟล์นี้คือ "ถังข้อมูลทดสอบ" (Data Seeder)
# ทำไมถึงมีไฟล์นี้? -> เพื่อเติมข้อมูลตัวอย่าง (เช่น ชื่ออะไหล่, ยอดในคลัง, แผนการผลิต) ให้ระบบไม่ว่างเปล่า
# หน้าที่สำคัญ:
# 1. ล้างฐานข้อมูลเก่าทิ้งทั้งหมด (Drop All)
# 2. สร้างใหม่ และใส่ข้อมูลที่จำลองมาจากหน้ากรงใน Figma (โปรเจกต์ต้นแบบ)
# คำเตือน: รันไฟล์นี้แล้วข้อมูลเก่าจะหายหมดนะครับ ใช้สำหรับเริ่มต้นทดสอบระบบเท่านั้นครับ

from app import create_app
from app.utils.db import db
from app.models.user import User
from app.models.part import Part
from app.models.station import Station
from app.models.production_plan import ProductionPlan
from app.models.bom import BOM
from app.models.consumption import Consumption
from app.models.scrap import Scrap
from app.models.stock import Stock
from datetime import datetime, date


def seed_data():
    app = create_app()
    with app.app_context():
        print("Dropping and recreating all tables...")
        db.drop_all()
        db.create_all()

        print("Creating default users...")
        admin = User(username="admin", email="admin@example.com", role="admin")
        admin.set_password("admin123")
        op = User(username="operator", email="operator@example.com", role="operator")
        op.set_password("op123")
        db.session.add_all([admin, op])
        db.session.flush()

        print("Creating default stations...")
        s1 = Station(station_name="Assembly Line 1", description="Main Assembly")
        db.session.add(s1)
        db.session.flush()

        # Data from Figma exact match
        figma_parts = [
            {
                "name": "Motor Assembly",
                "sku": "M-401",
                "stock": 250,
                "min": 100,
                "req": 150,
                "used": 145,
                "scrap": 10,
            },
            {
                "name": "Bearing Unit",
                "sku": "B-225",
                "stock": 87,
                "min": 100,
                "req": 300,
                "used": 298,
                "scrap": 15,
            },
            {
                "name": "Gear Box",
                "sku": "GB-150",
                "stock": 350,
                "min": 100,
                "req": 200,
                "used": 195,
                "scrap": 12,
            },
            {
                "name": "Control Panel",
                "sku": "CP-88",
                "stock": 28,
                "min": 100,
                "req": 100,
                "used": 102,
                "scrap": 5,
            },
            {
                "name": "Hydraulic Pump",
                "sku": "HP-320",
                "stock": 180,
                "min": 50,
                "req": 80,
                "used": 78,
                "scrap": 4,
            },
            {
                "name": "Sensor Module",
                "sku": "SM-77",
                "stock": 92,
                "min": 150,
                "req": 400,
                "used": 395,
                "scrap": 22,
            },
            {
                "name": "Cable Harness",
                "sku": "CH-450",
                "stock": 225,
                "min": 200,
                "req": 350,
                "used": 347,
                "scrap": 14,
            },
            {
                "name": "PCB Board",
                "sku": "PCB-300",
                "stock": 35,
                "min": 80,
                "req": 120,
                "used": 118,
                "scrap": 7,
            },
        ]

        print("Creating active production plan...")
        plan = ProductionPlan(
            order_id="ORD-001",
            product_name="Product Model A",
            quantity_planned=100,
            start_date=date.today(),
            end_date=date.today(),
            status="In Progress",
            created_by=admin.user_id,
        )
        db.session.add(plan)
        db.session.flush()

        print("Seeding parts and consumption records...")
        for p_data in figma_parts:
            # Create Part
            part = Part(
                part_id=p_data["sku"],
                part_name=p_data["name"],
                stock_qty=p_data["stock"],
                min_level=p_data["min"],
                safety_stock=p_data["min"] // 2,
                max_level=p_data["stock"] * 2,
                unit="pcs",
                is_active=1,
            )
            db.session.add(part)
            db.session.flush()

            # Create BOM for the plan (Product Model A)
            bom = BOM(
                model="Product Model A",
                part_id=part.part_id,
                qty_per_unit=max(1, p_data["req"] // 100)
            )
            db.session.add(bom)

            # Create Consumption record
            consumption = Consumption(
                station_id=s1.station_id,
                order_id=plan.order_id,
                part_id=part.part_id,
                planned_qty=p_data["used"],
                actual_qty=p_data["used"],
                recorded_by=op.user_id,
            )
            db.session.add(consumption)
            db.session.flush()

            # Create Scrap record if any
            if p_data["scrap"] > 0:
                scrap = Scrap(
                    consumption_id=consumption.consumption_id,
                    scrap_qty=p_data["scrap"],
                    reason="Defect detected on line"
                )
                db.session.add(scrap)

            # Create initial stock history record
            stock_history = Stock(
                part_id=part.part_id,
                change_qty=p_data["stock"],
                change_type="IN",
                reference_id="Initial Seed",
                created_by=admin.user_id
            )
            db.session.add(stock_history)

        db.session.commit()
        print("Database seeded with Figma-accurate data successfully!")


if __name__ == "__main__":
    seed_data()
