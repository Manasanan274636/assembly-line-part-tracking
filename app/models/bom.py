# BOM Model aligned with DB schema
from app.utils.db import db

class BOM(db.Model):
    __tablename__ = "bom"

    bom_id = db.Column(db.Integer, primary_key=True)
    model = db.Column(db.String(50))
    part_id = db.Column(db.String(50), db.ForeignKey("parts.part_id"), primary_key=True)
    qty_per_unit = db.Column(db.Integer, nullable=False)

    # Relationships
    part = db.relationship("Part", backref="bom_entries", lazy=True)

    def __repr__(self):
        return f"<BOM {self.bom_id} Part:{self.part_id}>"
