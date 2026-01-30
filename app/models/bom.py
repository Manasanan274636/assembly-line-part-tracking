# ไฟล์นี้คือ "สูตรการผลิต (BOM)" ครับ บอกว่างานนี้ต้องใช้ชิ้นส่วนอะไรบ้าง อย่างละกี่ชิ้นถึงจะประกอบเสร็จ
# ทำไมถึงมีไฟล์นี้? -> เพื่อเป็น "มาตรฐานการผลิต" ให้ระบบใช้คำนวณว่า ถ้าเราจะผลิตงาน 100 ชิ้น เราต้องเตรียมอะไหล่ชนิดละกี่ชิ้น
# มีการเชื่อมต่อ (Foreign Key) ไปที่:
# - ProductionPlan: เพื่อบอกว่าเป็นสูตรสำหรับแผนการผลิตไหน
# - Part: เพื่อบอกว่าในสูตรนี้ประกอบไปด้วยชิ้นส่วนชิ้นไหนบ้าง
# ที่เขียนแบบนี้เพราะงาน 1 แผน (Plan) มักประกอบไปด้วยชิ้นส่วนหลายอย่าง การใช้ตาราง BOM มาช่วยทำให้เรากำหนดจำนวนที่ต้องใช้ (Quantity Required) ได้ยืดหยุ่นครับ

from app.utils.db import db


class BOM(db.Model):
    __tablename__ = "bom"

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(
        db.Integer, db.ForeignKey("production_plans.id"), nullable=False
    )
    part_id = db.Column(db.Integer, db.ForeignKey("parts.id"), nullable=False)
    quantity_required = db.Column(db.Integer, nullable=False)

    # Relationship to get part info
    part_info = db.relationship("Part", backref="required_in_boms", lazy=True)

    def __repr__(self):
        return f"<BOM Plan:{self.plan_id} Part:{self.part_id}>"
