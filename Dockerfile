# Use Python bookworm image which includes many build dependencies
FROM python:3.10-bookworm

# Environment variables
ARG YOUR_ENV

ENV YOUR_ENV=${YOUR_ENV:-development} \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=1.7.1

# Install only the remaining necessary dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Set the working directory
WORKDIR /app

# Copy Poetry files
COPY pyproject.toml poetry.lock /app/

# Install dependencies with Poetry
RUN poetry config virtualenvs.in-project true \
    && poetry install $(test "$YOUR_ENV" = production && echo "--only=main") --all-extras --no-interaction --no-ansi

