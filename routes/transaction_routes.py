from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from services.transaction_service import (
    get_transaction_history,
    monthly_transaction_details,
    filter_transactions,
    get_user_accounts  # NEW: powers the Account filter dropdown
)
from services.category_service import get_all_categories  # NEW: powers the cascading Category/Subcategory dropdowns

transaction_bp = Blueprint("transaction", __name__)


@transaction_bp.route("/transaction_detail")
@login_required
def history():
    # --- NOT CHANGED: unrelated to this request.
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
    # --- NOT CHANGED: unrelated to this request.
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
    # --- CHANGED: now reads the 5 new filter query params (subcategory,
    # account, search, date_from, date_to) in addition to the existing
    # category/month/payment, and passes all 8 through to the upgraded
    # filter_transactions() service function as keyword args.
    data = filter_transactions(
        current_user.id,
        category=request.args.get("category"),
        subcategory=request.args.get("subcategory"),
        account=request.args.get("account"),
        payment=request.args.get("payment"),
        month=request.args.get("month"),
        search=request.args.get("search"),
        date_from=request.args.get("date_from"),
        date_to=request.args.get("date_to"),
    )

    # --- NEW: categories (each with its nested list of subcategories)
    # are fetched so the template can render the Category dropdown and
    # build the cascading Subcategory dropdown (subcategories scoped to
    # whichever category is selected) without any hardcoded option list.
    categories = get_all_categories(current_user.id)

    # --- NEW: the distinct accounts this user has actually transacted
    # with, used to populate the Account filter dropdown.
    accounts = get_user_accounts(current_user.id)

    return render_template(
        "filter_transaction.html",
        data=data,
        categories=categories,
        accounts=accounts
    )