from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from services.analysis_service import (
    transaction_analysis_service,
    compare_months_service
)

analysis_bp = Blueprint("analysis", __name__)


@analysis_bp.route("/transaction_analysis")
@login_required
def transaction_analysis():

    category_totals_dict, month_amounts = (
        transaction_analysis_service(current_user.id)
    )

    return render_template(
        "transaction_analysis.html",
        category_totals_dict=category_totals_dict,
        month_amounts=month_amounts
    )


@analysis_bp.route("/compare_months", methods=["GET"])
@login_required
def compare_months():

    data = compare_months_service(
        current_user.id,
        request.args.get("month1"),
        request.args.get("month2"),
        request.args.get("year1"),
        request.args.get("year2")
    )

    return render_template(
        "compare_months.html",
        **data
    )