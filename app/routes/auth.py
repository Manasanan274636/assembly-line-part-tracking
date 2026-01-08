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
        username = request.form["username"]

        # mock user
        if username == "admin":
            user = User("1", "admin", "admin")
        else:
            user = User("2", "operator", "operator")

        login_user(user)
        return redirect(url_for("dashboard.index"))

    return render_template("auth/login.html")

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))