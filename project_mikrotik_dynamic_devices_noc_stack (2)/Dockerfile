# Builder
FROM python:3.11-slim as builder
RUN apt-get update && apt-get install -y --no-install-recommends gcc libssl-dev build-essential && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip
RUN /opt/venv/bin/pip install -r requirements.txt

# Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY . /app
EXPOSE 9102 5000
CMD ["python", "run_api_collector.py", "--config", "mi_config.json"]
