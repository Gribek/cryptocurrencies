from string import Template

# DATABASE
# Database filename
DB_FILENAME = 'crypto.db'

# Relative path to the database file directory
DB_PATH = 'db'


# API
# url for historical OHLC
HISTORICAL_URL = Template(
    'https://api.coinpaprika.com/v1/coins/$coin/ohlcv/historical')

# Maximum number of rows in one request (due to API limit)
ROWS_LIMIT = 360


# API DATA MODIFICATIONS
# Configuration of the modifications to be performed on API data before
# they can be saved in the database

# Modifications for HistoricalValue model
HISTORICAL_MODIFICATIONS = (
    {
        'function': 'format_date',
        'args': ('time_close', 'date', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d')
    },
)
