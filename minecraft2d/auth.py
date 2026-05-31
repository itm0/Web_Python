from flask import current_app, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from models import Database, User


def get_db():
    return current_app.config["db"]


def create_default_slots(user):
    database = get_db()
    database.create_default_slots(user.id, Database.DEFAULT_SLOT_COUNT)
    database.add_action_log(user.id, "Conta criada com recursos iniciais.")


def register():
    messages = []

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        database = get_db()

        if not username or not email or not password:
            messages.append(("error", "Preenche username, email e password."))
            return render_template("register.html", messages=messages, is_logged_in=False)

        if len(password) < 4:
            messages.append(("error", "A password tem de ter pelo menos 4 caracteres."))
            return render_template("register.html", messages=messages, is_logged_in=False)

        if database.get_user_by_username(username):
            messages.append(("error", "Esse username já existe."))
            return render_template("register.html", messages=messages, is_logged_in=False)

        if database.get_user_by_email(email):
            messages.append(("error", "Esse email já existe."))
            return render_template("register.html", messages=messages, is_logged_in=False)

        user = database.create_user(username, email, password)
        create_default_slots(user)
        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("register.html", messages=messages, is_logged_in=False)


def login():
    messages = []

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = get_db().get_user_by_username(username)

        if user is None or not user.check_password(password):
            messages.append(("error", "Credenciais inválidas."))
            return render_template("login.html", messages=messages, is_logged_in=False)

        login_user(user)
        return redirect(url_for("dashboard"))

    return render_template("login.html", messages=messages, is_logged_in=False)


@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))
