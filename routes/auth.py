"""Authentication routes for Student AI Assistant (StudyBuddy).

Handles registration, login, logout, and session state.
"""

from functools import wraps
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
)
from database.db import db
from models.user import User

auth_bp = Blueprint("auth", __name__)


def login_required(f):
    """Decorator to protect routes requiring student authentication."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required. Please log in."}), 401
            flash("Please log in to access your StudyBuddy account.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


def get_current_user():
    """Retrieve the currently authenticated User instance using SQLAlchemy 2.0 API."""
    user_id = session.get("user_id")
    if user_id:
        return db.session.get(User, user_id)
    return None


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Register a new student account."""
    if "user_id" in session and not request.is_json and request.method == "GET":
        return redirect(url_for("dashboard.dashboard_view"))

    if request.method == "POST":
        # Handle both JSON API and HTML form submissions
        if request.is_json:
            data = request.get_json() or {}
            username = data.get("username", "").strip()
            email = data.get("email", "").strip().lower()
            password = data.get("password", "")
            full_name = data.get("full_name", "").strip()
        else:
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            full_name = request.form.get("full_name", "").strip()

        # Validation
        if not username or len(username) < 3:
            msg = "Username must be at least 3 characters long."
            if request.is_json:
                return jsonify({"error": msg}), 400
            flash(msg, "danger")
            return render_template("register.html", username=username, email=email, full_name=full_name)

        if not email or "@" not in email:
            msg = "Please provide a valid email address."
            if request.is_json:
                return jsonify({"error": msg}), 400
            flash(msg, "danger")
            return render_template("register.html", username=username, email=email, full_name=full_name)

        if not password or len(password) < 6:
            msg = "Password must be at least 6 characters long."
            if request.is_json:
                return jsonify({"error": msg}), 400
            flash(msg, "danger")
            return render_template("register.html", username=username, email=email, full_name=full_name)

        # Check existing username / email
        if User.query.filter_by(username=username).first():
            msg = "Username is already taken. Please choose another."
            if request.is_json:
                return jsonify({"error": msg}), 409
            flash(msg, "danger")
            return render_template("register.html", username=username, email=email, full_name=full_name)

        if User.query.filter_by(email=email).first():
            msg = "An account with this email already exists."
            if request.is_json:
                return jsonify({"error": msg}), 409
            flash(msg, "danger")
            return render_template("register.html", username=username, email=email, full_name=full_name)

        # Create user
        user = User(
            username=username,
            email=email,
            full_name=full_name or username,
        )
        user.set_password(password)

        try:
            db.session.add(user)
            db.session.commit()

            # Auto-login after registration
            session["user_id"] = user.id
            session["username"] = user.username
            session["full_name"] = user.full_name

            if request.is_json:
                return jsonify({"message": "Registration successful!", "user": user.to_dict()}), 201

            flash(f"Welcome to StudyBuddy, {user.full_name}! Your account is ready.", "success")
            return redirect(url_for("dashboard.dashboard_view"))
        except Exception as e:
            db.session.rollback()
            msg = f"Registration error: {str(e)}"
            if request.is_json:
                return jsonify({"error": msg}), 500
            flash(msg, "danger")

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate student with username/email and password."""
    if "user_id" in session and not request.is_json and request.method == "GET":
        return redirect(url_for("dashboard.dashboard_view"))

    if request.method == "POST":
        if request.is_json:
            data = request.get_json() or {}
            identifier = data.get("identifier", "").strip()
            password = data.get("password", "")
        else:
            identifier = request.form.get("identifier", "").strip()
            password = request.form.get("password", "")

        if not identifier or not password:
            msg = "Please provide both your username/email and password."
            if request.is_json:
                return jsonify({"error": msg}), 400
            flash(msg, "danger")
            return render_template("login.html", identifier=identifier)

        # Lookup by username or email
        user = User.query.filter(
            (User.username == identifier) | (User.email == identifier.lower())
        ).first()

        if not user or not user.check_password(password):
            msg = "Invalid username/email or password."
            if request.is_json:
                return jsonify({"error": msg}), 401
            flash(msg, "danger")
            return render_template("login.html", identifier=identifier)

        # Set session
        session["user_id"] = user.id
        session["username"] = user.username
        session["full_name"] = user.full_name

        if request.is_json:
            return jsonify({"message": "Login successful!", "user": user.to_dict()}), 200

        flash(f"Welcome back, {user.full_name}!", "success")
        next_page = request.args.get("next")
        if next_page and not next_page.startswith("//") and not next_page.startswith("http"):
            return redirect(next_page)
        return redirect(url_for("dashboard.dashboard_view"))

    return render_template("login.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Clear student session."""
    session.clear()
    flash("You have been securely logged out.", "info")
    return redirect(url_for("auth.login"))
