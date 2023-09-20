# aws-costs
Show blended cost for a given time frame, on a per-month basis.

## Usage

```Usage: aws-costs [OPTIONS]

  Show blended cost for a given time frame, on a per-month basis.

  Credentials are currently passed solely via the two environment variables:

  AWS_ACCESS_KEY_ID
  AWS_SECRET_ACCESS_KEY

Options:
  -V, --version  Show the version and exit.
  -h, --help     Show this message and exit.
  -v, --verbose  Repeat for extra visibility
  --start TEXT   Start date for report  [default: (First day of this month)]
  --end TEXT     End date for report. Default is today.  [default: (Today)]
```

## Requirements

- arrow
- babel
- boto3
- click
