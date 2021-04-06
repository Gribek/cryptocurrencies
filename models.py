from peewee import *

from db_connection import sqlite_connection
from settings import DB_FILENAME, DB_PATH

db = sqlite_connection(DB_PATH, DB_FILENAME)


class BaseModel(Model):
    """Base model class that specifies the database."""

    class Meta:
        database = db

    @classmethod
    def get_data_in_range(cls, column, lower, upper, condition=None):
        """Return data within the given range."""
        attr = getattr(cls, column)
        if condition:
            cond_attr = getattr(cls, condition['column'])
            return cls.select().where(
                (cond_attr == condition['value']) &
                (attr.between(lower, upper))).order_by(attr)
        return cls.select().where(attr.between(lower, upper)).order_by(attr)


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

    def to_file(self, price_column, precision=2):
        """Prepare a dictionary with object data."""
        price = getattr(self, price_column)
        return {'date': str(self.date),
                'price': round(float(price), precision)}


# Initialize database and create tables
if __name__ == '__main__':
    db.connect(reuse_if_open=True)
    db.create_tables([Cryptocurrency, HistoricalValue])
    db.close()
