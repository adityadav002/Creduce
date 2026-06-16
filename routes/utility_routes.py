from flask import Blueprint, render_template
from flask_login import login_required

utility_bp = Blueprint("utility", __name__)


@utility_bp.route("/calculator", methods=["GET", "POST"])
@login_required
def calculator():
    return render_template("calculator.html")