FROM python:3.12-slim

WORKDIR /app

ENV APP_ENV=production HOST=0.0.0.0 PORT=5000 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 backend

COPY app ./app
COPY scripts ./scripts
COPY run.py ./
USER backend

EXPOSE 5000

CMD ["python", "run.py"]
