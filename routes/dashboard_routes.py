from flask import Blueprint, render_template
from flask_login import login_required, current_user

from services.dashboard_service import get_dashboard_data

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def main():

    dashboard_data = get_dashboard_data(current_user.id)

    return render_template(
        "dashboard.html",
        **dashboard_data
    )