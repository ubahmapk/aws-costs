# aws-costs
Show blended cost for a given time frame, on a per-month basis.

## Usage

```Usage: aws-costs [OPTIONS]

 Show blended cost for a given time frame, on a per-month basis.
 Credentials are passed solely via the two environment variables:

 AWS_ACCESS_KEY_ID
 AWS_SECRET_ACCESS_KEY

╭─ Options ───────────────────────────────────────────────────────────────────────────────────╮
│ --start-date          TEXT     Start date for report [default: (First day of this month)]   │
│ --end-date            TEXT     End date for report [default: (Today)]                       │
│ --region      -r      TEXT     AWS Region [default: us-east-1]                              │
│ --verbose     -v      INTEGER  Repeat for extra verbosity [default: 0]                      │
│ --version     -V               Show the version and exit.                                   │
│ --help        -h               Show this message and exit.                                  │
╰─────────────────────────────────────────────────────────────────────────────────────────────╯
```

## Requirements

- arrow
- babel
- boto3
- typer
- loguru
- pydantic-settings
