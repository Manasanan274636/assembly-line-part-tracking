# Part Model aligned with DB schema
from app.utils.db import db

class Part(db.Model):
    __tablename__ = "parts"

    part_id = db.Column(db.String(50), primary_key=True)
    part_name = db.Column(db.String(255), nullable=False)
    unit = db.Column(db.String(20), default="unit")
    stock_qty = db.Column(db.Integer, default=0)
    min_level = db.Column(db.Integer, default=0)
    max_level = db.Column(db.Integer)
    safety_stock = db.Column(db.Integer)
    is_active = db.Column(db.Integer, default=1)

    def __repr__(self):
        return f"<Part {self.part_name}>"
