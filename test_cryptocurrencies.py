import json
import os
import re

from click.testing import CliRunner
from peewee import SqliteDatabase
import pytest

from historical import cli
from models import Cryptocurrency, HistoricalValue

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
