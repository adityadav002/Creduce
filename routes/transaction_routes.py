from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from services.transaction_service import (
    get_transaction_history,
    monthly_transaction_details,
    filter_transactions
)

transaction_bp = Blueprint("transaction", __name__)


@transaction_bp.route("/transaction_detail")
@login_required
def history():

    data = get_transaction_history(
        current_user.id
    )

    return render_template(
        "transaction_detail.html",
        data=data
    )


@transaction_bp.route("/monthly_transaction")
@login_required
def monthly_transaction():

    category_details = monthly_transaction_details(
        current_user.id
    )

    return render_template(
        "monthly_transaction.html",
        category_details=category_details
    )


@transaction_bp.route("/filter_transaction")
@login_required
def filter_transaction():

    data = filter_transactions(
        current_user.id,
        request.args.get("category"),
        request.args.get("month"),
        request.args.get("payment")
    )

    return render_template(
        "filter_transaction.html",
        data=data
    )