from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
import time
from flask_login import current_user, login_required, login_user, logout_user

from game_data import DEFAULT_SLOT_COUNT
from models import User


auth_bp = Blueprint("auth", __name__)

# Simple in-memory rate limiter: keys are `user:<username>` or `ip:<remote_addr>`
FAILED_LOGINS: dict = {}
RATE_LIMIT = 5
RATE_WINDOW = 300  # seconds


def _login_identifier():
    username = request.form.get("username", "").strip()
    if username:
        return f"user:{username}"
    return f"ip:{request.remote_addr or 'unknown'}"


def _is_blocked(key: str) -> bool:
    entry = FAILED_LOGINS.get(key)
    if not entry:
        return False
    now = time.time()
    first = entry.get("first", now)
    blocked_until = entry.get("blocked_until")
    if blocked_until and now < blocked_until:
        return True
    if now - first > RATE_WINDOW:
        # window expired -> reset
        FAILED_LOGINS.pop(key, None)
        return False
    if entry.get("count", 0) >= RATE_LIMIT:
        # set a block period
        entry["blocked_until"] = now + RATE_WINDOW
        return True
    return False


def _blocked_remaining(key: str) -> int:
    """Return remaining block seconds for `key`, or 0 if not blocked."""
    entry = FAILED_LOGINS.get(key)
    if not entry:
        return 0
    blocked_until = entry.get("blocked_until")
    if not blocked_until:
        return 0
    rem = int(max(0, blocked_until - time.time()))
    return rem


def _register_failure(key: str) -> None:
    now = time.time()
    entry = FAILED_LOGINS.get(key)
    if not entry:
        FAILED_LOGINS[key] = {"count": 1, "first": now, "blocked_until": None}
        return
    if now - entry.get("first", now) > RATE_WINDOW:
        FAILED_LOGINS[key] = {"count": 1, "first": now, "blocked_until": None}
    else:
        entry["count"] = entry.get("count", 0) + 1
        if entry["count"] >= RATE_LIMIT:
            entry["blocked_until"] = now + RATE_WINDOW


def _register_success(key: str) -> None:
    FAILED_LOGINS.pop(key, None)


def get_db():
    return current_app.config["db"]


def create_default_slots(user):
    database = get_db()
    database.create_default_slots(user.id, DEFAULT_SLOT_COUNT)
    database.add_action_log(user.id, "Conta criada com recursos iniciais.")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("game.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        database = get_db()

        if not username or not email or not password:
            flash("Preenche username, email e password.", "error")
            return render_template("register.html")

        if len(password) < 4:
            flash("A password tem de ter pelo menos 4 caracteres.", "error")
            return render_template("register.html")

        if database.get_user_by_username(username):
            flash("Esse username já existe.", "error")
            return render_template("register.html")

        if database.get_user_by_email(email):
            flash("Esse email já existe.", "error")
            return render_template("register.html")

        user = database.create_user(username, email, password)
        create_default_slots(user)
        login_user(user)
        return redirect(url_for("game.dashboard"))

    return render_template("register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("game.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        key = _login_identifier()
        if _is_blocked(key):
            rem = _blocked_remaining(key)
            if rem >= 60:
                mins = rem // 60
                flash(f"Muitas tentativas falhadas. Tenta novamente daqui a {mins} minutos.", "error")
            else:
                flash(f"Muitas tentativas falhadas. Tenta novamente daqui a {rem} segundos.", "error")
            return render_template("login.html")

        user = get_db().get_user_by_username(username)

        if user is None or not user.check_password(password):
            _register_failure(key)
            flash("Credenciais inválidas.", "error")
            return render_template("login.html")

        # Success -> clear failures
        _register_success(key)
        login_user(user)
        return redirect(url_for("game.dashboard"))

    return render_template("login.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
