# ไฟล์นี้เก็บข้อมูล "สถานีงาน" หรือจุดต่างๆ ในสายการผลิต ครับ ว่ามีจุดไหนบ้าง (เช่น Station A, Station B)
# ทำไมถึงมีไฟล์นี้? -> เพื่อกำหนดพื้นที่ทำงานให้ชัดเจน ทำให้รู้ว่าคอขวดหรือของเสียเกิดขึ้นที่สถานีไหนเป็นพิเศษ
# มีการเชื่อมต่อ (Relationship) ไปที่:
# - ProductionPlan: เพื่อบอกว่าสถานีนี้กำลังทำงานตามแผนงานไหนอยู่
# - Consumption: เพื่อดึงข้อมูลการใช้งานย้อนหลังของสถานีนี้
# ที่เขียนแบบนี้เพราะเรามองว่าระบบโรงงานต้องมีการระบุตำแหน่งการทำงาน การแยกตาราง Station ออกมาทำให้เราเปลี่ยนชื่อหรือเพิ่มจุดทำงานใหม่ได้โดยไม่กระทบข้อมูลอื่นครับ

from app.utils.db import db


class Station(db.Model):
    __tablename__ = "stations"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)

    # Relationships
    plans = db.relationship("ProductionPlan", backref="station", lazy=True)
    consumptions = db.relationship("Consumption", backref="station", lazy=True)

    def __repr__(self):
        return f"<Station {self.name}>"
