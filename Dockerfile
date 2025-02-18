# Use an official Python runtime as a parent image
FROM python:3.10-slim@sha256:8666a639a54acc810408e505e2c6b46b50834385701675ee177f578b3d2fdef9

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

# Install system dependencies and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    make \
    build-essential \
    libffi-dev \
    libssl-dev \
    python3-dev \
    curl \
    wget \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    llvm \
    libncurses5-dev \
    libncursesw5-dev \
    xz-utils \
    tk-dev \
    liblzma-dev \
    python3-openssl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install FFmpeg
RUN mkdir -p /usr/local/bin \
    && cd /usr/local/bin \
    && wget -O ffmpeg.tar.xz "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz" \
    && tar -xf ffmpeg.tar.xz --strip-components=1 \
    && rm ffmpeg.tar.xz

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

