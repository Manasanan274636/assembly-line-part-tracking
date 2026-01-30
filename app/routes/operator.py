# ไฟล์นี้คือ "หน้าต่างการทำงานของพนักงาน" (Operator Interface)
# ทำไมถึงมีไฟล์นี้? -> เพื่อแยกหน้าจอกันระหว่างคนคุมระบบ (Admin) กับคนทำงานหน้าเครื่อง (Operator) ไม่ให้สับสน
# มีหน้าที่สำคัญ:
# - โชว์หน้าจอที่จำเป็นสำหรับการผลิตและการตัดสต็อกที่หน้าเครื่อง
# - รักษาความปลอดภัยด้วย @role_required("operator") เพื่อกันไม่ให้คนอื่นเข้ามาดูหน้างานนี้
# ที่เขียนแบบนี้เพื่อให้หนัาจอของพนักงานมีความเรียบง่าย (Simple) เน้นเฉพาะข้อมูลที่ต้องใช้ตอนทำงานหน้าเครื่องเท่านั้นครับ

from flask import Blueprint, render_template
from flask_login import login_required
from app.utils.decorators import role_required

bp = Blueprint("operator", __name__, url_prefix="/operator")


@bp.route("/")
@login_required
@role_required("operator")
def index():
    return render_template("operator/dashboard.html")


@bp.route("/production")
@login_required
@role_required("operator")
def production():
    return render_template("operator/production.html")


@bp.route("/consumption")
@login_required
@role_required("operator")
def consumption():
    return render_template("operator/consumption.html")


@bp.route("/stock")
@login_required
@role_required("operator")
def stock():
    return render_template("operator/stock.html")


@bp.route("/reports")
@login_required
@role_required("operator")
def reports():
    return render_template("operator/reports.html")
