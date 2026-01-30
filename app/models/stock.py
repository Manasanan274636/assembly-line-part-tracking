# ไฟล์นี้คือ "ประวัติสต็อก" ครับ เอาไว้ดูย้อนหลังว่าของเข้า-ออกตอนไหน และเพราะอะไร (เช่น ซื้อเพิ่ม หรือ แก้ไขสต็อกเอง)
# ทำไมถึงมีไฟล์นี้? -> เพื่อสร้าง "บัญชีคลังสินค้า" (Audit Trail) ให้เราตรวจสอบย้อนกลับได้เสมอว่ายอดสต็อกที่เปลี่ยนไปเนี่ย มันมาจากสาเหตุอะไร
# มีการเชื่อมต่อ (Foreign Key) ไปที่:
# - Part: เพื่อระบุว่านี่คือประวัติของชิ้นส่วนชิ้นไหน
# ที่เขียนแบบนี้เพราะยอดคงเหลือ (Current Stock) ในไฟล์ Part อาจจะไม่พอสำหรับการตรวจสอบหาที่มาที่ไป เราจึงต้องมีตาราง History นี้ไว้เก็บทุกความเคลื่อนไหวครับ

from app.utils.db import db
from datetime import datetime


class Stock(db.Model):
    __tablename__ = "stock_history"

    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False)
    change_qty = db.Column(
        db.Integer, nullable=False
    )  # positive for stock-in, negative for consumption adjustment
    reason = db.Column(db.String(200))  # e.g., 'Purchase', 'Manual Adjustment', 'Scrap'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Stock Change {self.change_qty} for Part:{self.part_id}>"
