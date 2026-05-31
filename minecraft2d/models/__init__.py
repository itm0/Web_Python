from flask import current_app

from extensions import login_manager

from .database import ActionLog, BuildingSlot, Database, Stone, Tree, User


@login_manager.user_loader
def load_user(user_id):
    database = current_app.config.get("db")
    if database is None:
        return None
    try:
        return database.get_user_by_id(int(user_id))
    except (TypeError, ValueError):
        return None
