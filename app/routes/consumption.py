from flask import Blueprint, render_template
from flask_login import login_required
from app.utils.decorators import role_required

bp = Blueprint("consumption", __name__, url_prefix="/consumption")

@bp.route("/")
@login_required
@role_required("operator")
def index():
    return render_template("consumption/index.html")
