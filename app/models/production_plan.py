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
    def total_required_parts(self):
        """Calculates total required parts across all BOM entries for this plan"""
        from app.models.bom import BOM
        boms = BOM.query.filter_by(model=self.product_name).all()
        if boms and (self.quantity_planned or 0) > 0:
            return sum((b.qty_per_unit or 0) * self.quantity_planned for b in boms)
        if self.consumptions:
            planned_sum = sum(c.planned_qty or 0 for c in self.consumptions)
            if planned_sum > 0:
                return planned_sum
        return self.quantity_planned or 0

    @property
    def progress(self):
        """Calculates production progress percentage"""
        if not self.consumptions:
            return 0
        total_actual = sum(c.actual_qty or 0 for c in self.consumptions)
        target = self.total_required_parts
        if target > 0:
            prog = int(round((total_actual / target) * 100))
            return min(prog, 100)
        return 0

    def __repr__(self):
        return f"<ProductionPlan {self.order_id}>"
