# ไฟล์นี้เก็บข้อมูล "ผู้ใช้งาน" ครับ ทั้ง Admin และ Operator เอาไว้เช็คชื่อ-รหัสผ่านเวลาจะ Login เข้าเว็บ
# ทำไมถึงมีไฟล์นี้? -> เพื่อความปลอดภัยและแบ่งสิทธิ์การใช้งาน (Role Based Access Control) ใครเป็นแอดมินดูสรุปได้ ใครเป็นพนักงานคีย์ข้อมูลได้
# มีหน้าที่สำคัญ:
# - เก็บ Password แบบ Hash (ถอดรหัสไม่ได้) เพื่อความปลอดภัย
# - แยกประเภทผู้ใช้ (Role) เพื่อจำกัดเมนูที่จะเห็นบนหน้าเว็บ
# ที่เขียนแบบนี้เพื่อให้ระบบจัดการสิทธิ์ได้ชัดเจนและตรวจสอบได้ว่าใครเป็นคนทำรายการต่างๆ ในเครื่องครับ

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.utils.db import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(512))
    role = db.Column(
        db.String(20), nullable=False, default="operator"
    )  # admin / operator

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"
