# Use a Python image with uv pre-installed
FROM ghcr.io/astral-sh/uv:python3.10-alpine

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# TODO: Add a local directory mount to access exclusions and history files

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
ADD . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

USER guest

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Set these variables to blank and have them overwritten at runtime
ENV AWS_ACCESS_KEY_ID=""
ENV AWS_SECRET_ACCESS_KEY=""

# Reset the entrypoint, don't invoke `uv`
ENTRYPOINT ["aws-costs"]
