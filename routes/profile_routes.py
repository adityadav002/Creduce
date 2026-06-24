from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from services.user_service import get_user_profile, update_user_profile
from services.budget_service import save_monthly_budget

profile_bp = Blueprint("profile", __name__)


@profile_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        monthly_budget = request.form.get("monthly_budget")

        if name or email:
            update_user_profile(current_user.id, name, email)
        if monthly_budget is not None:
            save_monthly_budget(current_user.id, monthly_budget)

    user = get_user_profile(current_user.id)
    from services.budget_service import get_monthly_budget
    budget = get_monthly_budget(current_user.id)

    return render_template(
        "profile.html",
        user=user,
        budget=budget
    )
