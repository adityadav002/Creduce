from flask import Flask
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

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

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


if __name__ == "__main__":
    app.run()