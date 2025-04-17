# Use an official Python runtime as a parent image
FROM python:3.13-slim@sha256:21e39cf1815802d4c6f89a0d3a166cc67ce58f95b6d1639e68a394c99310d2e5

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
    POETRY_NO_INTERACTION=1

# Install necessary build tools and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    make \
    build-essential \
    libffi-dev \
    libssl-dev \
    python3-dev \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry in a known location and add to PATH
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && ln -s /root/.local/bin/poetry /usr/local/bin/poetry

# Set the working directory in the container
WORKDIR /app

# Copy only pyproject.toml and poetry.lock to cache them in the Docker layer
COPY pyproject.toml poetry.lock /app/

# Install the dependencies from pyproject.toml using Poetry
RUN poetry install $(test "$YOUR_ENV" = production && echo "--only=main") --no-interaction --no-ansi

# Install the darwin-py package and CLI executable using pip
RUN pip install darwin-py

# The following steps are commented out to allow users to customize the Dockerfile:

# Copy the rest of the application code (uncomment and modify as needed)
# COPY . /app

# Expose any necessary ports (uncomment and modify as needed)
# EXPOSE 80

# Set an entry point or command (uncomment and modify as needed)
# CMD ["python", "/app/your_main_script.py"]

# End of Dockerfile
