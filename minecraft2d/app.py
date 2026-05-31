import os
import secrets
import shutil

from flask import Flask, abort, request, session
from flask_login import current_user

from extensions import login_manager
from models import Database


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-minecraft-2d")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(app.instance_path, exist_ok=True)

    models_dir = os.path.join(os.path.dirname(__file__), "models")
    database_path = os.path.join(models_dir, "minecraft2d.sqlite")
    legacy_database_path = os.path.join(app.instance_path, "minecraft2d.db")

    if not os.path.exists(database_path) and os.path.exists(legacy_database_path):
        shutil.copy2(legacy_database_path, database_path)

    database = Database(database_path)
    app.config["db"] = database
    login_manager.init_app(app)

    from auth import auth_bp
    from game import game_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(game_bp)

    @app.context_processor
    def inject_user():
        return {"current_game_user": current_user, "csrf_token": generate_csrf_token}

    @app.before_request
    def protect_mutating_requests():
        if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
            return None

        token = request.form.get("_csrf_token") or request.headers.get("X-CSRF-Token")
        if not token or token != session.get("_csrf_token"):
            abort(400)

        return None

    return app


def generate_csrf_token():
    token = session.get("_csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(debug=debug, host="127.0.0.1", port=port)
