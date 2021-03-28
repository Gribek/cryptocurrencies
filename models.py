from peewee import *

from db_connection import sqlite_connection
from settings import DB_FILENAME, DB_PATH

db = sqlite_connection(DB_PATH, DB_FILENAME)


class BaseModel(Model):
    """Base model class that specifies the database."""

    class Meta:
        database = db


class Cryptocurrency(BaseModel):
    """Represent a single cryptocurrency."""
    currency_name = TextField(unique=True)


class HistoricalValue(BaseModel):
    """Represent currency OHLC values for one day."""
    date = DateField()
    open = DecimalField(max_digits=10, decimal_places=4)
    close = DecimalField(max_digits=10, decimal_places=4)
    high = DecimalField(max_digits=10, decimal_places=4)
    low = DecimalField(max_digits=10, decimal_places=4)
    currency = ForeignKeyField(Cryptocurrency, backref='historical_values',
                               on_delete='CASCADE')


# Initialize database and create tables
if __name__ == '__main__':
    db.connect(reuse_if_open=True)
    db.create_tables([Cryptocurrency, HistoricalValue])
    db.close()
