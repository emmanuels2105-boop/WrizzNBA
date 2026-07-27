import sqlite3

import pytest

from pipeline.db.connection import init_db


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    connection.row_factory = sqlite3.Row
    init_db(connection)
    yield connection
    connection.close()
