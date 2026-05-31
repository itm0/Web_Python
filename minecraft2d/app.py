import os
import shutil

from flask import Flask
from flask_login import current_user

from extensions import login_manager
from models import Database


class Config:
    SECRET_KEY = "dev-minecraft-2d"


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
        return {"current_game_user": current_user}

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    app.run(debug=True, host="127.0.0.1", port=port)
