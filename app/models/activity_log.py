# ActivityLog Model aligned with DB schema
from app.utils.db import db

class ActivityLog(db.Model):
    __tablename__ = "activity_log"

    activity_id = db.Column(db.Integer, primary_key=True)
    activity_type = db.Column(db.String(100), nullable=False)
    reference_id = db.Column(db.String(100))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.now())
    created_by = db.Column(db.Integer, db.ForeignKey("users.user_id"))

    # Relationships
    user = db.relationship("User", backref="activity_logs", lazy=True)

    def __repr__(self):
        return f"<ActivityLog {self.activity_id} Type:{self.activity_type}>"
