import click

from functions import historical_collector
from validation import validate_start_date, validate_end_date


@click.group()
@click.option('--start-date', prompt=True, callback=validate_start_date)
@click.option('--end-date', prompt=True, callback=validate_end_date)
@click.option('--coin', default='btc-bitcoin')
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


if __name__ == '__main__':
    cli(obj={})
