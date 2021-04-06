import csv
from datetime import datetime, timedelta
from decimal import Decimal
from importlib import import_module
import json
import requests
from statistics import mean
from string import Template
import sys

from models import Cryptocurrency, HistoricalValue
from db_connection import sqlite_connection
import settings


class ApiDataContainer:
    """Store data received from API."""

    def __init__(self, api_data=None):
        self._data = api_data

    @property
    def data(self):
        """Return the stored API data."""
        return self._data

    @data.setter
    def data(self, new_data):
        """Replace the stored data with the new ones."""
        self._data = new_data


class ApiDataDownloader(ApiDataContainer):
    """Download data from API."""

    def __init__(self, url, parameters, timeout=5):
        super(ApiDataDownloader, self).__init__()
        self.__api_url = url
        self.__parameters = parameters
        self.__timeout = timeout
        self.__error = None

    @property
    def error(self):
        """Return the error."""
        return self.__error

    def get_data(self):
        """Send all requests to the API and gather data."""
        api_data = []
        with requests.Session() as s:
            for parameter_dict in self.__parameters:
                data = self._send_request(s, parameter_dict)
                if data is None:
                    break
                if isinstance(data, list):
                    api_data += data
                else:
                    api_data.append(data)
            else:
                self._data = api_data

    def _send_request(self, session, params):
        """Send a request using the given session and parameters."""
        try:
            response = session.get(self.__api_url, params=params,
                                   timeout=self.__timeout)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            self.__error = f'HTTP Error: {err}'
        except requests.exceptions.Timeout as err:
            self.__error = f'Timeout Error: {err}'
        except requests.exceptions.ConnectionError as err:
            self.__error = f'Connection Error: {err}'
        except requests.exceptions.RequestException as err:
            self.__error = f'Request Error: {err}'
        else:
            return response.json()


class ApiDataModifier(ApiDataContainer):
    """Modify data received from API."""

    def __init__(self, data, modifications):
        super(ApiDataModifier, self).__init__(data)
        self.__modifications = modifications

    class _Decorators:
        """Decorators for ApiDataModifier methods."""

        @classmethod
        def add_new_key(cls, func):
            """Add new key-value pair to the dictionary"""

            def wrapper(self, dict_obj, dict_key, new_key, *args):
                value = func(self, dict_obj, dict_key, *args)
                if value is None:
                    return False
                dict_obj[new_key] = value
                return True

            return wrapper

    def make_modifications(self):
        """Perform the required data modifications."""
        for data_dict in self._data:
            for modification in self.__modifications:
                method = getattr(self, modification['function'])
                method(data_dict, *modification['args'])

    @_Decorators.add_new_key
    def _format_date(self, dict_obj, key, in_format, out_format):
        """Return the date in the specified format."""
        date_string = dict_obj.get(key)
        try:
            d = to_datetime(date_string, in_format)
        except (ValueError, TypeError):
            return None
        return to_string(d, out_format)

    @_Decorators.add_new_key
    def _currency_name(self, dict_obj, key):
        return dict_obj[key]


class ApiDataSave(ApiDataContainer):
    """Save API data to the database."""

    def __init__(self, api_data, db, table, foreign_keys, models='models'):
        super(ApiDataSave, self).__init__(api_data)
        self.__db = db
        self.__table = table
        self.__foreign_keys = foreign_keys
        self.__models_file = models

    def save_data(self):
        """Save all data to the database."""
        saved_objects = []
        columns = self._get_columns()
        for data_dict in self._data:
            obj = self._save_object(data_dict, columns)
            saved_objects.append(obj)
        return saved_objects

    def _save_object(self, data_dict, columns):
        """Create and save a new object to the database."""
        dataset = {column: data_dict[column] for column in columns}
        if self.__foreign_keys:
            dataset.update(self.__foreign_keys)
        cls = getattr(import_module(self.__models_file), self.__table)
        with self.__db:
            return cls.create(**dataset)

    def _get_columns(self):
        """Get a list of columns for the selected table.

        Exclude id and any foreign key fields.
        """
        with self.__db:
            fk = [i.column for i in self.__db.get_foreign_keys(self.__table)]
            columns = [c.name for c in self.__db.get_columns(self.__table) if
                       c.name != 'id' and c.name not in fk]
        return columns


