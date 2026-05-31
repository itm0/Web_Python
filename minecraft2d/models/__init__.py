from flask import current_app

from extensions import login_manager

from .database import ActionLog, BuildingSlot, Database, Stone, Tree, User


@login_manager.user_loader
def load_user(user_id):
    database = current_app.config["db"]
    return database.get_user_by_id(int(user_id))
