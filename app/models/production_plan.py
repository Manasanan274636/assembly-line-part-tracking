# ไฟล์นี้เก็บ "แผนการผลิต" ครับ ว่าวันนี้เราจะผลิตงานอะไร กี่ชิ้น และสถานะตอนนี้ทำถึงไหนแล้ว
# ทำไมถึงมีไฟล์นี้? -> เพื่อเป็น "ตัวตั้งต้นของงาน" ในระบบ ทำให้เรารู้เป้าหมาย (Target Qty) และวันที่ต้องเสร็จ (Target Date)
# มีการเชื่อมต่อ (Foreign Key / Relationship) ไปที่:
# - Station: เพื่อบอกว่าแผนนี้ต้องผลิตที่สถานีไหน
# - BOM: เพื่อดึงรายการอะไหล่ที่ต้องใช้ตามสูตร
# - Consumption: เพื่อดูยอดผลิตจริง (Actual Output) ที่เกิดขึ้นจริง
# ที่เขียนแบบนี้เพราะเราต้องการรวมศูนย์ข้อมูลของโครงการหรือแผนงานไว้ที่เดียว เพื่อให้ง่ายต่อการติดตามความคืบหน้า (Status) ของงานครับ

from app.utils.db import db
from datetime import datetime


class ProductionPlan(db.Model):
    __tablename__ = "production_plans"

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey("stations.id"), nullable=False)
    project_title = db.Column(db.String(200), nullable=False)
    target_date = db.Column(db.Date)
    planned_qty = db.Column(db.Integer, default=0)
    actual_output = db.Column(db.Integer, default=0)
    status = db.Column(
        db.String(50), default="In Progress"
    )  # In Progress, Completed, On Hold
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    bom_items = db.relationship("BOM", backref="plan", lazy=True)
    consumptions = db.relationship("Consumption", backref="plan", lazy=True)

    def __repr__(self):
        return f"<ProductionPlan {self.project_title}>"
