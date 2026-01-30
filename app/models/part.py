# ไฟล์นี้เอาไว้เก็บ "ข้อมูลชิ้นส่วน" ครับ ว่าในโรงงานเรามีอะไหล่อะไรบ้าง SKU ไหน และตอนนี้เหลือของในสต็อกกี่ชิ้น
# ทำไมถึงมีไฟล์นี้? -> เพื่อสร้าง "ฐานข้อมูลหลักของสินค้า" (Master Data) ให้ระบบรู้ว่าเรามีของอะไรบ้างในคลัง
# มีการเชื่อมต่อ (Relationship) ไปที่:
# - Stock: เพื่อดูประวัติการเข้า-ออกของชิ้นส่วนนี้
# - Consumption: เพื่อดูว่าชิ้นส่วนนี้ถูกเอาไปใช้ผลิตงานอะไรไปบ้าง
# ที่เขียนแบบนี้เพราะเราต้องการเก็บข้อมูลพื้นฐานแยกออกมา ไม่ให้ปนกับประวัติการใช้งาน ทำให้จัดการข้อมูลได้ง่ายขึ้นครับ

from app.utils.db import db
from datetime import datetime


class Part(db.Model):
    __tablename__ = "parts"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(50))
    unit = db.Column(db.String(20), default="unit")
    min_stock_level = db.Column(db.Integer, default=0)
    current_stock = db.Column(db.Integer, default=0)

    # Relationships
    stocks = db.relationship("Stock", backref="part", lazy=True)
    consumptions = db.relationship("Consumption", backref="part", lazy=True)

    def __repr__(self):
        return f"<Part {self.name}>"
