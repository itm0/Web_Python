import os
import sqlite3

from datetime import datetime

from flask_login import UserMixin
from passlib.hash import pbkdf2_sha256 as hasher


def _parse_datetime(value):
    if value is None or value == "":
        return None
    if type(value) == datetime:
        return value
    parts = value.split("T")
    date_parts = parts[0].split("-")
    time_parts = parts[1].split(":") if len(parts) > 1 else ["0", "0", "0"]
    return datetime(
        int(date_parts[0]),
        int(date_parts[1]),
        int(date_parts[2]),
        int(time_parts[0]),
        int(time_parts[1]),
        int(time_parts[2]) if len(time_parts) > 2 else 0,
    )


def _format_datetime(value):
    if value is None:
        return None
    if type(value) == str:
        return value
    return "%04d-%02d-%02dT%02d:%02d:%02d" % (value.year, value.month, value.day, value.hour, value.minute, value.second)


class User(UserMixin):
    def __init__(self, id, username, email, password_hash, wood=26, stone=26, created_at=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.wood = wood
        self.stone = stone
        self.created_at = created_at

    def set_password(self, password):
        self.password_hash = hasher.hash(password)

    def check_password(self, password):
        return hasher.verify(password, self.password_hash)

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return cls(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            password_hash=row["password_hash"],
            wood=row["wood"],
            stone=row["stone"],
            created_at=_parse_datetime(row["created_at"]),
        )


class BuildingSlot:
    def __init__(self, id, user_id, slot_number, building_type=None, state="empty", action_type=None, started_at=None, ready_at=None, created_at=None):
        self.id = id
        self.user_id = user_id
        self.slot_number = slot_number
        self.building_type = building_type
        self.state = state
        self.action_type = action_type
        self.started_at = started_at
        self.ready_at = ready_at
        self.created_at = created_at

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            slot_number=row["slot_number"],
            building_type=row["building_type"],
            state=row["state"],
            action_type=row["action_type"],
            started_at=_parse_datetime(row["started_at"]),
            ready_at=_parse_datetime(row["ready_at"]),
            created_at=_parse_datetime(row["created_at"]),
        )


class ActionLog:
    def __init__(self, id, user_id, message, created_at=None):
        self.id = id
        self.user_id = user_id
        self.message = message
        self.created_at = created_at

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            message=row["message"],
            created_at=_parse_datetime(row["created_at"]),
        )


class Tree:
    def __init__(self, id, column, chopped_at=None, removed_at=None, created_at=None):
        self.id = id
        self.column = column
        self.chopped_at = chopped_at
        self.removed_at = removed_at
        self.created_at = created_at

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return cls(
            id=row["id"],
            column=row["column"],
            chopped_at=_parse_datetime(row["chopped_at"]),
            removed_at=_parse_datetime(row["removed_at"]),
            created_at=_parse_datetime(row["created_at"]),
        )


class Stone:
    def __init__(self, id, column, mined_at=None, removed_at=None, created_at=None):
        self.id = id
        self.column = column
        self.mined_at = mined_at
        self.removed_at = removed_at
        self.created_at = created_at

    @classmethod
    def from_row(cls, row):
        if row is None:
            return None
        return cls(
            id=row["id"],
            column=row["column"],
            mined_at=_parse_datetime(row["mined_at"]),
            removed_at=_parse_datetime(row["removed_at"]),
            created_at=_parse_datetime(row["created_at"]),
        )


