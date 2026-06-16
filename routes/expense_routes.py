from flask import Blueprint, render_template, request, redirect
from flask_login import login_required, current_user

from services.expense_service import (
    add_expense,
    delete_expense,
    update_expense,
    get_expense_by_id
)

expense_bp = Blueprint("expense", __name__)


@expense_bp.route("/addExpense", methods=["GET", "POST"])
@login_required
def add_expense_route():

    if request.method == "POST":

        add_expense(
            current_user.id,
            request.form["exp_date"],
            float(request.form["amount"]),
            request.form.get("note", "").lower(),
            request.form["payment"],
            request.form.get("category")
        )

        return redirect("/")

    return render_template("addExpense.html")


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

    return render_template(
        "editExpense.html",
        expense=expense
    )


@expense_bp.route("/updateExpense", methods=["POST"])
@login_required
def update_expense_route():

    update_expense(
        request.form["id"],
        current_user.id,
        request.form["exp_date"],
        request.form["category"],
        request.form["amount"],
        request.form["note"],
        request.form["payment"]
    )

    return redirect("/")