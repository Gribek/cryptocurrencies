import os

from peewee import SqliteDatabase

from settings import DATABASE


class DatabaseConnection:
    """Connect to the database.

    The connection method is selected based on the DATABASE
    setting in settings.py file.
    """

    @classmethod
    def connect(cls):
        """Connect and return the database object."""
        connection = getattr(cls, DATABASE['connection'])
        return connection(**DATABASE['parameters'])

    @staticmethod
    def sqlite_connection(path, filename):
        """Prepare a connection to the selected SQLite database."""
        return SqliteDatabase(database=os.path.join(path, filename),
                              pragmas={'foreign_keys': 1})
