FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements-app.txt /app/requirements-app.txt

RUN python -m pip install --upgrade pip \
    && pip install -r /app/requirements-app.txt

COPY assistant /app/assistant

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "assistant.api.main:app", "--host", "0.0.0.0", "--port", "8000"]