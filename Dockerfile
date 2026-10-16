# The API image: Python 3.12 with the locked dependencies, the app, the
# migrations, the seed and the tests.
FROM python:3.12-slim

# gcc, libc6-dev and libpq-dev build psycopg2, which pgmigrate needs.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /bin/uv

WORKDIR /code

# Dependencies first, so code changes do not reinstall them.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
ENV PATH="/code/.venv/bin:$PATH"

COPY app app
COPY database database
COPY tests tests

EXPOSE 8000

# Create or update the tables, load the seed (safe to repeat), start the API.
CMD ["sh", "-c", "pgmigrate -d database -c \"$DATABASE_URL\" -t latest migrate && python -m database.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
