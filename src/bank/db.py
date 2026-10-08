"""SQLite boundary: untyped driver rows become checked, typed Python values."""

import sqlite3
from collections.abc import Generator, Sequence
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path
from types import TracebackType
from typing import Self, cast

from bank.models import BankError

type SqlValue = str | int | None
type Row = tuple[object, ...]


def integer(value: object) -> int:
    if not isinstance(value, int):
        raise BankError("Database contains an invalid integer value.")
    return value


def string(value: object) -> str:
    if not isinstance(value, str):
        raise BankError("Database contains an invalid text value.")
    return value


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection: sqlite3.Connection = sqlite3.connect(
            path, isolation_level=None
        )
        try:
            sql = """
                PRAGMA foreign_keys = ON;
            """
            self.execute(sql)
            sql = """
                PRAGMA busy_timeout = 5000;
            """
            self.execute(sql)
            sql = """
                PRAGMA user_version;
            """
            rows = self.rows(sql)
            version = integer(rows[0][0])
            if version not in (0, 2):
                raise BankError(
                    "This database uses a different schema. Use --db with a new filename."
                )
            if version == 0:
                resource = files("bank").joinpath("schema.sql")
                schema = resource.read_text(encoding="utf-8")
                script = f"""
                    BEGIN IMMEDIATE;
                    {schema}
                    PRAGMA user_version = 2;
                    COMMIT;
                """
                self.connection.executescript(script)
        except BaseException:
            if self.connection.in_transaction:
                self.connection.rollback()
            self.close()
            raise

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()

    def rows(self, sql: str, params: Sequence[SqlValue] = ()) -> list[Row]:
        # sqlite3 returns Any. Confine that driver boundary to a single cast;
        # service mappers validate every column before constructing domain records.
        cursor = self.connection.execute(sql, params)
        rows = cursor.fetchall()
        return cast("list[Row]", rows)

    def insert(self, sql: str, params: Sequence[SqlValue] = ()) -> int:
        cursor = self.connection.execute(sql, params)
        key = cursor.lastrowid
        if key is None:
            raise BankError("Database did not return an inserted record ID.")
        return key

    def execute(self, sql: str, params: Sequence[SqlValue] = ()) -> None:
        self.connection.execute(sql, params)

    @contextmanager
    def atomic(self) -> Generator[None]:
        sql = """
            BEGIN IMMEDIATE;
        """
        self.execute(sql)
        try:
            yield
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise
