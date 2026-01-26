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
