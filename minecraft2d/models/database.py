from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash


def _parse_datetime(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _format_datetime(value):
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat(timespec="seconds")


@dataclass
class User(UserMixin):
    id: int
    username: str
    email: str
    password_hash: str
    wood: int = 26
    stone: int = 26
    created_at: Optional[datetime] = None

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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


@dataclass
class BuildingSlot:
    id: int
    user_id: int
    slot_number: int
    building_type: Optional[str] = None
    state: str = "empty"
    action_type: Optional[str] = None
    started_at: Optional[datetime] = None
    ready_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

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


@dataclass
class ActionLog:
    id: int
    user_id: int
    message: str
    created_at: Optional[datetime] = None

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


@dataclass
class Tree:
    id: int
    column: int
    chopped_at: Optional[datetime] = None
    removed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

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


@dataclass
class Stone:
    id: int
    column: int
    mined_at: Optional[datetime] = None
    removed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

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
        connection.execute("PRAGMA foreign_keys = ON")
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
            self.drop_legacy_tables(cursor)
            connection.commit()

    def drop_legacy_tables(self, cursor):
        for table_name in ("action_log", "building_slot", "stone", "tree", "user"):
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

    def create_user(self, username, email, password):
        password_hash = generate_password_hash(password, method="pbkdf2:sha256")
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
