# Claim Model aligned with DB schema
from app.utils.db import db

class Claim(db.Model):
    __tablename__ = "claim"

    claim_id = db.Column(db.String(50), primary_key=True)
    part_id = db.Column(db.String(50), db.ForeignKey("parts.part_id"))
    qty = db.Column(db.Integer, default=0)
    claim_date = db.Column(db.Date)
    claim_status = db.Column(db.String(100), default="Pending")
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.user_id"))

    # Relationships
    part = db.relationship("Part", backref="claims", lazy=True)
    user = db.relationship("User", backref="claims", lazy=True)

    def __repr__(self):
        return f"<Claim {self.claim_id} Part:{self.part_id}>"
