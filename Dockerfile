FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY data ./data

EXPOSE 8000

# Загрузчик идемпотентен: при повторном старте данные не дублируются.
CMD ["sh", "-c", "python -m app.load_data && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
