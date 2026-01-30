# ไฟล์นี้จัดการเรื่อง "ความปลอดภัยและการเข้าถึง" (Authentication)
# ทำไมถึงมีไฟล์นี้? -> เพื่อคัดกรองคนที่จะเข้าใช้งานระบบ ไม่ให้คนนอกแอบเข้ามาดูข้อมูลในโรงงานได้
# มีหน้าที่สำคัญ:
# - Login: เช็คว่าชื่อผู้ใช้กับรหัสผ่านตรงกับที่เราเก็บไว้ใน Model User ไหม
# - Redirection: หลังจาก Login แล้ว จะส่งคนไปหน้าเว็บที่ถูกต้องตามหน้าที่ (Admin ไปหน้า Dashboard, Operator ไปหน้า Operator)
# - Logout: จัดการปิด Session เมื่อผู้ใช้งานเลิกใช้งาน
# ที่เขียนแบบนี้แยกออกมาจาก Route อื่นๆ เพื่อให้เรื่องการเข้าบ้าน (Login) ชัดเจนและดูแลง่าย ไม่ปนกับขั้นตอนการทำงานจริงครับ

from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_user
from app.models.user import User
from flask_login import logout_user, login_required

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/")
def index():
    return redirect(url_for("auth.login"))


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        print(f"DEBUG: Login Attempt for user: {request.form.get('username')}")
        username = request.form["username"]
        password = request.form["password"]

        from sqlalchemy import or_

        user = User.query.filter(
            or_(User.username == username, User.email == username)
        ).first()
        print(f"DEBUG: User found: {user}")

        if user and user.check_password(password):
            print("DEBUG: Password check passed")
            login_user(user)

            # Role-based redirection
            if user.role == "admin":
                return redirect(url_for("admin.index"))
            elif user.role == "operator":
                return redirect(url_for("operator.index"))
            else:
                return redirect(url_for("auth.login"))

        print("DEBUG: Login failed - Invalid credentials")
        # If login fails
        return render_template("auth/login.html", error="Invalid username or password")

    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