class Database:
    def __init__(self, dbfile):
        self.dbfile = dbfile
        directory = os.path.dirname(dbfile)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self.create_table()

    def _connect(self):
        connection = sqlite3.connect(self.dbfile)
        connection.row_factory = sqlite3.Row

        return connection

    def create_table(self):
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username VARCHAR(80) NOT NULL UNIQUE,
                    email VARCHAR(120) NOT NULL UNIQUE,
                    password_hash VARCHAR(255) NOT NULL,
                    wood INTEGER NOT NULL DEFAULT 26,
                    stone INTEGER NOT NULL DEFAULT 26,
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS building_slots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    slot_number INTEGER NOT NULL,
                    building_type VARCHAR(40),
                    state VARCHAR(20) NOT NULL DEFAULT 'empty',
                    action_type VARCHAR(40),
                    started_at TEXT,
                    ready_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE (user_id, slot_number)
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS action_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message VARCHAR(255) NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS trees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    column INTEGER NOT NULL UNIQUE,
                    chopped_at TEXT,
                    removed_at TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS stones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    column INTEGER NOT NULL UNIQUE,
                    mined_at TEXT,
                    removed_at TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            for column in (2, 5, 9):
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO trees (column, created_at)
                    VALUES (?, ?)
                    """,
                    (column, _format_datetime(datetime.utcnow())),
                )
            for column in (1, 4, 7, 10):
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO stones (column, created_at)
                    VALUES (?, ?)
                    """,
                    (column, _format_datetime(datetime.utcnow())),
                )
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS buildings (
                    key VARCHAR(40) PRIMARY KEY,
                    name VARCHAR(80) NOT NULL,
                    cost_wood INTEGER NOT NULL,
                    cost_stone INTEGER NOT NULL,
                    construction_seconds INTEGER NOT NULL,
                    task_name VARCHAR(80) NOT NULL,
                    task_seconds INTEGER NOT NULL,
                    reward_wood INTEGER NOT NULL DEFAULT 0,
                    reward_stone INTEGER NOT NULL DEFAULT 0,
                    description VARCHAR(255)
                )
                """
            )
            cursor.execute(
                "INSERT OR IGNORE INTO buildings VALUES ('cabana','Cabana',15,5,20,'Recolher madeira',20,8,0,'Produz madeira e mantém a aldeia viva.')"
            )
            cursor.execute(
                "INSERT OR IGNORE INTO buildings VALUES ('mina','Mina',10,15,25,'Minerar pedra',25,0,10,'Gera pedra para novas construções.')"
            )
            cursor.execute(
                "INSERT OR IGNORE INTO buildings VALUES ('forja','Forja',20,10,30,'Reforjar ferramentas',30,4,4,'Equilibra madeira e pedra em progresso.')"
            )
            self.drop_legacy_tables(cursor)
            connection.commit()

    def drop_legacy_tables(self, cursor):
        for table_name in ("action_log", "building_slot", "stone", "tree", "user"):
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

    def create_user(self, username, email, password):
        password_hash = hasher.hash(password)
        created_at = _format_datetime(datetime.utcnow())
        with self._connect() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, wood, stone, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (username, email, password_hash, 26, 26, created_at),
            )
            connection.commit()
            return self.get_user_by_id(cursor.lastrowid)

    def get_user_by_id(self, user_id):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return User.from_row(row)

    def get_user_by_username(self, username):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        return User.from_row(row)

    def get_user_by_email(self, email):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,),
            ).fetchone()
        return User.from_row(row)

    def update_user(self, user):
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE users
                SET username = ?, email = ?, password_hash = ?, wood = ?, stone = ?
                WHERE id = ?
                """,
                (user.username, user.email, user.password_hash, user.wood, user.stone, user.id),
            )
            connection.commit()

    def update_user_resources(self, user):
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE users
                SET wood = ?, stone = ?
                WHERE id = ?
                """,
                (user.wood, user.stone, user.id),
            )
            connection.commit()

    def create_default_slots(self, user_id, slot_count):
        with self._connect() as connection:
            cursor = connection.cursor()
            for slot_number in range(1, slot_count + 1):
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO building_slots (
                        user_id, slot_number, building_type, state, action_type,
                        started_at, ready_at, created_at
                    )
                    VALUES (?, ?, NULL, 'empty', NULL, NULL, NULL, ?)
                    """,
                    (user_id, slot_number, _format_datetime(datetime.utcnow())),
                )
            connection.commit()

    def list_user_slots(self, user_id):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM building_slots
                WHERE user_id = ?
                ORDER BY slot_number
                """,
                (user_id,),
            ).fetchall()
        return [BuildingSlot.from_row(row) for row in rows]

    def get_slot(self, slot_id, user_id=None):
        query = "SELECT * FROM building_slots WHERE id = ?"
        params = [slot_id]
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        return BuildingSlot.from_row(row)

    def update_slot(self, slot):
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE building_slots
                SET user_id = ?, slot_number = ?, building_type = ?, state = ?,
                    action_type = ?, started_at = ?, ready_at = ?, created_at = ?
                WHERE id = ?
                """,
                (
                    slot.user_id,
                    slot.slot_number,
                    slot.building_type,
                    slot.state,
                    slot.action_type,
                    _format_datetime(slot.started_at),
                    _format_datetime(slot.ready_at),
                    _format_datetime(slot.created_at),
                    slot.id,
                ),
            )
            connection.commit()

    def add_action_log(self, user_id, message):
        created_at = _format_datetime(datetime.utcnow())
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO action_logs (user_id, message, created_at)
                VALUES (?, ?, ?)
                """,
                (user_id, message, created_at),
            )
            connection.commit()

    def get_buildings(self):
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM buildings ORDER BY key"
            ).fetchall()
        result = {}
        for row in rows:
            result[row["key"]] = {
                "name": row["name"],
                "cost_wood": row["cost_wood"],
                "cost_stone": row["cost_stone"],
                "construction_seconds": row["construction_seconds"],
                "task_name": row["task_name"],
                "task_seconds": row["task_seconds"],
                "reward_wood": row["reward_wood"],
                "reward_stone": row["reward_stone"],
                "description": row["description"],
            }
        return result

    def get_building(self, key):
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM buildings WHERE key = ?", (key,)
            ).fetchone()
        if row is None:
            return None
        return {
            "name": row["name"],
            "cost_wood": row["cost_wood"],
            "cost_stone": row["cost_stone"],
            "construction_seconds": row["construction_seconds"],
            "task_name": row["task_name"],
            "task_seconds": row["task_seconds"],
            "reward_wood": row["reward_wood"],
            "reward_stone": row["reward_stone"],
            "description": row["description"],
        }

    def list_action_logs(self, user_id, limit=8):
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM action_logs
                WHERE user_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [ActionLog.from_row(row) for row in rows]

    def ensure_trees(self):
        with self._connect() as connection:
            cursor = connection.cursor()
            for column in (2, 5, 9):
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO trees (column, created_at)
                    VALUES (?, ?)
                    """,
                    (column, _format_datetime(datetime.utcnow())),
                )
            connection.commit()

    def ensure_stones(self):
        with self._connect() as connection:
            cursor = connection.cursor()
            for column in (1, 4, 7, 10):
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO stones (column, created_at)
                    VALUES (?, ?)
                    """,
                    (column, _format_datetime(datetime.utcnow())),
                )
            connection.commit()

    DEFAULT_SLOT_COUNT = 4

    def list_trees(self, include_removed=False):
        query = "SELECT * FROM trees"
        params = []
        if not include_removed:
            query += " WHERE removed_at IS NULL"
        query += " ORDER BY column"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [Tree.from_row(row) for row in rows]

    def list_stones(self, include_removed=False):
        query = "SELECT * FROM stones"
        params = []
        if not include_removed:
            query += " WHERE removed_at IS NULL"
        query += " ORDER BY column"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [Stone.from_row(row) for row in rows]

    def get_tree_by_column(self, column, include_removed=False):
        query = "SELECT * FROM trees WHERE column = ?"
        params = [column]
        if not include_removed:
            query += " AND removed_at IS NULL"
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        return Tree.from_row(row)

    def get_stone_by_column(self, column, include_removed=False):
        query = "SELECT * FROM stones WHERE column = ?"
        params = [column]
        if not include_removed:
            query += " AND removed_at IS NULL"
        with self._connect() as connection:
            row = connection.execute(query, params).fetchone()
        return Stone.from_row(row)

    def update_tree(self, tree):
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE trees
                SET column = ?, chopped_at = ?, removed_at = ?, created_at = ?
                WHERE id = ?
                """,
                (
                    tree.column,
                    _format_datetime(tree.chopped_at),
                    _format_datetime(tree.removed_at),
                    _format_datetime(tree.created_at),
                    tree.id,
                ),
            )
            connection.commit()

    def update_stone(self, stone):
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE stones
                SET column = ?, mined_at = ?, removed_at = ?, created_at = ?
                WHERE id = ?
                """,
                (
                    stone.column,
                    _format_datetime(stone.mined_at),
                    _format_datetime(stone.removed_at),
                    _format_datetime(stone.created_at),
                    stone.id,
                ),
            )
            connection.commit()
