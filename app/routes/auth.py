from datetime import datetime
import secrets

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models import User


auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET"])
def index():
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        login_input = request.form.get("login_input", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            (User.username == login_input) | (User.email == login_input)
        ).first()

        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["username"] = user.username
            flash("Welcome back to StocVue.", "success")
            return redirect(url_for("main.dashboard"))

        flash("Invalid username/email or password.", "error")

    return render_template("login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return render_template("register.html")

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already exists.", "error")
            return render_template("register.html")

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
        )
        db.session.add(user)
        db.session.commit()

        session["user_id"] = user.id
        session["username"] = user.username
        flash("Account created successfully.", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("register.html")


@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    email = request.args.get("email")
    submitted = False

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        otp_input = request.form.get("otp", "").strip()
        new_password = request.form.get("new_password", "")
        user = User.query.filter_by(email=email).first()

        if user is None:
            flash("No account found with that email.", "error")
            return render_template("reset_password.html", email=email)

        if request.form.get("action") == "request_otp":
            otp = str(secrets.randbelow(900000) + 100000)
            user.otp_code = otp
            user.otp_created_at = datetime.utcnow()
            db.session.commit()
            flash(f"Demo OTP sent: {otp}. Use it to reset your password.", "info")
            submitted = True
            return render_template("reset_password.html", email=email, otp_sent=True)

        if not otp_input or not new_password:
            flash("Please enter the OTP and a new password.", "error")
            return render_template("reset_password.html", email=email, otp_sent=True)

        if user.otp_code is None or user.otp_code != otp_input:
            flash("The OTP you entered is invalid.", "error")
            return render_template("reset_password.html", email=email, otp_sent=True)

        user.password_hash = generate_password_hash(new_password)
        user.otp_code = None
        user.otp_created_at = None
        db.session.commit()
        flash("Password reset successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", email=email, otp_sent=submitted)


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
