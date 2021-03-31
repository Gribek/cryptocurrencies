from datetime import datetime, date, timedelta
from importlib import import_module
import requests


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

    def get_data(self):
        """Send all requests to the API and gather data."""
        api_data = []
        with requests.Session() as s:
            for parameter_dict in self.__parameters:
                data = self.send_request(s, parameter_dict)
                if data is None:
                    break
                api_data += data
            else:
                self._data = api_data

    def send_request(self, session, params):
        """Send a request using the given session and parameters."""
        try:
            response = session.get(self.__api_url, params=params,
                                   timeout=self.__timeout)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print('HTTP Error:', err)
        except requests.exceptions.Timeout as err:
            print('Timeout Error:', err)
        except requests.exceptions.ConnectionError as err:
            print('Connection Error:', err)
        except requests.exceptions.RequestException as err:
            print('Request Error:', err)
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
    def format_date(self, dict_obj, key, in_format, out_format):
        """Return the date in the specified format."""
        date_string = dict_obj.get(key)
        try:
            d = datetime.strptime(date_string, in_format)
        except (ValueError, TypeError):
            return None
        return datetime.strftime(d, out_format)


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
        columns = self.__get_columns()
        for data_dict in self._data:
            obj = self.__save_object(data_dict, columns)
            saved_objects.append(obj)
        return saved_objects

    def __save_object(self, data_dict, columns):
        """Create and save a new object to the database."""
        dataset = {column: data_dict[column] for column in columns}
        dataset.update(self.__foreign_keys)
        cls = getattr(import_module(self.__models_file), self.__table)
        with self.__db:
            return cls.create(**dataset)

    def __get_columns(self):
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

        modifier = ApiDataModifier(downloader.data, self.__modifications)
        modifier.make_modifications()
        if self.__selection:
            data = self.__select_data(data=downloader.data)
            downloader.data = data

        save_obj = ApiDataSave(downloader.data, self.__db, self.__table,
                               self.__foreign_keys)
        return save_obj.save_data()

    def __select_data(self, data):
        """Select data to be saved in the database."""
        return [data_dict for data_dict in data if
                data_dict[self.__selection] not in self.__reject_values]


class DataCollector:

    def __init__(self, db):
        self._db = db

    @staticmethod
    def list_values(db_data, column):
        return [getattr(object_, column) for object_ in db_data]
