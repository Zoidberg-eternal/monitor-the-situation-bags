FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY . .

EXPOSE 8402

CMD ["python", "-m", "uvicorn", "monitor.server:app", "--host", "0.0.0.0", "--port", "8402"]
