import requests


class ApiDataDownloader:
    """Download data from API."""

    def __init__(self, url, parameters, timeout=5):
        self.__api_url = url
        self.__parameters = parameters
        self.__timeout = timeout
        self.__data = None

    @property
    def data(self):
        """Return the data collected from the API."""
        return self.__data

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
                self.__data = api_data

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
