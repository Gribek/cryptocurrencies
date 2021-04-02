from calendar import monthrange

import click

from functions import to_datetime


def validate_start_date(ctx, value):
    """Validate start_date argument."""

    # Check that the date format is correct
    format_match = False
    for format_ in ('%Y-%m-%d', '%Y-%m'):
        try:
            start_date = to_datetime(value, format_)
        except ValueError:
            pass
        else:
            format_match = True

    # Raise error if no format matches
    if not format_match:
        raise click.BadParameter(
            'Incorrect date format. Should be YYYY-MM-DD or YYYY-MM')

    # Add value to the context dictionary
    ctx.obj['start'] = start_date

    # Check that the start date is before the end date
    try:
        if start_date > ctx.obj['end']:
            raise click.BadParameter('Start date has to be before end date!')
    except KeyError:  # In case the user enters start_date first
        pass

    return start_date


def validate_end_date(ctx, value):
    """Validate end_date argument."""

    # Check that the date format is correct
    format_match = False
    modify_date = False
    try:
        end_date = to_datetime(value, '%Y-%m-%d')
    except ValueError:
        pass
    else:
        format_match = True

    try:
        end_date = to_datetime(value, '%Y-%m')
    except ValueError:
        pass
    else:
        format_match = True
        modify_date = True

    # Raise error if no format matches
    if not format_match:
        raise click.BadParameter(
            'Incorrect date format. Should be YYYY-MM-DD or YYYY-MM')

    # Set day to the last day of the month for format YYYY-MM
    if modify_date:
        end_date = last_day(end_date)

    # Add value to the context dictionary
    ctx.obj['end'] = end_date

    # Check that the start date is before the end date
    try:
        if end_date < ctx.obj['start']:
            raise click.BadParameter('End date has to be after start date!')
    except KeyError:  # In case the user enters end_date first
        pass

    return end_date


def last_day(date):
    """Set the day to the last day of the month."""
    day = monthrange(date.year, date.month)[1]
    return date.replace(day=day)
