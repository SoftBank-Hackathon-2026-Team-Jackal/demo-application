FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN useradd --uid 10001 --create-home appuser
USER appuser
EXPOSE 8080
CMD ["uvicorn", "demo_api.main:app", "--host", "0.0.0.0", "--port", "8080"]
