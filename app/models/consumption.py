# ไฟล์นี้ใช้จดบันทึก "การเบิกไปใช้" ครับ ว่าใครหยิบชิ้นส่วนไหนไปใช้ที่สถานีไหน และมีของเสีย (Scrap) เกิดขึ้นเท่าไหร่
# ทำไมถึงมีไฟล์นี้? -> เพื่อบันทึก "เหตุการณ์จริง" ในไลน์การผลิต ทำให้เราทำรายงาน (Report) สรุปยอดการใช้งานและของเสียได้อย่างแม่นยำ
# มีการเชื่อมต่อ (Foreign Key) ไปที่:
# - Station: เพื่อบอกว่าของนี้ถูกใช้ที่จุดไหน
# - ProductionPlan: เพื่อบอกว่าของนี้ถูกใช้ในแผนงานหรืองานโปรเจกต์ไหน
# - Part: เพื่อระบุว่าชิ้นส่วนที่ถูกใช้คือชิ้นไหน
# ที่เขียนแบบนี้เพราะการใช้งาน 1 ครั้ง ต้องเชื่อมโยงข้อมูลจากหลายที่เข้าด้วยกัน เพื่อให้ภาพรวมของรายงานมีความเกี่ยวข้องกันทั้งหมดครับ

from app.utils.db import db
from datetime import datetime


class Consumption(db.Model):
    __tablename__ = "consumptions"

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey("stations.id"), nullable=False)
    plan_id = db.Column(
        db.Integer, db.ForeignKey("production_plans.id"), nullable=False
    )
    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False)
    quantity_used = db.Column(db.Integer, nullable=False)
    scrap_qty = db.Column(db.Integer, default=0)
    lot_no = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Consumption {self.quantity_used} of Part:{self.part_id}>"
