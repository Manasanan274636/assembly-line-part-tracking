# Consumption Model aligned with DB schema
from app.utils.db import db

class Consumption(db.Model):
    __tablename__ = "consumption"

    consumption_id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.String(50), db.ForeignKey("production_plan.order_id"))
    part_id = db.Column(db.String(50), db.ForeignKey("parts.part_id"))
    station_id = db.Column(db.Integer, db.ForeignKey("stations.station_id"))
    planned_qty = db.Column(db.Integer, default=0)
    actual_qty = db.Column(db.Integer, default=0)
    recorded_by = db.Column(db.Integer, db.ForeignKey("users.user_id"))
    recorded_at = db.Column(db.DateTime, default=db.func.now())

    # Relationships
    plan = db.relationship("ProductionPlan", backref="consumptions", lazy=True)
    part = db.relationship("Part", backref="consumptions", lazy=True)
    station = db.relationship("Station", backref="consumptions", lazy=True)
    user = db.relationship("User", backref="consumptions", lazy=True)

    def __repr__(self):
        return f"<Consumption {self.consumption_id} Order:{self.order_id}>"
