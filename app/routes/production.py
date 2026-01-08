from flask import Blueprint, render_template
from flask_login import login_required
from app.utils.decorators import role_required

bp = Blueprint(
    "production",
    __name__,
    url_prefix="/production"
)

@bp.route("/")
@login_required                 # ต้อง login ก่อน
@role_required("admin")         # เฉพาะ admin
def index():
    return render_template("production/index.html")
