import json
import os
import re

from click.testing import CliRunner
from peewee import SqliteDatabase
import pytest

from historical import cli
from models import Cryptocurrency, HistoricalValue
from functions import ApiDataDownloader, ApiDataModifier
import settings

MODELS = [Cryptocurrency, HistoricalValue]
TEST_DATA_FILE = 't_data.json'

# SQLite database for tests
db = SqliteDatabase(':memory:')


class TestHistoricalCommands:
    """Test CLI historical commands."""

    code_error = 'Exit code other than 0'
    description_error = 'Incorrect description of the results'
    increase_error = 'Incorrect increase value calculated'
    period_error = 'Incorrect consecutive period found'

    @classmethod
    def setup_class(cls):
        """Set up the database and add testing data."""
        db.bind(MODELS, bind_refs=False, bind_backrefs=False)
        db.connect()
        db.create_tables(MODELS)

        try:
            with open(TEST_DATA_FILE, 'r') as f:
                data = json.load(f)
                c = Cryptocurrency.create(currency_name='btc-bitcoin')
                for elem in data:
                    elem['currency'] = c
                    HistoricalValue.create(**elem)
        except FileNotFoundError:
            pytest.exit(f'{TEST_DATA_FILE} file is missing')

    @classmethod
    def teardown_class(cls):
        """Disconnect from the database. Delete temporary test files."""
        db.drop_tables(MODELS)
        db.close()

        for file in ['test.csv', 'test.json', 'test_name.csv']:
            try:
                os.remove(file)
            except FileNotFoundError:
                pass

    def test_consecutive_increase_single_result(self):
        """Test consecutive-increase command, single period found."""
        runner = CliRunner()
        args = ['--start-date', '2020-01-01', '--end-date', '2020-01-31',
                'consecutive-increase']
        result = runner.invoke(cli, args=args, obj={})
        o = result.output
        assert result.exit_code == 0, self.code_error
        assert 'from 2020-01-25 to 2020-01-28' in o, self.period_error
        assert len(re.findall(r'\d{4}-\d{2}-\d{2}', o)) == 2, self.period_error
        assert '$966.27' in o, self.increase_error
        assert 'Longest consecutive period was' in o, self.description_error

    def test_consecutive_increase_multiple_results(self):
        """Test consecutive-increase command, many periods found."""
        runner = CliRunner()
        args = ['--start-date', '2020-01-01', '--end-date', '2020-01-20',
                'consecutive-increase']
        result = runner.invoke(cli, args=args, obj={})
        o = result.output
        assert result.exit_code == 0, self.code_error
        for period in ['from 2020-01-02 to 2020-01-04',
                       'from 2020-01-05 to 2020-01-07',
                       'from 2020-01-16 to 2020-01-18']:
            assert period in o, self.period_error
        assert len(re.findall(r'\d{4}-\d{2}-\d{2}', o)) == 6, self.period_error
        for value in ['$383.57', '$804.65', '$218.37']:
            assert value in o, self.increase_error
        assert 'More than one consecutive period' in o, self.description_error

    def test_month_average_price(self):
        """Test average-price-by-month command."""
        average_error = 'Incorrect average value calculated'
        month_error = 'Average value calculated for wrong month'

        runner = CliRunner()
        args = ['--start-date', '2020-01', '--end-date', '2020-03',
                'average-price-by-month']
        result = runner.invoke(cli, args=args, obj={})
        o = result.output
        assert result.exit_code == 0, self.code_error
        for value in ['8388.25', '9663.34', '6884.03']:
            assert value in o, average_error
        for month in ['2020-01', '2020-02', '2020-03']:
            assert month in o, month_error
        assert len(re.findall(r'\d{4}-\d{2}', o)) == 3, (
            'Calculated more average values than expected')
        assert 'Date' in o, self.description_error
        assert 'Average price ($)' in o, self.description_error

    def test_export_csv(self):
        """Test export command, export to the csv file."""
        file_content_error = 'Incorrect file content'
        runner = CliRunner()
        args = ['--start-date', '2020-01-01', '--end-date', '2020-01-31',
                'export', '--format', 'csv', '--file', 'test']
        result = runner.invoke(cli, args=args, obj={})
        assert result.exit_code == 0, self.code_error
        try:
            with open('test.csv', 'r') as f:
                first_line = f.readline()
                assert first_line == 'Date,Price ($)\n', 'Incorrect fieldnames'
                next_line = f.readline()
                assert '2020-01-01' in next_line, file_content_error
                assert '7220.19' in next_line, file_content_error
                assert ',' in next_line, 'Incorrect delimiter'
        except FileNotFoundError:
            raise AssertionError("File not created")

    def test_export_json(self):
        """Test export command, export to the json file."""
        runner = CliRunner()
        args = ['--start-date', '2020-01-01', '--end-date', '2020-01-31',
                'export', '--format', 'json', '--file', 'test']
        result = runner.invoke(cli, args=args, obj={})
        assert result.exit_code == 0, self.code_error
        try:
            with open('test.json', 'r') as f:
                try:
                    content = json.load(f)
                    assert len(content) == 31, (
                        'Incorrect number of database rows exported')
                except ValueError:
                    raise AssertionError('File content is not valid json')
        except FileNotFoundError:
            raise AssertionError('File not created')

    def test_export_correct_filename(self):
        """Test export command, check filename and format."""
        runner = CliRunner()
        args = ['--start-date', '2020-01-01', '--end-date', '2020-01-2',
                'export', '--format', 'csv', '--file', 'test_name.json']
        result = runner.invoke(cli, args=args, obj={})
        assert result.exit_code == 0, self.code_error
        assert os.path.isfile('test_name.csv'), 'Incorrect filename'
        assert not os.path.isfile('test_name.json'), 'Incorrect file format'


