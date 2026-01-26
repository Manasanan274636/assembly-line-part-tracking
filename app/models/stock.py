from app.utils.db import db
from datetime import datetime

class Stock(db.Model):
    __tablename__ = 'stock_history'

    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    change_qty = db.Column(db.Integer, nullable=False) # positive for stock-in, negative for consumption adjustment
    reason = db.Column(db.String(200)) # e.g., 'Purchase', 'Manual Adjustment', 'Scrap'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Stock Change {self.change_qty} for Part:{self.part_id}>'
