from flask import Blueprint, render_template, request, redirect
from flask_login import login_required, current_user

from services.expense_service import (
    add_expense,
    delete_expense,
    update_expense,
    get_expense_by_id
)
from services.account_service import get_all_accounts
from services.category_service import get_all_categories

expense_bp = Blueprint("expense", __name__)


@expense_bp.route("/addExpense", methods=["GET", "POST"])
@login_required
def add_expense_route():

    if request.method == "POST":

        # Sanitize: treat empty strings as None
        category_val = request.form.get("category") or None
        subcategory_val = request.form.get("subcategory_id") or None
        new_subcategory = request.form.get("new_subcategory", "").strip()

        add_expense(
            current_user.id,
            request.form["account_id"],
            request.form["exp_date"],
            float(request.form["amount"]),
            request.form.get("note", "").lower(),
            request.form["payment"],
            category_val,
            subcategory_val,
            new_subcategory
        )

        return redirect("/")

    accounts = get_all_accounts(current_user.id)
    categories = get_all_categories(current_user.id)
    return render_template("addExpense.html", accounts=accounts, categories=categories)


@expense_bp.route("/deleteExpense", methods=["POST"])
@login_required
def delete_expense_route():

    delete_expense(
        request.form["id"],
        current_user.id
    )

    return redirect("/")


@expense_bp.route("/editExpense/<int:id>")
@login_required
def edit_expense(id):

    expense = get_expense_by_id(
        id,
        current_user.id
    )
    
    accounts = get_all_accounts(current_user.id)
    categories = get_all_categories(current_user.id)

    return render_template(
        "editExpense.html",
        expense=expense,
        accounts=accounts,
        categories=categories
    )


@expense_bp.route("/updateExpense", methods=["POST"])
@login_required
def update_expense_route():

    # Sanitize: treat empty strings as None
    category_val = request.form.get("category") or None
    subcategory_val = request.form.get("subcategory_id") or None
    new_subcategory = request.form.get("new_subcategory", "").strip()

    update_expense(
        request.form["id"],
        current_user.id,
        request.form["account_id"],
        request.form["exp_date"],
        category_val,
        float(request.form["amount"]),
        request.form["note"],
        request.form["payment"],
        subcategory_val,
        new_subcategory
    )

    return redirect("/")