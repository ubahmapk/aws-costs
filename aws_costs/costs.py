
import arrow
import boto3
# import botocore.exceptions
import click
from babel import numbers as b_numbers
from loguru import logger
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings
from sys import exit, stderr

__version__ = "0.3.3"
__author__ = "Jon Mark Allen (ubahmapk@gmail.com)"

class Settings(BaseSettings):
    aws_access_key_id: str = Field(min_length=20, pattern=r'^[a-zA-Z0-9]{20,}$')
    aws_secret_access_key: str = Field(min_length=40, pattern=r'^[a-zA-Z0-9/\+=]{40,}$')


def set_logging_level(verbosity: int) -> None:
    """Set the global logging level"""

    if verbosity is not None:
        if verbosity == 1:
            log_level = "INFO"
        elif verbosity > 1:
            log_level = "DEBUG"
        else:
            log_level = "ERROR"

    logger.remove(0)
    logger.add(stderr, level=log_level)


def validate_date(ctx: click.Context, param: click.ParamType, value: str) -> str:
    """Validate the proper format for a date"""

    try:
        date_option = arrow.get(value, "YYYY-MM-DD").format("YYYY-MM-DD")
        logger.debug(f"{date_option} is a valid YYYY-MM-DD string")
    except Exception:
        logger.debug(f"Entered date: {value}")
        raise click.BadParameter("Date format must be YYYY-MM-DD") from None

    return date_option


def validate_date_range(start_date: str, end_date: str) -> tuple[str, str]:
    """Validate the range provided will not cause AWS to vomit

    Right now, that only entails:
    - Ensuring the start and end dates are not the same
    - Ensuring the end date comes AFTER the start date

    Helpfully prompt for last month's costs, if today is the first of the month.
    """

    logger.debug(f"start_date: {start_date}")
    logger.debug(f"end_date: {end_date}")

    if start_date == end_date:
        if start_date == arrow.utcnow().floor("month").format("YYYY-MM-DD"):
            if click.confirm(
                "Today is the first of the month. Would you like to see last month's cost, instead?",
                default=True,
                show_default=True,
            ):
                start_date = arrow.utcnow().shift(months=-1).format("YYYY-MM-DD")
                logger.debug(f"start_date modified, now {start_date}")
            else:
                raise click.BadOptionUsage(
                    end_date,
                    "Invalid date range. Start and end dates cannot be the same day.",
                )

        else:
            raise click.BadOptionUsage(
                end_date,
                "Invalid date range. Start and end dates cannot be the same day.",
            )

    if start_date >= end_date:
        raise click.BadOptionUsage(
            end_date, "Invalid date range. Start date must come before end date"
        )

    # Return potentially modified start and end dates
    return start_date, end_date


def retrieve_aws_credentials() -> tuple[str, str]:
    """Retrieve AWS credentials from environment variables"""

    try:
        settings = Settings()
        aws_access_key_id: str = settings.aws_access_key_id
        aws_secret_access_key: str = settings.aws_secret_access_key

    except ValidationError:
        click.secho(
            "AWS credentials are not set or are invalid. Please set the AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.",
            fg="red",
            bold=True,
        )
        exit(500)

    logger.debug("AWS credentials found in environment")

    return aws_access_key_id, aws_secret_access_key


@click.command()
@click.version_option(__version__, "-V", "--version")
@click.help_option("-h", "--help")
@click.option(
    "-v", "--verbose", "verbosity", help="Repeat for extra visibility", count=True
)
@click.option(
    "-r",
    "--region",
    "aws_region",
    help="AWS Region",
    default="us-east-1",
    show_default=True,
)
@click.option(
    "--start",
    "start_date",
    type=click.UNPROCESSED,
    callback=validate_date,
    help="Start date for report",
    default=lambda: arrow.now().replace(day=1).format("YYYY-MM-DD"),
    show_default="First day of this month",
)
@click.option(
    "--end",
    "end_date",
    type=click.UNPROCESSED,
    callback=validate_date,
    help="End date for report. Default is today.",
    default=lambda: arrow.now().format("YYYY-MM-DD"),
    show_default="Today",
)
def cli(start_date: str, end_date: str, verbosity: int, aws_region: str) -> None:
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

    aws_access_key_id, aws_secret_access_key = retrieve_aws_credentials()

    start_date, end_date = validate_date_range(start_date, end_date)

    # Set up the AWS Cost Explorer client
    ce_client = boto3.client(
        "ce",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=aws_region,
    )

    logger.debug(f"Start date: {start_date}")
    logger.debug(f"End date: {end_date}")

    # Retrieve the AWS cost and usage report
    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={"Start": start_date, "End": end_date},
            Granularity="MONTHLY",
            Metrics=("BlendedCost",),
        )

    except Exception as e:
        click.secho("Error retrieving AWS Cost and Usage report", fg="red", bold=True)
        click.echo(f"{str(e)}")
        exit(500)

    # Print results
    time_periods = response["ResultsByTime"]
    unit = time_periods[0]["Total"]["BlendedCost"]["Unit"]
    for time_range in time_periods:
        start = time_range["TimePeriod"]["Start"]
        end = time_range["TimePeriod"]["End"]
        cost = time_range["Total"]["BlendedCost"]["Amount"]
        local_cost = b_numbers.format_currency(cost, "USD", locale="en_US")

        click.echo()
        click.secho(f"Start: {start} -> End: {end}", fg="white", bold=True)
        click.echo(f"Cost: {local_cost} {unit}")
