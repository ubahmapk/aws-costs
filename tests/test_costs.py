import click
import pytest
from typer import BadParameter
from typer.testing import CliRunner

from aws_costs.__version__ import __version__
from aws_costs.costs import (
    app,
    retrieve_aws_credentials,
    validate_date,
    validate_date_range,
)


@pytest.fixture
def mock_env_vars(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIAIOSFODNN7EXAMPLE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")


def test_successful_aws_credentials_retrieval(mock_env_vars):
    access_key, secret_key = retrieve_aws_credentials()
    assert access_key == "AKIAIOSFODNN7EXAMPLE"
    assert secret_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"


def test_cost_report_generation(mocker, mock_env_vars):
    mock_ce_client = mocker.Mock()
    mock_ce_client.get_cost_and_usage.return_value = {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": "2023-01-01", "End": "2023-01-31"},
                "Total": {"BlendedCost": {"Amount": "100.00", "Unit": "USD"}},
                "Groups": [],
                "Estimated": False,
            }
        ]
    }
    mocker.patch("boto3.client", return_value=mock_ce_client)

    runner = CliRunner()
    result = runner.invoke(app, ["--start-date", "2023-01-01", "--end-date", "2023-01-31"])
    assert result.exit_code == 0


def test_invalid_date_range():
    with pytest.raises(click.exceptions.Abort):
        validate_date_range("2023-02-01", "2023-01-01")


def test_aws_api_error_handling(mocker, mock_env_vars):
    mock_ce_client = mocker.Mock()
    mock_ce_client.get_cost_and_usage.side_effect = Exception("AWS API Error")
    mocker.patch("boto3.client", return_value=mock_ce_client)

    runner = CliRunner()
    result = runner.invoke(app, ["--start-date", "2023-01-01", "--end-date", "2023-01-31"])
    assert result.exit_code == 500


def test_version_display():
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert f"aws-costs version {__version__}" in result.stdout


def test_invalid_date_format():
    with pytest.raises(BadParameter):
        validate_date("2023/01/01")

    with pytest.raises(BadParameter):
        validate_date("invalid-date")
