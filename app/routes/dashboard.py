from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user, login_required

from app.utils.decorators import role_required

bp = Blueprint("dashboard", __name__)

@bp.route("/")
def index():
    return render_template("dashboard/index.html")