class ApiWorker:
    """Download, modify and save the required API data."""

    def __init__(self, db, url, parameters, modifications, table,
                 foreign_keys, selection=None, reject_values=None):
        self.__db = db
        self.__url = url
        self.__parameters = parameters
        self.__modifications = modifications
        self.__table = table
        self.__foreign_keys = foreign_keys
        self.__selection = selection
        self.__reject_values = reject_values

    def data_one_to_many(self):
        """Prepare and save data with one to many relationship."""
        downloader = ApiDataDownloader(self.__url, self.__parameters)
        downloader.get_data()
        if downloader.data is None:
            error = downloader.error
            return None, error

        modifier = ApiDataModifier(downloader.data, self.__modifications)
        modifier.make_modifications()
        if self.__selection:
            data = self._select_data(data=downloader.data)
            downloader.data = data

        save_obj = ApiDataSave(downloader.data, self.__db, self.__table,
                               self.__foreign_keys)
        return save_obj.save_data(), None

    def _select_data(self, data):
        """Select data to be saved in the database."""
        return [data_dict for data_dict in data if
                data_dict[self.__selection] not in self.__reject_values]


class HistoricalCollector:
    """Collect historical OHLC values."""

    __table = 'HistoricalValue'
    __column = 'date'
    __api_url = settings.HISTORICAL_URL
    __modifications = settings.HISTORICAL_MODIFICATIONS

    def __init__(self, db, currency, start_date, end_date):
        self.__db = db
        self.__currency = currency
        self.__start_date = start_date
        self.__end_date = end_date

    def get_data(self):
        """Gather the requested data from the db or the API."""
        c, error = self.get_cryptocurrency()
        if c is None:
            return None, error

        with self.__db:
            db_data = self.get_historical_values(c)

        entries_required = self.count_days()
        if len(db_data) == entries_required:
            return db_data, None

        new_data, error = self.get_missing_data(c, db_data, entries_required)
        if new_data is None:
            return None, error

        with self.__db:
            complete_data = self.get_historical_values(c)

        return complete_data, error

    def get_cryptocurrency(self):
        """Get cryptocurrency from the database or the API."""
        error = None
        with self.__db:
            c = Cryptocurrency.get_or_none(currency_name=self.__currency)
        if c is not None:
            return c, error

        url = settings.CRYPTOCURRENCY_URL.safe_substitute(
            currency=self.__currency)
        parameters = (None,)
        modifications = settings.CRYPTOCURRENCY_MODIFICATIONS
        worker = ApiWorker(self.__db, url, parameters, modifications,
                           'Cryptocurrency', foreign_keys=None)
        data, error = worker.data_one_to_many()
        if error is None:
            data = data[0]
        else:
            if '404 Client Error' in error:
                error += ("\n\nMake sure you have entered the correct"
                          " cryptocurrency ID")
        return data, error

    def get_missing_data(self, c, db_data, entries_required):
        """Download missing historical data from the api."""
        parameters = self.requests_parameters(entries_required,
                                              settings.ROWS_LIMIT)
        reject_values = [to_string(day) for day in
                         list_values(db_data, self.__column)]
        url = self.__api_url.safe_substitute(coin=self.__currency)
        worker = ApiWorker(
            self.__db, url, parameters, self.__modifications, self.__table,
            {'currency': c}, self.__column, reject_values
        )
        new_data, error = worker.data_one_to_many()
        return new_data, error

    def get_historical_values(self, cryptocurrency):
        """Download historical values from the database."""
        db_data = HistoricalValue.get_data_in_range(
            self.__column, self.__start_date, self.__end_date,
            condition={'column': 'currency', 'value': cryptocurrency})
        return db_data

    def count_days(self):
        """Count days between start and end dates inclusively."""
        delta = self.__end_date - self.__start_date
        return delta.days + 1

    def date_range(self, days):
        """Get a list of dates for which data are needed."""
        dates = []
        start = self.__start_date
        for i in range(days):
            day = start + timedelta(days=i)
            dates.append(to_string(day))
        return dates

    def requests_parameters(self, entries_required, limit):
        """Prepare query parameters for requests sent to the API."""
        if entries_required < limit:
            return {'start': to_string(self.__start_date),
                    'end': to_string(self.__end_date)},

        date_range = self.date_range(entries_required)
        split_dates = [date_range[i * limit:(i + 1) * limit] for i in
                       range((len(date_range) + limit - 1) // limit)]
        return ({'start': i[0], 'end': i[-1]} for i in split_dates)


class HistoricalFunctions:
    """Perform calculations or actions as required by cli commands."""

    def __init__(self, historical_data, price_column):
        self.__historical_data = historical_data
        self.__price_column = price_column

    def longest_growth_period(self):
        """Find longest consecutive periods with increasing price."""

        if len(self.__historical_data) < 2:
            return None
        prices = list_values(self.__historical_data, self.__price_column)
        local_max, local_min = self.find_local_max_min(prices)

        # Discard first element if local maximum
        if len(local_max) > len(local_min):
            local_max.pop(0)
        # Discard last element if local minimum
        elif len(local_max) < len(local_min):
            local_min.pop(-1)
        else:
            # Discard first and last elem if local max and min accordingly
            if local_max[0] == 0:
                local_max.pop(0)
                local_min.pop(-1)

        pairs = list(zip(local_min, local_max))
        if not pairs:
            return None
        m = max(pairs, key=self.difference)
        return (p for p in pairs if self.difference(p) == self.difference(m))

    @staticmethod
    def find_local_max_min(data):
        """Find local maximum and local minimum values."""
        local_max = []
        local_min = []
        n = len(data)

        # First element on list
        if data[0] > data[1]:
            local_max.append(0)
        elif data[0] < data[1]:
            local_min.append(0)

        # Iterate through middle of tle list
        for i in range(1, n - 1):
            if data[i - 1] > data[i] < data[i + 1]:
                local_min.append(i)
            elif data[i - 1] < data[i] > data[i + 1]:
                local_max.append(i)

        # Last element on list
        if data[-1] > data[-2]:
            local_max.append(n - 1)
        elif data[-1] < data[-2]:
            local_min.append(n - 1)

        return local_max, local_min

    @staticmethod
    def difference(pair):
        """Calculate absolute difference between two elements."""
        return abs(pair[0] - pair[1])

    def period_details(self, period):
        """Get information about the selected period."""
        start, end = period
        d = self.difference((getattr(start, self.__price_column),
                             getattr(end, self.__price_column)))
        if d >= 0.01:
            d = d.quantize(Decimal('0.01'))
        return start.date, end.date, d

    def average_price(self):
        """Calculate the average price for each month."""
        grouped_by_months = self.group_by_months()
        result = []
        for data in grouped_by_months:
            prices = list_values(data, self.__price_column)
            average = mean(prices)
            if average >= 0.01:
                average = average.quantize(Decimal('0.01'))
            date = to_string(data[0].date, '%Y-%m')
            result.append((date, average))
        return result

    def group_by_months(self):
        """Group historical data by month."""
        result = []
        month = self.__historical_data[0].date.month
        start_index = 0
        for index, record in enumerate(self.__historical_data):
            if record.date.month == month:
                continue
            result.append(self.__historical_data[start_index:index])
            start_index = index
            month = record.date.month
        else:
            result.append(self.__historical_data[start_index:])
        return result

    def export_fo_file(self, name, format_):
        """Export historical data to the file in the given format."""
        export_methods = {'csv': '_save_as_csv', 'json': '_save_as_json'}
        method = export_methods.get(format_)
        if method is None:
            sys.exit(f'Unable to save to {format_} file. Unknown format.')
        func = getattr(self, method)
        filename = name + '.' + format_
        data = [i.to_file(self.__price_column) for i in self.__historical_data]
        func(data, filename)
        return filename

    @staticmethod
    def _save_as_json(data, filename):
        """Save the data as json file."""
        with open(filename, 'w') as file:
            json.dump(data, file, indent=4)

    @staticmethod
    def _save_as_csv(data, filename):
        """Save the data as csv file."""
        with open(filename, 'w') as file:
            headers = ['date', 'price']
            writer = csv.DictWriter(file, fieldnames=headers, delimiter=',')
            writer.writerow({'date': 'Date', 'price': 'Price ($)'})
            for dict_ in data:
                writer.writerow(dict_)


def list_values(container, attribute):
    """List the values of the selected attribute for all objects."""
    return [getattr(object_, attribute) for object_ in container]


def to_datetime(value, format_='%Y-%m-%d'):
    """Convert datetime object to a string."""
    return datetime.strptime(value, format_)


def to_string(value, format_='%Y-%m-%d'):
    """Convert string to a datetime object."""
    return datetime.strftime(value, format_)


def historical_functions(cli_function):
    """Decorator for cli historical functions."""

    no_data_message = Template(
        "No data has been found for the following query:\n "
        "Start date: $start\n End date: $end\n Coin: $coin"
    )
    error_message = Template(
        "\nThe command could not be executed.\n\nThe following error "
        "occurred while downloading data from API:\n $error\n"
    )

    def wrapper(ctx, **kwargs):
        """Gather required data and pass them to a CLI function."""
        db = sqlite_connection(settings.DB_PATH, settings.DB_FILENAME)
        c = HistoricalCollector(db, ctx.obj['coin'], ctx.obj['start_date'],
                                ctx.obj['end_date'])
        data, error = c.get_data()

        if error is not None:
            sys.exit(error_message.safe_substitute({'error': error}))

        if len(data) == 0:
            sys.exit(no_data_message.safe_substitute(
                {'start': to_string(ctx.obj['start_date']),
                 'end': to_string(ctx.obj['end_date']),
                 'coin': ctx.obj['coin']}))

        h = HistoricalFunctions(data, ctx.obj['ohlc'])

        cli_function(h, ctx, data, **kwargs)

    return wrapper
