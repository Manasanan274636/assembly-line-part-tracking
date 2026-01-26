from app.utils.db import db
from datetime import datetime

class Part(db.Model):
    __tablename__ = 'parts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(50))
    unit = db.Column(db.String(20), default='unit')
    min_stock_level = db.Column(db.Integer, default=0)
    current_stock = db.Column(db.Integer, default=0)
    
    # Relationships
    stocks = db.relationship('Stock', backref='part', lazy=True)
    consumptions = db.relationship('Consumption', backref='part', lazy=True)

    def __repr__(self):
        return f'<Part {self.name}>'
