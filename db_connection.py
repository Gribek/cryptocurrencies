import os

from peewee import SqliteDatabase


def sqlite_connection(path, filename):
    """Prepare a connection to the selected SQLite database."""
    return SqliteDatabase(database=os.path.join(path, filename),
                          pragmas={'foreign_keys': 1})
