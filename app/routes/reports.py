from flask import Blueprint, render_template
from flask_login import login_required
from app.utils.decorators import role_required

bp = Blueprint("reports", __name__, url_prefix="/reports")

@bp.route("/")
@login_required
@role_required("admin")
def index():
    return render_template("reports/index.html")