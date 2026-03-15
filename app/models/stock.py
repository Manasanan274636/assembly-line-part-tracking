# Stock History Model aligned with DB schema
from app.utils.db import db

class Stock(db.Model):
    __tablename__ = "stock_history"

    history_id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.String(50), db.ForeignKey("parts.part_id"))
    change_qty = db.Column(db.Integer, nullable=False)
    change_type = db.Column(db.String(50))
    reference_id = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=db.func.now())
    created_by = db.Column(db.Integer, db.ForeignKey("users.user_id"))

    # Relationships
    part = db.relationship("Part", backref="stock_history", lazy=True)
    user = db.relationship("User", backref="stock_history", lazy=True)

    def __repr__(self):
        return f"<Stock {self.history_id} Part:{self.part_id}>"
