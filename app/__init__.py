from flask import Flask
from flask_login import LoginManager
from app.routes import dashboard, production, consumption, stock, reports, auth
from app.models.user import User

login_manager = LoginManager()
login_manager.login_view = "auth.login"

def create_app():
    app = Flask(__name__)
    app.secret_key = "dev-secret"

    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        # mock user
        if user_id == "1":
            return User("1", "admin", "admin")
        if user_id == "2":
            return User("2", "operator", "operator")
        return None

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(production.bp)
    app.register_blueprint(consumption.bp)
    app.register_blueprint(stock.bp)
    app.register_blueprint(reports.bp)

    return app
