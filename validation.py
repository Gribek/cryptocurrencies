import click

from functions import to_datetime


def validate_start_date(ctx, value):
    """Validate start_date argument."""
    try:
        start_date = to_datetime(value)
        ctx.obj['start'] = start_date
    except ValueError:
        raise click.BadParameter('Incorrect date format. Should be YYYY-MM-DD')

    try:
        if start_date > ctx.obj['end']:
            raise click.BadParameter('Start date has to be before end date!')
    except KeyError:  # In case the user enters start_date first
        pass

    return start_date


def validate_end_date(ctx, value):
    """Validate end_date argument."""
    try:
        end_date = to_datetime(value)
        ctx.obj['end'] = end_date
    except ValueError:
        raise click.BadParameter('Incorrect date format. Should be YYYY-MM-DD')

    try:
        if end_date < ctx.obj['start']:
            raise click.BadParameter('End date has to be after start date!')
    except KeyError:  # In case the user enters end_date first
        pass

    return end_date
