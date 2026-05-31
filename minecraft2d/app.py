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

from auth import login, logout, register
from game import api_build, api_chop, api_inventory_remove, api_mine_stone, api_state, api_task_collect, api_task_start, dashboard

app.add_url_rule("/", view_func=dashboard)
app.add_url_rule("/dashboard", view_func=dashboard)
app.add_url_rule("/api/state", view_func=api_state)
app.add_url_rule("/api/build/<int:slot_id>", view_func=api_build, methods=["POST"])
app.add_url_rule("/api/task/<int:slot_id>/start", view_func=api_task_start, methods=["POST"])
app.add_url_rule("/api/task/<int:slot_id>/collect", view_func=api_task_collect, methods=["POST"])
app.add_url_rule("/api/chop", view_func=api_chop, methods=["POST"])
app.add_url_rule("/api/mine-stone", view_func=api_mine_stone, methods=["POST"])
app.add_url_rule("/api/inventory/remove", view_func=api_inventory_remove, methods=["POST"])
app.add_url_rule("/register", view_func=register, methods=["GET", "POST"])
app.add_url_rule("/login", view_func=login, methods=["GET", "POST"])
app.add_url_rule("/logout", view_func=logout, methods=["GET", "POST"])

if __name__ == "__main__":
    app.run(debug=False, host="127.0.0.1", port=8000)
