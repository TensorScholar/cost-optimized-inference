FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*

# Copy project
COPY pyproject.toml README.md /app/
COPY src /app/src

# Install
RUN pip install --upgrade pip poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

EXPOSE 8000
CMD ["uvicorn", "inference_engine.adapters.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
