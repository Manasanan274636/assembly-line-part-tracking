# ไฟล์นี้คือ "จุดกำเนิดของแอปพลิเคชัน" (Application Factory)
# ทำไมถึงมีไฟล์นี้? -> เพื่อรวบรวมส่วนประกอบทุกอย่าง (Database, Login, Routes) เข้ามาประกอบร่างเป็นตัวเว็บ
# หน้าที่สำคัญ:
# 1. ตั้งค่าระบบสมาชิก (LoginManager)
# 2. เชื่อมต่อฐานข้อมูลและระบบอัปเดตตาราง (SQLAlchemy & Migrate)
# 3. ลงทะเบียนเส้นทางเดินเว็บ (Blueprints) เช่น /admin, /auth, /operator
# 4. กำหนดหน้าแรกสุด (/) ว่าถ้าใครเข้ามาให้ส่งไปหน้าไหนตามสิทธิ์ของเขาครับ

from flask import Flask
from flask_login import LoginManager
from app.models.user import User

login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    from app.utils.db import db

    db.init_app(app)
    from flask_migrate import Migrate

    Migrate(app, db)

    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.routes import auth, admin, operator

    # app.register_blueprint(dashboard.bp) # Removed
    # app.register_blueprint(production.bp) # Removed
    # app.register_blueprint(consumption.bp) # Removed
    # app.register_blueprint(stock.bp) # Removed
    # app.register_blueprint(reports.bp) # Removed

    app.register_blueprint(auth.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(operator.bp)

    from flask import redirect, url_for
    from flask_login import current_user

    @app.route("/favicon.ico")
    def favicon():
        return "", 204

    @app.route("/")
    def index():
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if current_user.role == "admin":
            return redirect(url_for("admin.index"))
        return redirect(url_for("operator.index"))

    return app
