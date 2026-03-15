# Station Model aligned with DB schema
from app.utils.db import db

class Station(db.Model):
    __tablename__ = "stations"

    station_id = db.Column(db.Integer, primary_key=True)
    station_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Integer, default=1)

    def __repr__(self):
        return f"<Station {self.station_name}>"
