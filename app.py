from flask import Flask, render_template
from dotenv import load_dotenv
from flask_login import LoginManager

from config import Config
from models.user import User

from routes.auth_routes import auth_bp
from routes.dashboard_routes import dashboard_bp
from routes.expense_routes import expense_bp
from routes.profile_routes import profile_bp
from routes.transaction_routes import transaction_bp
from routes.analysis_routes import analysis_bp
from routes.utility_routes import utility_bp
from routes.account_routes import account_bp
from routes.category_routes import category_bp

load_dotenv()
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Database Schema
from utils.db import create_tables
with app.app_context():
    create_tables()

# Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"


@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(expense_bp)
app.register_blueprint(profile_bp)
app.register_blueprint(transaction_bp)
app.register_blueprint(analysis_bp)
app.register_blueprint(utility_bp)
app.register_blueprint(account_bp)
app.register_blueprint(category_bp)


@app.errorhandler(404)
def not_found(error):
    app.logger.warning("404 Not Found: %s", error)
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(error):
    app.logger.exception("Unhandled server error: %s", error)
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run()
