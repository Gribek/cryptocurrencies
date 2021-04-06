from calendar import monthrange

import click

from functions import to_datetime


def validate_start_date(ctx, param, value):
    """Validate start_date argument."""

    # Check that the date format is correct
    format_match = False
    for format_ in ('%Y-%m-%d', '%Y-%m'):
        start_date = try_format(value, format_)
        if start_date is not None:
            format_match = True
            break

    # Raise error if no format matches
    if not format_match:
        raise click.BadParameter(
            'Incorrect date format. Should be YYYY-MM-DD or YYYY-MM')

    # Add value to the context dictionary
    ctx.obj['start'] = start_date

    # Check that the start date is before the end date
    try:
        if start_date > ctx.obj['end']:
            raise click.BadParameter(
                'The start date must be earlier than the end date!')
    except KeyError:  # In case the user enters start_date first
        pass

    return start_date


def validate_end_date(ctx, param, value):
    """Validate end_date argument."""

    # Check that the date format is correct
    format_match = False
    modify_date = False
    end_date = try_format(value, '%Y-%m-%d')
    if end_date is not None:
        format_match = True
    else:
        end_date = try_format(value, '%Y-%m')
        if end_date is not None:
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
            raise click.BadParameter(
                'The end date must be later than the start date!')
    except KeyError:  # In case the user enters end_date first
        pass

    return end_date


def validate_filename(ctx, param, value):
    """Validate file argument. Return value without file format."""
    return value.split('.')[0]


def try_format(value, format_):
    """Try to change type to datetime with the given format."""
    try:
        return to_datetime(value, format_)
    except ValueError:
        return None


def last_day(date):
    """Set the day to the last day of the month."""
    day = monthrange(date.year, date.month)[1]
    return date.replace(day=day)
