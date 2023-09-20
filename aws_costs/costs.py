import arrow
import boto3
import click
import logging
import os
from babel import numbers as b_numbers
from pprint import pprint

__version__ = "0.0.1"
__author__ = "Jon Mark Allen (jm@phyxt.net)"


logger = logging.getLogger()

def set_logging_level(verbosity):
    """Set the global logging level"""

    if verbosity is not None:
        if verbosity == 1:
            log_level = "INFO"
        elif verbosity > 1:
            log_level = "DEBUG"
        else:
            log_level = "ERROR"

    logging.basicConfig(level=log_level)


def validate_date(ctx, param, value):
    """Validate the proper format for a date"""

    try:
        date_option = arrow.get(value, "YYYYMMDD").format("YYYY-MM-DD")
        logger.debug(f"{date_option} is a valid YYYYMMDD string")
    except Exception as e:
        logger.debug(f"Entered date: {value}")
        raise click.BadParameter("Date format must be YYYYMMDD")

    return date_option


@click.command()
@click.version_option(__version__, "-V", "--version")
@click.help_option("-h", "--help")
@click.option(
    "-v", "--verbose", "verbosity", help="Repeat for extra visibility", count=True
)
@click.option(
    "--start",
    "start_date",
    type=click.UNPROCESSED,
    callback=validate_date,
    help="Start date for report",
    default=lambda: arrow.now().replace(day=1).format("YYYYMMDD"),
    show_default="First day of this month",
)
@click.option(
    "--end",
    "end_date",
    type=click.UNPROCESSED,
    callback=validate_date,
    help="End date for report. Default is today.",
    default=lambda: arrow.now().format("YYYYMMDD"),
    show_default="Today",
)
def cli(start_date, end_date, verbosity):
    """
    \b
    Show blended cost for a given time frame, on a per-month basis.

    \b
    Credentials are currently passed solely via the two environment variables:

    \b
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY
    """

    set_logging_level(verbosity)

    # Retrieve AWS credentials from environment variables
    aws_access_key_id = os.environ.get("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.environ.get("AWS_SECRET_ACCESS_KEY")

    logger.debug(f"AWS ACCESS KEY: {aws_access_key_id}")
    logger.debug(f"AWS SECRET ACCESS KEY: {aws_secret_access_key}")

    # AWS region
    aws_region = "us-east-1"  # Replace with your AWS region

    # Set up the AWS Cost Explorer client
    ce_client = boto3.client(
        "ce",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region,
    )

    # Cost and usage reports are *inclusive* for start dates and *exclusive* for end dates
    end_date = arrow.get(start_date).shift(months=1).replace(day=1).format("YYYY-MM-DD")

    logger.debug(f"Start date: {start_date}")
    logger.debug(f"End date: {end_date}")

    # Specify the report name and format
    report_name = "LastMonthBill"  # Replace with your report name

    # Retrieve the AWS cost and usage report
    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={"Start": start_date, "End": end_date},
            Granularity="MONTHLY",
            Metrics=("BlendedCost",),
        )

    except Exception as e:
        click.secho(f"Error retrieving AWS Cost and Usage report", fg="red", bold=True)
        click.echo(f"{str(e)}")
        exit(500)

    time_periods = response["ResultsByTime"]
    for time_range in time_periods:
        start = time_range["TimePeriod"]["Start"]
        end = time_range["TimePeriod"]["End"]
        cost = time_range["Total"]["BlendedCost"]["Amount"]
        local_cost = b_numbers.format_currency(cost, "USD", locale="en_US")
        unit = time_range["Total"]["BlendedCost"]["Unit"]

        click.echo()
        click.secho(f"Start: {start} -> End: {end}", fg="white", bold=True)
        click.echo(f"Cost: {local_cost} {unit}")
        click.echo()
