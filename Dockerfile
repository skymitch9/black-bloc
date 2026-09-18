# Always-on container image for the bot. Used by Fly.io (fly.toml) or any
# Docker host. The image holds NO secrets — DISCORD_TOKEN arrives via the
# host's secret store (docs/access/deploy.md).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_PATH=/data/black_bloc.sqlite3

# libopus is what decodes what people say in a voice meeting (docs/info/minutes-design.md).
# discord.py bundles the DLL on Windows only; everywhere else it asks the system for it.
RUN apt-get update \
    && apt-get install --no-install-recommends -y libopus0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md ./
COPY black_bloc ./black_bloc
RUN pip install --no-cache-dir .

# The status page is served by this same app under one hostname (SITE_ROOT).
COPY site/public ./site/public

# SQLite lives on a mounted volume so it survives redeploys.
VOLUME ["/data"]

CMD ["python", "-m", "black_bloc"]
