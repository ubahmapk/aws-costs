from sys import stderr
from typing import Annotated

import arrow
import boto3

# import botocore.exceptions
import typer
from babel import numbers as b_numbers
from loguru import logger
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings
from rich import print as rprint

from aws_costs.__version__ import __version__


class Settings(BaseSettings):
    aws_access_key_id: str = Field(min_length=20, pattern=r"^[a-zA-Z0-9]{20,}$")
    aws_secret_access_key: str = Field(min_length=40, pattern=r"^[a-zA-Z0-9/\+=]{40,}$")


def set_logging_level(verbosity: int) -> None:
    """Set the global logging level"""

    # Default level
    log_level = "ERROR"

    if verbosity is not None:
        if verbosity == 1:
            log_level = "INFO"
        elif verbosity > 1:
            log_level = "DEBUG"

    logger.remove(0)
    # noinspection PyUnboundLocalVariable
    logger.add(stderr, level=log_level)


def validate_date(value: str) -> str:
    """Validate the proper format for a date"""

    try:
        date_option = arrow.get(value, "YYYY-MM-DD").format("YYYY-MM-DD")
        # logger.debug(f"{date_option} is a valid YYYY-MM-DD string")
    except Exception:
        # logger.debug(f"Entered date: {value}")
        raise typer.BadParameter("Date format must be YYYY-MM-DD") from None

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
            if typer.confirm(
                "Today is the first of the month. Would you like to see last month's cost, instead?",
                default=True,
                show_default=True,
            ):
                start_date = arrow.utcnow().shift(months=-1).format("YYYY-MM-DD")
                logger.debug(f"start_date modified, now {start_date}")
            else:
                rprint("[bold red]Invalid date range. Start and end dates cannot be the same day.[/bold red]")
                raise typer.Abort()

        else:
            rprint("[bold red]Invalid date range. Start and end dates cannot be the same day.[/bold red]")
            raise typer.Abort()

    if start_date >= end_date:
        rprint("[bold red]Invalid date range. Start date must come before end date[/bold red]")
        raise typer.Abort()

    # Return potentially modified start and end dates
    return start_date, end_date


def retrieve_aws_credentials() -> tuple[str, str]:
    """Retrieve AWS credentials from environment variables"""

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    try:
        settings = Settings()  # type: ignore reportCallIssue
        aws_access_key_id = settings.aws_access_key_id
        aws_secret_access_key = settings.aws_secret_access_key

    except ValidationError:
        rprint(
            "[bold red]AWS credentials are not set or are invalid. Please set the AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.[/bold red]"
        )
        raise typer.Exit(500) from None

    logger.debug("AWS credentials found in environment")

    return aws_access_key_id, aws_secret_access_key


app = typer.Typer(add_completion=False, context_settings={"help_option_names": ["-h", "--help"]})


def version_callback(value: bool) -> None:
    if value:
        print(f"aws-costs version {__version__}")

        raise typer.Exit(0)

    return None


@app.command()
def cli(
    start_date: str = typer.Option(
        help="Start date for report",
        callback=validate_date,
        default=lambda: arrow.now().replace(day=1).format("YYYY-MM-DD"),
        show_default="First day of this month",
    ),
    end_date: str = typer.Option(
        help="End date for report",
        callback=validate_date,
        default=lambda: arrow.now().format("YYYY-MM-DD"),
        show_default="Today",
    ),
    aws_region: Annotated[str, typer.Option("--region", "-r", help="AWS Region", show_default=True)] = "us-east-1",
    verbosity: Annotated[int, typer.Option("--verbose", "-v", help="Repeat for extra verbosity")] = 0,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=version_callback,
            is_eager=True,
            show_default=False,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """
    \b
    Show blended cost for a given time frame, on a per-month basis.

    \b
    Credentials are passed solely via the two environment variables:

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
        rprint("[bold red]Error retrieving AWS Cost and Usage report[/bold red]")
        rprint(f"{e!s}")
        raise typer.Exit(500) from None

    # Print results
    time_periods = response["ResultsByTime"]
    unit = time_periods[0]["Total"]["BlendedCost"]["Unit"]
    for time_range in time_periods:
        start = time_range["TimePeriod"]["Start"]
        end = time_range["TimePeriod"]["End"]
        cost = time_range["Total"]["BlendedCost"]["Amount"]
        local_cost = b_numbers.format_currency(cost, "USD", locale="en_US")

        print()
        rprint(f"[bold white]Start: {start} -> End: {end}[/bold white]")
        print(f"Cost: {local_cost} {unit}")


if __name__ == "__main__":
    app()
