# Run `make help` to see what each target does.
.DEFAULT_GOAL := help
PY ?= python
export PITCHLINE_ROOT ?= data
export PITCHLINE_BRONZE ?= ../data/bronze
export PITCHLINE_WAREHOUSE ?= ../warehouse/pitchline.duckdb
export DBT_PROFILES_DIR ?= .

help:  ## Show this help
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

setup:  ## Install everything (run inside a virtualenv)
	pip install -r requirements-dev.txt && pip install -e .

test:  ## Unit tests (ingest, storage, bronze, health, DAG shape, app smoke test)
	$(PY) -m pytest -q

lint:  ## Style check
	ruff check .

ingest:  ## Download raw StatsBomb files (skips files you already have)
	$(PY) -m pitchline ingest

bronze:  ## Convert raw JSON to Parquet
	$(PY) -m pitchline bronze

dbt:  ## Build the warehouse and run all 44 data tests
	mkdir -p warehouse && cd dbt && dbt build

health:  ## Write the dbt test summary the app's Data health page reads
	$(PY) -m pitchline dbt-summary

all: ingest bronze dbt health  ## Whole pipeline, end to end

sample:  ## Quick run: 3 matches, same steps (what CI does)
	$(PY) -m pitchline all --config config/ci_sources.yml --limit 3
	mkdir -p warehouse && cd dbt && dbt build
	$(PY) -m pitchline dbt-summary

docs:  ## Generate and open dbt docs (lineage graph)
	cd dbt && dbt docs generate && dbt docs serve

app:  ## Start the Streamlit app
	streamlit run app/streamlit_app.py
