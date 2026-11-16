FROM apache/airflow:3.0.0-python3.12

# dbt and the pipeline code live in their own virtualenv so their dependencies
# never clash with Airflow's pinned ones.
COPY --chown=airflow:root requirements-pipeline.txt /tmp/requirements-pipeline.txt
RUN python -m venv /home/airflow/pitchline-venv \
 && /home/airflow/pitchline-venv/bin/pip install --no-cache-dir -r /tmp/requirements-pipeline.txt

ENV PITCHLINE_HOME=/opt/pitchline \
    PITCHLINE_PYTHON=/home/airflow/pitchline-venv/bin/python \
    PITCHLINE_DBT=/home/airflow/pitchline-venv/bin/dbt
