# ProductionPlan Model aligned with DB schema
from app.utils.db import db

class ProductionPlan(db.Model):
    __tablename__ = "production_plan"

    order_id = db.Column(db.String(50), primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    quantity_planned = db.Column(db.Integer, default=0)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(50), default="In Progress")
    created_by = db.Column(db.Integer, db.ForeignKey("users.user_id"))

    # Relationships
    user = db.relationship("User", backref="production_plans", lazy=True)

    @property
    def progress(self):
        """Calculates production progress percentage"""
        if not self.consumptions:
            return 0
        total_actual = sum(c.actual_qty for c in self.consumptions)
        if self.quantity_planned > 0:
            prog = int((total_actual / self.quantity_planned) * 100)
            return min(prog, 100)
        return 0

    def __repr__(self):
        return f"<ProductionPlan {self.order_id}>"
