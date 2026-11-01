# INSURELAKE

**A governed insurance data lakehouse for Kenyan general insurance: medallion pipeline, actuarial reserving, fraud scoring, data quality, and two executive dashboards.**

[![Python](https://img.shields.io/badge/python-3.10-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/dashboard-streamlit-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](dashboard/app.py)
[![Next.js](https://img.shields.io/badge/dashboard-next.js-000000?style=flat-square&logo=nextdotjs&logoColor=white)](dashboard/web)
[![DuckDB](https://img.shields.io/badge/query-duckdb-FFF000?style=flat-square&logo=duckdb&logoColor=black)](api/main.py)
[![FastAPI](https://img.shields.io/badge/api-fastapi-009688?style=flat-square&logo=fastapi&logoColor=white)](api/main.py)
[![Storage](https://img.shields.io/badge/storage-local%20%7C%20s3--compatible-22d3ee?style=flat-square)](#configuration)
[![Status](https://img.shields.io/badge/pipeline-verified%20locally-34d399?style=flat-square)](#verified-status)

---

## Contents

- [Why this exists](#why-this-exists)
- [Verified status](#verified-status)
- [Architecture](#architecture)
- [Quickstart](#quickstart)
- [Repository layout](#repository-layout)
- [Data model](#data-model)
- [Pipeline stages](#pipeline-stages)
- [Serving layer](#serving-layer)
- [API reference](#api-reference)
- [Configuration](#configuration)
- [Make targets](#make-targets)
- [Design decisions](#design-decisions)
- [Known limitations](#known-limitations)
- [Roadmap](#roadmap)
- [Troubleshooting](#troubleshooting)

---

## Why this exists

General insurers in East Africa run on spreadsheets stapled to a core policy system. That works until someone asks three questions in the same meeting:

1. What is our loss ratio, by line, right now?
2. How much of what we are paying is fraudulent?
3. Are our reserves adequate, and by how much could they be wrong?

Answering those needs the same claims data arranged three different ways, with provenance you can defend to a regulator. This repo builds that arrangement end to end on one laptop: synthetic ingestion, a medallion lake, actuarial triage, fraud scoring, quality gates, and a dashboard that states its own confidence.

It is a portfolio project, but the constraints are real ones - Windows, no cloud account, no R toolchain, intermittent Docker - and the code reflects them.

---

## Verified status

Every badge in the dashboard header names a technology this project is *designed* to use. This table is the honest reconciliation.

| Component | Status | Evidence in repo |
|---|---|---|
| Synthetic data generation | **Works** | `data_generator/seed.py`, `data_generator/seed_local.py` |
| Bronze -> Silver transform | **Works** | `pipeline/bronze_to_silver.py` |
| Silver -> Gold star schema | **Works** | `pipeline/silver_to_gold.py` |
| Chain ladder / IBNR | **Works** | `actuarial/reserving/chain_ladder.py` |
| Data quality gate | **Works** | `governance/quality/quality_report.py` |
| Fraud model training | **Works** | `ml/fraud/train.py` -> `ml/models/fraud_xgb.pkl` |
| Read API (gold -> JSON) | **Works** | `api/main.py` |
| Streamlit dashboard | **Works** | `dashboard/app.py` |
| Next.js dashboard | **Works** | `dashboard/web/app/page.tsx` |
| Dual-mode storage (local/S3) | **Works** | `pipeline/_storage.py` |
| Kafka ingestion | **Not implemented** | `kafka-python` is in `requirements.txt`; no producer or consumer exists |
| Spark Structured Streaming | **Not implemented** | No Spark code; batch pandas transforms only |
| dbt models | **Not implemented** | Transforms are plain Python |
| Iceberg table format | **Not implemented** | Parquet files on local disk |
| Trino / OpenMetadata / MLflow | **Not implemented** | Dashboard badges are aspirational |
| Docker Compose stack | **Designed, unverified** | `docker-compose.yml` exists; Docker Desktop would not start on the build machine |

If a claim in this repo is not in the "Works" column, treat it as architecture, not delivery. The [Roadmap](#roadmap) says what it would take.

---

## Architecture

```
                        +------------------------------+
                        |   data_generator/seed.py     |
                        |   customers, policies,       |
                        |   claims, payments           |
                        +--------------+---------------+
                                       |
                                       v
  ============================ LANDING ============================
                                       |
                            data/raw/*.parquet
                                       |
                    +------------------v------------------+
                    |     pipeline/bronze_to_silver.py    |
                    |  typing, dedup, key validation      |
                    +------------------+------------------+
                                       |
                            data/silver/*.parquet
                                       |
                    +------------------v------------------+
                    |     pipeline/silver_to_gold.py      |
                    |  star schema, KPI marts             |
                    +------------------+------------------+
                                       |
  ============================ CURATED ============================
            |                          |                          |
            v                          v                          v
     data/gold/                gold/actuarial/            governance/
     fact_claims               ibnr_by_cohort             quality_report.json
     dim_customer              triangle                   (Great Expectations
     dim_policy                                             compatible shape)
     dim_provider
     dim_county
     county_kpi
     claims_development
     fact_payments
            |                          |                          |
            +--------------+-----------+--------------+-----------+
                           |                          |
                           v                          v
              +------------------------+   +----------------------+
              |      api/main.py       |   |  dashboard/app.py    |
              |  FastAPI + DuckDB      |   |  Streamlit           |
              |  gold -> JSON          |   +----------------------+
              +-----------+------------+
                          |
                          v   HTTP / JSON, CORS enabled
              +------------------------+
              |   dashboard/web/       |
              |   Next.js + Tailwind   |
              |   App Router, RSC      |
              +------------------------+
```

**Storage abstraction.** `pipeline/_storage.py` presents one `read`/`write` interface over either the local filesystem (`./data`) or any S3-compatible endpoint. Mode is chosen by `STORAGE_MODE` and resolved at import time, so every pipeline module is storage-agnostic. This is what lets the same code run on a laptop today and against MinIO or S3 later without edits.

**Medallion layers.** Bronze is append-only and untrusted. Silver is typed, deduplicated, and referentially checked. Gold is query-shaped: facts, dimensions, and pre-aggregated marts that a dashboard or an actuary can consume without joins.

---

## Quickstart

### Prerequisites

| Requirement | Version | Check |
|---|---|---|
| Python | 3.10+ | `python --version` |
| Node.js | 18.17+ (20.9+ on Next.js 16) | `node -v` |
| make | any GNU make | `make --version` |
| Docker | optional, not required | `docker --version` |

### Install

```bash
git clone <your-fork-url> insurelake
cd insurelake

python -m venv .venv
source .venv/Scripts/activate      # Windows Git Bash
# source .venv/bin/activate        # macOS / Linux

pip install -r requirements.txt
export STORAGE_MODE=local
export PYTHONUTF8=1
```

`STORAGE_MODE=local` keeps everything on disk. Without it the storage layer probes `localhost:9000` for MinIO and may pick the wrong backend.

### Run the batch pipeline

```bash
make seed         # write synthetic source data
make pipeline     # bronze -> silver -> gold
make actuarial    # chain ladder, IBNR, development triangle
make quality      # data quality gate -> governance/quality_report.json
make train        # fraud model -> ml/models/fraud_xgb.pkl
```

One-shot:

```bash
make pipeline actuarial quality train
```

Verify:

```bash
find data/gold -name '*.parquet' | wc -l     # expect >= 8
cat governance/quality_report.json           # expect overall_score near 1.0
```

### Serve

```bash
make api          # terminal 1 -> http://localhost:8000
make streamlit    # terminal 2 -> http://localhost:8501
make web          # terminal 3 -> http://localhost:3100
```

The Next.js app needs the API base URL to read live data:

```bash
cd dashboard/web
npm install
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev
```

Without that variable every panel renders deterministic fixtures. With it, each panel tries the live endpoint first and falls back to fixtures on timeout or 404, so the dashboard never renders empty.

---

## Repository layout

```
insurelake/
|-- Makefile                       one entry point per stage (.RECIPEPREFIX set for Windows)
|-- requirements.txt
|-- README.md
|
|-- data_generator/
|   |-- seed.py                    source-shaped data -> data/raw/
|   `-- seed_local.py              direct-to-silver convenience path
|
|-- pipeline/
|   |-- _storage.py                local <-> S3 abstraction, mode resolution
|   |-- bronze_to_silver.py        typing, dedup, key validation
|   `-- silver_to_gold.py          star schema + KPI marts
|
|-- actuarial/
|   `-- reserving/
|       `-- chain_ladder.py        triangle, CDFs, IBNR per cohort
|
|-- governance/
|   |-- quality/
|   |   `-- quality_report.py      completeness, validity, duplicates, orphans
|   `-- quality_report.json        generated by make quality
|
|-- ml/
|   |-- fraud/
|   |   `-- train.py               fraud model training
|   `-- models/
|       `-- fraud_xgb.pkl          artifact
|
|-- api/
|   `-- main.py                    FastAPI + DuckDB read layer
|
|-- dashboard/
|   |-- app.py                     Streamlit port
|   `-- web/                       Next.js executive control centre
|       |-- app/page.tsx
|       |-- components/
|       |   |-- panels.tsx         Panel, Kpi, Badge, Legend
|       |   |-- charts.tsx         hand-rolled SVG charts
|       |   `-- LiveEventTicker.tsx
|       `-- lib/
|           |-- queries.ts         typed fetchers + fixtures
|           `-- format.ts          KES / count / percent
|
`-- data/                          gitignored
    |-- raw/
    |-- bronze/
    |-- silver/
    `-- gold/
```

---

## Data model

### Silver

| Table | Grain | Key columns |
|---|---|---|
| `silver.customers` | one row per customer | `customer_id`, `county`, `segment` |
| `silver.policies` | one row per policy | `policy_id`, `customer_id`, `lob`, `premium` |
| `silver.claims` | one row per claim | `claim_id`, `policy_id`, `claim_amount`, `status`, `claim_date` |
| `silver.payments` | one row per payment | `payment_id`, `claim_id`, `channel`, `amount` |

### Gold

| Table | Grain | Used by |
|---|---|---|
| `gold.fact_claims` | claim | every claims panel, KPI cards |
| `gold.fact_payments` | payment | payments / M-PESA panel |
| `gold.dim_customer` | customer | joins, segment analysis |
| `gold.dim_policy` | policy | premium, LOB mix, loss ratio denominator |
| `gold.dim_provider` | provider | provider concentration |
| `gold.dim_county` | county | 47-county geography |
| `gold.county_kpi` | county | county risk map |
| `gold.claims_development` | cohort x development period | reserving triangle source |
| `gold/actuarial/ibnr_by_cohort` | cohort | IBNR by method |
| `gold/actuarial/triangle` | cohort x dev | development factors |
| `governance/quality_report.json` | check | trust gauge |

### Conventions

- **Currency** is Kenyan shillings, stored as `float64`, suffixed `_kes` in the API layer.
- **Dates** are ISO-8601. `claim_date` drives the trend and intensity charts.
- **`fraud_score`** is `0.0`-`1.0`, produced by `ml/fraud/train.py`, thresholded at `0.65` for "flagged" and `0.85` for "critical".
- **Status** is normalised to `OPEN | REVIEW | SETTLED | DECLINED` at the API boundary, so heterogeneous source spellings never reach the UI.

---

## Pipeline stages

### 1. Generation - `data_generator/seed.py`

Produces a realistic book: customers across all 47 counties, policies spanning seven lines of business, claims with a plausible development lag, and payments across M-PESA, bank transfer, card and cheque. Deliberately injects the failures the rest of the pipeline exists to catch - nulls, duplicate claim IDs, orphaned policy references, out-of-range amounts.

```bash
make seed
```

### 2. Bronze -> Silver - `pipeline/bronze_to_silver.py`

- Casts to declared dtypes, coercing failures to null rather than dropping rows silently
- Deduplicates on natural keys, retaining the latest write
- Validates foreign keys against the dimension it depends on
- Writes one Silver table per source entity

### 3. Silver -> Gold - `pipeline/silver_to_gold.py`

- Resolves facts and dimensions, backfilling missing dimension members as `Unknown`
- Builds `county_kpi` and `claims_development` as pre-aggregated marts
- Emits the star schema described above

### 4. Reserving - `actuarial/reserving/chain_ladder.py`

Classical chain ladder in Python, replacing an R path that could not be provisioned (`arrow` unavailable on the build machine):

1. Build the cumulative development triangle from `gold.claims_development`
2. Compute age-to-age link ratios per development period
3. Select development factors (volume-weighted, with a simple tail)
4. Derive CDFs to ultimate
5. IBNR = ultimate minus reported, per cohort

Outputs `ibnr_by_cohort` and `triangle`. **This is the single source of truth for the IBNR KPI.** The API derives Cape Cod and Bornhuetter-Ferguson from the same triangle rather than inventing them.

### 5. Quality - `governance/quality/quality_report.py`

| Check | Question |
|---|---|
| `claims_completeness` | Are required claim fields populated? |
| `customers_completeness` | Are required customer fields populated? |
| `payments_validity` | Are amounts positive and within bounds? |
| `duplicate_records` | Are natural keys unique? |
| `policy_orphans` | Does every claim reference a real policy? |

Writes `governance/quality_report.json` with an `overall_score` in `[0,1]` and per-check results. The report shape is Great Expectations-compatible, so it can be swapped for a real GE suite without changing consumers.

> **Caveat.** A passing run against empty Silver is vacuous - every check passes on zero rows. Always confirm row counts before trusting a green score.

### 6. Fraud model - `ml/fraud/train.py`

Gradient-boosted classifier over engineered claim features (amount, development lag, provider concentration, county, LOB, channel). Trains on synthetic labels and writes `ml/models/fraud_xgb.pkl`.

The model *trains*; it does not yet *score a stream*. `fraud_score` currently reaches Gold via the batch path. This is the largest gap between the dashboard's story and the repo's behaviour.

---

## Serving layer

### Read API - `api/main.py`

FastAPI over DuckDB. DuckDB reads parquet directly, so there is no warehouse to stand up and no load step - the gold files *are* the database.

Design points:

- **Tolerant readers.** Every column lookup tries a list of aliases (`claim_amount`, `amount`, `incurred`, `total_incurred`). Schema drift degrades a panel instead of 500-ing the page.
- **404 over fabrication.** If a source table is absent, the endpoint returns 404. The client falls back to fixtures. The API never invents a number.
- **CORS scoped** to the dashboard origins.
- **No writes.** The API is read-only by construction.

```bash
curl -s localhost:8000/health | python -m json.tool
curl -s "localhost:8000/claims/recent?limit=3" | python -m json.tool
curl -s localhost:8000/lakehouse/layers | python -m json.tool
```

### Dashboards

Two independent front ends over the same API. They exist to compare, not to duplicate.

| | Streamlit (`dashboard/app.py`) | Next.js (`dashboard/web`) |
|---|---|---|
| Port | 8501 | 3100 |
| Effort to change | minutes, Python | hours, TypeScript |
| Fidelity to reference design | close | exact |
| Charts | Plotly | hand-rolled SVG |
| Data | live API or fixture | live API or fixture |
| Best for | internal iteration | portfolio presentation |

**Next.js specifics.** Server components fetch on the server; `LiveEventTicker` is the only client component, rotating the event feed every 2.6s. Charts are plain SVG rather than `recharts` - few runtime dependencies, no peer-dependency surface, no build-time network access. Fonts use CSS stacks for the same reason; swap in `next/font` if the exact typefaces matter more than offline builds.

---

## API reference

| Method | Path | Source of truth | Fallback |
|---|---|---|---|
| GET | `/health` | filesystem paths | - |
| GET | `/executive/summary` | `gold/fact_claims`, `dim_policy`, `ibnr_by_cohort` | fixtures |
| GET | `/executive/premium-vs-claims` | `dim_policy.inception_date`, `fact_claims.claim_date` | fixtures |
| GET | `/executive/narrative` | computed from the three above | fixtures |
| GET | `/fraud/distribution` | `fact_claims.fraud_score` | fixtures |
| GET | `/geo/county-risk` | `fact_claims` joined `dim_county`, else `county_kpi` | 47 generated counties |
| GET | `/portfolio/lob-mix` | `dim_policy.lob` | fixtures |
| GET | `/payments/breakdown` | `fact_payments.channel` | fixtures |
| GET | `/lakehouse/layers` | parquet scan of `data/{bronze,silver,gold}` | fixtures |
| GET | `/governance/quality` | `governance/quality_report.json` | fixtures |
| GET | `/claims/recent?limit=N` | `fact_claims` sorted by date | fixtures |
| GET | `/claims/intensity` | `fact_claims` grouped by month | fixtures |
| GET | `/actuarial/ibnr-by-method` | `gold/actuarial/ibnr_by_cohort` | fixtures |
| GET | `/events/ticker` | mtimes of parquet, quality and model artifacts | fixtures |

Interactive schema: `http://localhost:8000/docs`.

### Reserving methods

`/actuarial/ibnr-by-method` returns:

- **Chain Ladder** - always present, the central estimate, `se_kes` from the cohort variance
- **Cape Cod** - derived from the empirical loss ratio, present whenever reported and premium are both populated
- **Bornhuetter-Ferguson** - requires an a priori loss ratio the data does not contain

BF is **omitted rather than faked**. Supply one explicitly:

```bash
INSURLAKE_APRIORI_ELR=0.68 make api
```

The dashboard then renders all three bars. Unset, it renders two. A missing bar is a data availability signal, not a bug.

---

## Configuration

| Variable | Default | Effect |
|---|---|---|
| `STORAGE_MODE` | `auto` | `local` uses `./data`; `s3` uses the S3-compatible endpoint; `auto` probes MinIO and falls back |
| `PYTHONUTF8` | unset | Set to `1` on Windows to avoid cp1252 encode errors on non-ASCII output |
| `INSURLAKE_ROOT` | repo root | Overrides where the API looks for `data/` |
| `INSURLAKE_APRIORI_ELR` | `0` | A priori loss ratio; non-zero enables Bornhuetter-Ferguson |
| `NEXT_PUBLIC_API_BASE` | unset | API origin for the Next.js app; unset means fixtures only |

Set the first two in every shell:

```bash
export STORAGE_MODE=local
export PYTHONUTF8=1
```

---

## Make targets

| Target | Does |
|---|---|
| `make help` | List every target |
| `make check` | Verify Python, packages, and storage mode |
| `make seed` | Generate synthetic source data |
| `make pipeline` | Bronze -> Silver -> Gold |
| `make actuarial` | Chain ladder, triangle, IBNR |
| `make quality` | Run quality gate, write report |
| `make train` | Train the fraud model |
| `make submit-claim` | Push one claim through the transform path |
| `make api` | FastAPI on `:8000` with reload |
| `make web` | Next.js on `:3100` |
| `make streamlit` | Streamlit on `:8501` |
| `make up` / `make down` | Docker Compose stack (unverified on Windows) |
| `make clean` | Remove generated data and artifacts |

The Makefile sets `.RECIPEPREFIX = >` so recipes use `>` instead of a literal tab. A tab-vs-space mismatch on Windows is a silent, confusing failure, and `>` is visible in review.

---

## Design decisions

**DuckDB instead of a warehouse.** The gold layer is parquet. DuckDB queries parquet with zero load step, zero infrastructure, and full SQL. Anything heavier would be a claim this project cannot support on a laptop.

**Tolerant column resolution.** Real insurance systems rename fields constantly. Every endpoint tries a list of aliases, so a renamed column degrades one panel rather than breaking the page. The cost is a little verbosity; the benefit is a dashboard that survives schema drift.

**Fixtures as an explicit fallback, not a default.** Every panel can render without a backend. That is a deliberate choice for a portfolio piece that must load on a stranger's machine - but the fallback is *visible in code*, and the API returns 404 rather than a plausible fake. A number on this dashboard is either from gold or from a fixture you can point at.

**Python reserving, not R.** The R path required the `arrow` package, which was not installable in this environment. Rather than ship a broken script, the chain ladder was implemented in Python. Reserving is too important to leave dependent on an unprovisioned toolchain.

**Hand-rolled SVG charts.** `recharts` and friends bring peer-dependency risk and build-time weight. Six chart primitives cover the whole dashboard and install in seconds on a cold machine.

**`.RECIPEPREFIX` over tabs.** Cosmetic in isolation, decisive on Windows where editors silently convert tabs and `make` then fails with `missing separator` on a line that looks correct.

---

## Known limitations

Stated plainly, because a README that hides these is worse than none.

1. **No streaming.** Fraud scores are computed in batch. Kafka is listed in the stack and installed in `requirements.txt` but no producer or consumer exists. The live ticker reflects file modification times, not event flow.
2. **No table format.** Tables are directories of parquet. There is no Iceberg catalog, so no time travel, no schema evolution guarantees, no snapshot isolation.
3. **No transformation framework.** Transforms are plain Python. There are no dbt models, no tests-by-default, no lineage graph.
4. **A priori loss ratio is absent.** Bornhuetter-Ferguson needs one; the synthetic data has none. It is opt-in via environment variable.
5. **Period deltas are zero.** Gold holds one snapshot, so `deltas` in `/executive/summary` all return `0.0`. Two pipeline runs and a snapshot table would make them real.
6. **Retention is fixture-only.** Nothing in gold records gross vs net written premium, so that KPI is illustrative. The endpoint omits the key; the TS overlay keeps the fixture. Visible in code, not hidden.
7. **Docker path unverified.** `docker-compose.yml` was never executed - Docker Desktop would not start on the build machine (`pipe/dockerDesktopLinuxEngine`). Everything documented here was run natively.
8. **Fraud model is synthetic.** Trained on injected labels, so its scores validate the plumbing, not the discrimination. Real performance would need labelled outcomes.
9. **County risk is exposure-ranked.** It is a composite of claims volume and incurred, normalised to the top county. It is not a geographic map and not a calibrated probability of loss.
10. **Single-node.** No partitioning strategy, no compaction, no concurrent-writer handling. Fine at 10k claims, unproven beyond.

---

## Roadmap

Ordered by what most narrows the gap between the dashboard's claims and the repo's behaviour.

**1. Kafka ingestion path**
Producer replays `data/raw/` onto `insurance.claims`; consumer writes micro-batches to Bronze with exactly-once semantics via idempotent keys. Makes the ticker real and unblocks everything below.

**2. Streaming fraud scoring**
Consume from Silver, score each micro-batch with the existing model, stamp `fraud_score` before the Gold write. Turns the fraud panel from a batch snapshot into a live feed.

**3. Iceberg table format**
Replace parquet directories with Iceberg tables over a local catalog. Gains time travel (which makes period deltas real) and schema evolution (which makes the alias-tolerant API less necessary).

**4. Snapshot table for deltas**
Write a dated `gold.snapshot_kpi` each run. `/executive/summary` then diffs the last two and the delta arrows become true.

**5. dbt for transforms**
Port `silver_to_gold.py` to dbt models with tests. Gains lineage, docs, and a real test suite.

**6. Great Expectations suite**
Promote `quality_report.py` to a full GE suite with the same output contract, so consumers never notice.

**7. Docker Compose parity**
Get the stack running so `make up` is documented with the same confidence as `make pipeline`. Includes MinIO, so `STORAGE_MODE=s3` gets exercised.

---

## Troubleshooting

**`silver empty` or zero-row gold**
The seed wrote to `data/raw/` while the storage layer resolved to S3. Confirm the mode, then re-run:

```bash
export STORAGE_MODE=local
rm -rf data/bronze data/silver data/gold
make seed && make pipeline
```

**`UnicodeEncodeError: 'charmap' codec can't encode character`**
The terminal is cp1252 and the source emitted a non-ASCII character (an arrow, em dash, or ellipsis). Set `export PYTHONUTF8=1` and keep source ASCII-only.

**`volumes.dbt Additional property volumes is not allowed`**
A service block was nested under `volumes:` instead of `services:` in `docker-compose.yml`. Indentation, not content.

**`pipe/dockerDesktopLinuxEngine: The system cannot find the file specified`**
Docker Desktop is not running. Nothing in the batch pipeline needs it - use `STORAGE_MODE=local` and skip `make up`.

**`No rule to make target 'train'`**
No Makefile in the working directory, or recipes indented with spaces. This Makefile uses `.RECIPEPREFIX = >`; recipes must start with `>`, not a tab.

**Streamlit: `File does not exist: dashboard/app.py`**
Wrong working directory. Run from the repo root.

**Next.js build tries to reach the network**
`next/font/google` was reintroduced. Revert to CSS font stacks in `app/layout.tsx` and `tailwind.config.ts`.

**Dashboard panels show fixture values**
`NEXT_PUBLIC_API_BASE` is unset or the API is down. Check `curl localhost:8000/health`, then restart with the variable set. The panels are working as designed - they prefer live data and fall back rather than fail.

**`make quality` reports 1.0 but data is empty**
Every check passes on zero rows. Confirm with `find data/silver -name '*.parquet' | wc -l` before trusting the score.

---

## Attribution

Built against the visual specification of the INSURELAKE executive control centre. Synthetic data models Kenyan general insurance: 47 counties, seven lines of business, M-PESA-dominant payment mix, KES-denominated amounts.

Built to run on one Windows laptop with no cloud account. That constraint is the reason for most of the design choices above, and the reason the limitations section is as long as it is.

---

**Start here:** `make seed && make pipeline && make actuarial && make quality && make train && make api`
