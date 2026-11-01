# INSURLAKE — works on Windows Git Bash, macOS, Linux.
# .RECIPEPREFIX = > avoids the tabs-vs-spaces trap entirely.
.RECIPEPREFIX = >
export STORAGE_MODE ?= local
SHELL := /bin/bash

PYTHON ?= python
COMPOSE ?= docker compose

.PHONY: help check train seed pipeline actuarial quality submit-claim stream dashboard up down clean

help:
> @echo "INSURLAKE targets:"
> @echo "  make check         - verify environment"
> @echo "  make train         - train fraud model (needs Python only)"
> @echo "  make seed          - generate fake Kenya insurance data"
> @echo "  make pipeline      - bronze -> silver -> gold"
> @echo "  make actuarial     - chain ladder / IBNR"
> @echo "  make quality       - data quality report"
> @echo "  make submit-claim  - POST a claim to the API"
> @echo "  make up            - docker: minio + kafka + api"
> @echo "  make down          - docker: stop everything"

check:
> @echo "---- environment ----"
> @command -v $(PYTHON) >/dev/null || (echo "❌ python not found"; exit 1)
> @$(PYTHON) --version
> @command -v docker >/dev/null && docker --version || echo "⚠️  docker not on PATH"
> @echo "---- files ----"
> @test -f ml/fraud/train.py       && echo "✅ ml/fraud/train.py"       || echo "⚠️  ml/fraud/train.py MISSING"
> @test -f data_generator/seed.py  && echo "✅ data_generator/seed.py"  || echo "⚠️  data_generator/seed.py MISSING"
> @test -f requirements.txt        && echo "✅ requirements.txt"        || echo "⚠️  requirements.txt MISSING"

train: check
> $(PYTHON) -m ml.fraud.train

seed:
> $(PYTHON) -m data_generator.seed

pipeline:
> $(PYTHON) -m pipeline.bronze_to_silver
> $(PYTHON) -m pipeline.silver_to_gold

actuarial:
> $(PYTHON) -m actuarial.reserving.chain_ladder

quality:
> $(PYTHON) -m governance.quality.quality_report

submit-claim:
> curl -s -X POST http://localhost:8000/claims \
>   -H 'Content-Type: application/json' \
>   -d '{"policy_id":"POL-00001-0","customer_id":"CUS-000001","claim_type":"Motor","claim_amount":850000,"claim_date":"2026-10-29","county":"Kisumu","provider_id":"PRV-0012","vehicle_id":"VEH-00123"}'

up:
> $(COMPOSE) up -d minio minio-init kafka api

down:
> $(COMPOSE) down

clean:
> rm -rf ml/models/*.pkl governance/quality_report.json

api:
> $(PYTHON) -m uvicorn api.main:app --reload --port 8000

web:
> cd dashboard/web && npm run dev

streamlit:
> $(PYTHON) -m streamlit run dashboard/app.py
