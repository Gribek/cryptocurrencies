from string import Template


# DATABASE
# Connection to the database
DATABASE = {
    'connection': 'sqlite_connection',
    'parameters': {
        'path': 'db',
        'filename': 'crypto.db',
    }
}


# API
# Endpoint for historical OHLC
HISTORICAL_URL = Template(
    'https://api.coinpaprika.com/v1/coins/$coin/ohlcv/historical')

# Endpoint for cryptocurrency
CRYPTOCURRENCY_URL = Template('https://api.coinpaprika.com/v1/coins/$currency')

# Maximum number of rows in one request (due to API limit)
ROWS_LIMIT = 360


# API DATA MODIFICATIONS
# Configuration of the modifications to be performed on API data before
# they can be saved in the database

# Modifications for HistoricalValue model
HISTORICAL_MODIFICATIONS = (
    {
        'function': '_format_date',
        'args': ('time_close', 'date', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d')
    },
)

# Modifications for Cryptocurrency model
CRYPTOCURRENCY_MODIFICATIONS = (
    {
        'function': '_rename',
        'args': ('id', 'currency_name')
    },
)

