FROM apache/airflow:3.3.0

ARG AIRFLOW_VERSION=3.3.0

COPY requirements-airflow.txt /tmp/requirements-airflow.txt

RUN pip install \
    "apache-airflow==${AIRFLOW_VERSION}" \
    -r /tmp/requirements-airflow.txt