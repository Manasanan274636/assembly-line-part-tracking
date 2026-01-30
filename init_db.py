# ไฟล์นี้คือ "ช่างก่อสร้าง" (Database Initializer)
# ทำไมถึงมีไฟล์นี้? -> เพื่อสร้าง "ตาราง" ทั้งหมดในฐานข้อมูล MySQL/SQLite จากศูนย์
# หน้าที่สำคัญ:
# 1. เชื่อมต่อฐานข้อมูล
# 2. สร้างโครงสร้างตารางตามที่นิยามไว้ใน Models
# 3. สร้าง User พื้นฐาน (admin และ operator) ให้คุณพร้อมใช้งานครั้งแรกครับ

from app import create_app
from app.utils.db import db
from app.models.user import User
from app.models.part import Part
from app.models.station import Station
from app.models.production_plan import ProductionPlan
from app.models.bom import BOM
from app.models.consumption import Consumption
from app.models.stock import Stock


def init_db():
    app = create_app()
    with app.app_context():
        print("Creating tables...")
        db.create_all()

        # Check if admin exists
        if not User.query.filter_by(username="admin").first():
            print("Creating default users...")
            admin = User(username="admin", email="admin@example.com", role="admin")
            admin.set_password("admin123")
            op = User(
                username="operator", email="operator@example.com", role="operator"
            )
            op.set_password("op123")
            db.session.add(admin)
            db.session.add(op)
            db.session.commit()
            print("Default users created!")
        else:
            print("Admin user already exists.")

        print("Database initialized successfully!")


if __name__ == "__main__":
    init_db()
