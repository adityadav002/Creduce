from datetime import datetime

from flask import Blueprint, render_template, request, send_file
from flask_login import login_required, current_user

from services.transaction_service import (
    get_transaction_history,
    monthly_transaction_details,
    filter_transactions,
    get_user_accounts,  # NEW: powers the Account filter dropdown
    get_report_preview,  # NEW: Download Report preview summary
    generate_excel_report,  # NEW: Download Report - Excel export
    generate_csv_report  # NEW: Download Report - CSV export
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


# ============================================================
# NEW: Download Report routes
# ============================================================

@transaction_bp.route("/download_report")
@login_required
def download_report():
    # --- NEW: reads the 6 report filters straight from the
    # querystring, the same way the other filtered pages above do.
    month = request.args.get("month")
    year = request.args.get("year")
    category = request.args.get("category")
    subcategory = request.args.get("subcategory")
    account = request.args.get("account")
    payment = request.args.get("payment")

    # --- NEW: categories (with nested subcategories) and the user's
    # accounts, used to populate the Category/Subcategory cascading
    # dropdown and the Account dropdown on download_report.html.
    categories = get_all_categories(current_user.id)
    accounts = get_user_accounts(current_user.id)

    # --- NEW: dynamic year list for the Year dropdown.
    current_year = datetime.now().year
    years = list(range(current_year - 3, current_year + 2))

    # --- NEW: preview summary (total transactions, total expense, top
    # category/account/payment method) for the currently selected
    # filters.
    preview = get_report_preview(
        current_user.id,
        month,
        year,
        category,
        subcategory,
        account,
        payment
    )

    return render_template(
        "download_report.html",
        preview=preview,
        categories=categories,
        accounts=accounts,
        years=years,
        selected_month=month,
        selected_year=year,
        selected_category=category,
        selected_subcategory=subcategory,
        selected_account=account,
        selected_payment=payment
    )


@transaction_bp.route("/download_report/excel")
@login_required
def download_report_excel():
    # --- NEW: same 6 filters as /download_report, read identically.
    month = request.args.get("month")
    year = request.args.get("year")
    category = request.args.get("category")
    subcategory = request.args.get("subcategory")
    account = request.args.get("account")
    payment = request.args.get("payment")

    buffer = generate_excel_report(
        current_user.id,
        month,
        year,
        category,
        subcategory,
        account,
        payment
    )

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Expense_Report_{month}_{year}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@transaction_bp.route("/download_report/csv")
@login_required
def download_report_csv():
    # --- NEW: same 6 filters as /download_report, read identically.
    month = request.args.get("month")
    year = request.args.get("year")
    category = request.args.get("category")
    subcategory = request.args.get("subcategory")
    account = request.args.get("account")
    payment = request.args.get("payment")

    buffer = generate_csv_report(
        current_user.id,
        month,
        year,
        category,
        subcategory,
        account,
        payment
    )

    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"Expense_Report_{month}_{year}.csv",
        mimetype="text/csv"
    )