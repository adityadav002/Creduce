from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from services.user_service import get_user_profile
from services.budget_service import save_monthly_budget

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    if request.method == "POST":
        monthly_budget = request.form.get("monthly_budget")

        save_monthly_budget(
            current_user.id,
            monthly_budget
        )

    user = get_user_profile(current_user.id)

    return render_template(
        "profile.html",
        user=user
    )