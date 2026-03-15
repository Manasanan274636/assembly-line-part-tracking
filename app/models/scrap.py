# Scrap Model aligned with DB schema
from app.utils.db import db

class Scrap(db.Model):
    __tablename__ = "scrap"

    scrap_id = db.Column(db.Integer, primary_key=True)
    consumption_id = db.Column(db.Integer, db.ForeignKey("consumption.consumption_id"))
    scrap_qty = db.Column(db.Integer, default=0)
    reason = db.Column(db.String(255))

    # Relationships
    consumption = db.relationship("Consumption", backref="scraps", lazy=True)

    def __repr__(self):
        return f"<Scrap {self.scrap_id} Qty:{self.scrap_qty}>"
