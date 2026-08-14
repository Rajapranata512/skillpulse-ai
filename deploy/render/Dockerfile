FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=10000 \
    SKILLPULSE_INTERNAL_API_PORT=8000 \
    SKILLPULSE_API_RATE_LIMIT_PER_MINUTE=30

ENV SKILLPULSE_PUBLIC_HOST=0.0.0.0

WORKDIR /app

RUN addgroup --system skillpulse && adduser --system --ingroup skillpulse skillpulse

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY configs ./configs

RUN python -m pip install ".[api,ui]"

USER skillpulse
EXPOSE 10000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import urllib.request; response=urllib.request.urlopen('http://127.0.0.1:10000/_stcore/health', timeout=3); assert response.status == 200"

CMD ["python", "-m", "skillpulse.release.public_runtime"]
