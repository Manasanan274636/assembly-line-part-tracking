from app.utils.db import db

class Station(db.Model):
    __tablename__ = 'stations'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    
    # Relationships
    plans = db.relationship('ProductionPlan', backref='station', lazy=True)
    consumptions = db.relationship('Consumption', backref='station', lazy=True)

    def __repr__(self):
        return f'<Station {self.name}>'
