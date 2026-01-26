from app.utils.db import db
from datetime import datetime

class Consumption(db.Model):
    __tablename__ = 'consumptions'

    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('stations.id'), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey('production_plans.id'), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    quantity_used = db.Column(db.Integer, nullable=False)
    scrap_qty = db.Column(db.Integer, default=0)
    lot_no = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Consumption {self.quantity_used} of Part:{self.part_id}>'
