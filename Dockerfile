FROM python:3.12-slim

WORKDIR /app

# install uv
RUN pip install uv

# copy dependency files first
COPY pyproject.toml uv.lock ./

# install dependencies
RUN uv sync --frozen

# copy project
COPY . .

EXPOSE 8000

# CMD ["uv", "run", "uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.app:app --host 0.0.0.0 --port 8000"]
