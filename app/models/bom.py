from app.utils.db import db

class BOM(db.Model):
    __tablename__ = 'bom'

    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('production_plans.id'), nullable=False)
    part_id = db.Column(db.Integer, db.ForeignKey('parts.id'), nullable=False)
    quantity_required = db.Column(db.Integer, nullable=False)
    
    # Relationship to get part info
    part_info = db.relationship('Part', backref='required_in_boms', lazy=True)

    def __repr__(self):
        return f'<BOM Plan:{self.plan_id} Part:{self.part_id}>'
