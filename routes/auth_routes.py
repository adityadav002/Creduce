from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_user, logout_user

from models.user import User
from services.auth_service import (
    register_user,
    authenticate_user
)

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        success = register_user(
            request.form["name"],
            request.form["email"],
            request.form["password"]
        )

        if success:
            return redirect("/login")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        user_data = authenticate_user(
            request.form["email"],
            request.form["password"]
        )

        if user_data:
            login_user(User(user_data[0]))
            return redirect("/")

        return redirect(url_for("auth.login"))

    return render_template("login.html")


@auth_bp.route("/logout")
def logout():

    logout_user()

    return redirect("/login")