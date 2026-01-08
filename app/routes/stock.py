from flask import Blueprint, render_template
from flask_login import login_required

from app.utils.decorators import role_required

bp = Blueprint("stock", __name__, url_prefix="/stock")

@bp.route("/")
@login_required
@role_required("operator")
def index():
    return render_template("stock/index.html")  