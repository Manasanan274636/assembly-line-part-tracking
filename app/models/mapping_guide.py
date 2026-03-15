# ไฟล์นี้ใช้เก็บ "คำอธิบายคอลัมน์ (Mapping Guide)" ระหว่างไฟล์ต้นฉบับกับเทมเพลตครับ
# ทำไมถึงมีไฟล์นี้? -> เพื่อใช้เป็นจุดอ้างอิงในการทำ ETL หรือการโอนย้ายข้อมูลในอนาคต

from app.utils.db import db

class MappingGuide(db.Model):
    __tablename__ = "mapping_guide"

    id = db.Column('mapping_id', db.Integer, primary_key=True, autoincrement=True)
    source_file = db.Column(db.String(255))
    source_column = db.Column(db.String(255))
    template_sheet = db.Column(db.String(100))
    template_column = db.Column(db.String(100))

    def __repr__(self):
        return f"<MappingGuide {self.template_sheet}.{self.template_column}>"
