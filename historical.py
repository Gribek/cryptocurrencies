import click

from functions import historical_collector, HistoricalFunctions
from validation import validate_start_date, validate_end_date, \
    validate_filename


@click.group()
@click.option('--start-date', prompt=True, callback=validate_start_date)
@click.option('--end-date', prompt=True, callback=validate_end_date)
@click.option('--coin', default='btc-bitcoin',
              help='Specify the name of the cryptocurrency, '
                   'default is "btc-bitcoin"')
@click.option('--ohlc', default='close',
              type=click.Choice(['open', 'close', 'high', 'low']),
              help='Choose one of the OHLC values, default is "close"')
@click.pass_context
def cli(ctx, **kwargs):
    ctx.ensure_object(dict)
    ctx.obj = kwargs


@cli.command('consecutive-increase')
@click.pass_context
@historical_collector
def consecutive_increase(ctx, data):
    click.echo(data)
    for i in data:
        click.echo(getattr(i, ctx.obj['ohlc']))
    click.echo('consecutive-increase')
    click.echo(ctx.obj['coin'])
    click.echo(ctx.obj['ohlc'])


@cli.command('average-price-by-month')
@click.pass_context
@historical_collector
def month_average_price(ctx, data):
    click.echo(data)
    for i in data:
        click.echo(getattr(i, 'date'))


@cli.command('export')
@click.pass_context
@click.option('--format', default='csv', type=click.Choice(['csv', 'json']),
              help='Choose file format, default is "csv"')
@click.option('--file', default='data', callback=validate_filename,
              help='Choose name of the file, default is "historical_data"')
@historical_collector
def export(ctx, data, **kwargs):
    h = HistoricalFunctions(data, ctx.obj['ohlc'])
    filename = h.export_fo_file(kwargs['file'], kwargs['format'])
    if filename:
        click.echo(
            f' The data has been successfully written to the {filename} file')


if __name__ == '__main__':
    cli(obj={})