@pytest.fixture
def downloader():
    parameters = ({'start': '2020-01-01', 'end': '2020-01-31'},)
    url = settings.HISTORICAL_URL.safe_substitute(coin='btc-bitcoin')
    downloader = ApiDataDownloader(url, parameters, 10)
    return downloader


@pytest.fixture
def downloader_second():
    parameters = ({'start': '2020-01-01', 'end': '2020-01-31'},
                  {'start': '2020-02-01', 'end': '2020-02-28'},
                  {'start': '2020-03-01', 'end': '2020-03-31'})
    url = settings.HISTORICAL_URL.safe_substitute(coin='btc-bitcoin')
    downloader = ApiDataDownloader(url, parameters, 10)
    return downloader


@pytest.fixture
def downloader_third():
    parameters = (None,)
    url = settings.CRYPTOCURRENCY_URL.safe_substitute(currency='btc-bitcoin')
    downloader = ApiDataDownloader(url, parameters, 10)
    return downloader


class TestApiDataDownloader:
    """Test ApiDataDownloader methods."""

    no_data_error = 'Data has not been downloaded'
    amount_error = 'Incorrect amount of downloaded data'

    def test_get_data_single_request(self, downloader):
        """Test downloading historical data with single request."""
        downloader.get_data()
        if downloader.error is None:
            assert downloader.data is not None, self.no_data_error
            assert len(downloader.data) == 31, self.amount_error

    def test_get_data_multiple_requests(self, downloader_second):
        """Test downloading historical data with multiple requests."""
        downloader_second.get_data()
        if downloader_second.error is None:
            assert downloader_second.data is not None, self.no_data_error
            assert len(downloader_second.data) == 90, self.amount_error

    def test_get_data_cryptocurrency(self, downloader_third):
        """Test downloading cryptocurrency data."""
        coin_error = 'Data collected for the wrong currency'

        downloader_third.get_data()
        if downloader_third.error is None:
            assert downloader_third.data is not None, self.no_data_error
            assert len(downloader_third.data) == 1, self.amount_error
            assert downloader_third.data[0]['id'] == 'btc-bitcoin', coin_error


@pytest.fixture
def modifier():
    data = [
        {"time_open": "2019-01-01T00:00:00Z",
         "time_close": "2019-01-01T23:59:59Z", "open": 3743.13383814,
         "high": 3848.768792, "low": 3695.32467935, "close": 3846.6792974,
         "volume": 3062073034, "market_cap": 65338972677},
        {"time_open": "2019-01-02T00:00:00Z",
         "time_close": "2019-01-02T23:59:59Z", "open": 3852.19783968,
         "high": 3951.20469616, "low": 3811.88806393, "close": 3941.99122065,
         "volume": 3627095860, "market_cap": 67250129005},
        {"time_open": "2019-01-03T00:00:00Z",
         "time_close": "2019-01-03T23:59:59Z", "open": 3942.27312969,
         "high": 3942.57529017, "low": 3828.26988091, "close": 3838.44932784,
         "volume": 3126326309, "market_cap": 68829869344}]
    modifications = settings.HISTORICAL_MODIFICATIONS
    modifier = ApiDataModifier(data, modifications)
    return modifier


@pytest.fixture
def modifier_currency():
    data = [{"id": "btc-bitcoin", "name": "Bitcoin", "symbol": "BTC",
             "rank": 1, "is_new": False, "is_active": True, "type": "coin"}]
    modifications = settings.CRYPTOCURRENCY_MODIFICATIONS
    modifier = ApiDataModifier(data, modifications)
    return modifier


class TestApiDataModifier:
    """Test ApiDataModifier methods."""

    ker_error = 'Key is missing in data dictionary'
    value_error = 'Incorrect value after modifications'

    def test_make_modifications_historical_data(self, modifier):
        """Test making modifications on historical data."""
        modifier.make_modifications()
        key = 'date'
        for data_dict in modifier.data:
            assert key in data_dict, self.ker_error
        for i, date in enumerate(('2019-01-01', '2019-01-02', '2019-01-03')):
            assert modifier.data[i][key] == date, self.value_error

    def test_make_modifications_cryptocurrency(self, modifier_currency):
        """Test making modifications on cryptocurrency data."""
        modifier_currency.make_modifications()
        currency_data = modifier_currency.data[0]
        key = 'currency_name'
        assert key in currency_data, self.ker_error
        assert currency_data[key] == 'btc-bitcoin', self.value_error
