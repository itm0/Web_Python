import os

from flask import Flask

from extensions import login_manager
from models import Database


app = Flask(__name__)
app.config["SECRET_KEY"] = "dev-minecraft-2d"

models_dir = os.path.join(os.path.dirname(__file__), "models")
database_path = os.path.join(models_dir, "minecraft2d.sqlite")
database = Database(database_path)
app.config["db"] = database
login_manager.init_app(app)

# Blueprint agrupa rotas em ficheiros separados (ex: auth.py, game.py).
from auth import auth_bp
from game import game_bp

app.register_blueprint(auth_bp)
app.register_blueprint(game_bp)

if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8000)
