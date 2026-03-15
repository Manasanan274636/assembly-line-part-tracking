# User Model aligned with DB schema
from flask_login import UserMixin
from app.utils.db import db

class User(UserMixin, db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default="operator")
    email = db.Column(db.String(120), unique=True)
    created_at = db.Column(db.DateTime, default=db.func.now())
    is_active_flag = db.Column('is_active', db.Integer, default=1)

    def get_id(self):
        return str(self.user_id)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        # Support both plain text (for initial seeding if any) and hashed passwords
        if self.password == password:
            return True
        return check_password_hash(self.password, password)

    def __repr__(self):
        return f"<User {self.username}>"
