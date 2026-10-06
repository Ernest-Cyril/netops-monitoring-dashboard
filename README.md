# NetOps — Network & Infrastructure Monitoring Dashboard

A Python/Django web application that simulates how a Network Operations Centre (NOC) or infrastructure team could monitor servers, routers, fibre links, cloud nodes, data-centre infrastructure and databases from one dashboard. It includes automatic threshold detection, incident creation and incident management.

> **Demo environment:** all infrastructure, metrics, IP addresses and incidents are fictional and simulated. NetOps does not connect to, scan or ping any real network.

---

## Overview

NetOps gives an operations engineer one screen that answers:

- What infrastructure do we have, and where is it?
- Which assets are Healthy, Warning, Critical or Offline?
- What is the overall uptime?
- Which assets have high latency or high CPU?
- Which incidents are open, what caused them and what should be done?
- Can I track an incident from **Open → Investigating → Resolved**?

## Problem

Infrastructure teams look after many different kinds of asset: routers, fibre links, servers, cloud nodes and databases. If each asset is checked by hand, problems are found late, the same issue gets reported many times, and nobody has a single view of overall health.

## Solution

NetOps stores every asset and its latest metrics in a database. A **rule-based monitoring engine** compares each metric with defined thresholds, works out each asset's overall status, and **automatically creates an incident**, with a severity and a recommended action, when a threshold is breached. The engine **never creates duplicate incidents** for a problem that is already being tracked. Engineers then manage each incident through its lifecycle from the dashboard.

## Features

| Area | What it does |
|---|---|
| Dashboard | Dark NOC-style overview with 6 live KPI cards (total, healthy, warning, critical, active incidents, average uptime) |
| Infrastructure table | Name, type, location, IP, status badge, CPU, memory, latency, uptime, last checked; metric values coloured by threshold |
| Asset detail page | Full metrics, threshold reminders, current rule-based recommendation, incident history, Investigate/Resolve buttons |
| Threshold engine | CPU, memory and latency thresholds; the worst metric decides the overall status; unreachable assets are Offline |
| Automatic incidents | High CPU / High Memory / High Latency / Asset Offline, with severity and recommended action |
| Duplicate prevention | One active incident per asset per problem; a Warning incident is **escalated** to Critical instead of being duplicated |
| Incident management | Mark as Investigating, Resolve (sets `resolved_at`), Recently Resolved list |
| Simulate Network Event | Randomly degrades 1–2 assets (Warning / Critical / Offline / recovery); every event includes at least one problem |
| Reset Demo | Restores the original 8 assets, metrics and 2 starting incidents; numbering restarts at INC-0001 |
| Charts (Chart.js) | Network Latency by Asset, Infrastructure Status Distribution, CPU by Compute Asset, all using live database data |
| Django Admin | Assets and incidents with list columns, filters, search and inline incident history |
| Tests | 22 automated Django tests covering thresholds, incidents, duplicates, lifecycle, simulation and reset |

## Technology Stack

- **Python 3.9+**: application language
- **Django** (4.2 LTS on Python 3.9; 5.2 LTS on Python 3.10+): web framework, ORM, admin, templates
- **SQLite**: file-based database (`db.sqlite3`)
- **Bootstrap 5 + Bootstrap Icons**: responsive layout and components (CDN)
- **Chart.js 4**: charts (CDN)
- **HTML / CSS / vanilla JavaScript**: templates, NOC theme, chart rendering

No Docker, Redis, Celery, Node.js, external APIs or paid services.

## Architecture

```
Browser (HTML + Bootstrap + Chart.js)
        │  HTTP GET (pages) / POST (actions, CSRF-protected)
        ▼
Django URLs ──► views.py  (request/response only)
                    │
                    ▼
               services.py  (business logic: thresholds, incidents,
                    │         recommendations, simulation, seed/reset)
                    ▼
               models.py  ── Django ORM ──►  SQLite (db.sqlite3)
```

- **Model → View → Template:** `models.py` defines the data, `views.py` collects it, and the templates in `templates/` display it.
- Business rules live in `monitoring/services.py`, so they can be unit-tested, and the simulated metrics could later be replaced by real telemetry without changing the UI.

## Monitoring Rules

| Metric | Healthy | Warning | Critical |
|---|---|---|---|
| CPU | < 70% | 70–85% | > 85% |
| Memory | < 75% | 75–90% | > 90% |
| Latency | < 100 ms | 100–250 ms | > 250 ms |

- An unreachable asset is **Offline**, which creates a Critical "Asset Offline" incident.
- **The most severe metric wins.** For example, CPU Critical + latency Healthy gives Critical overall.
- CPU and memory are not monitored for Fibre Links or the Data Centre (shown as "—").
- Recommendations are simple **rule-based** if/then mappings (not AI).

## Installation

Requires Python 3.9 or newer and Git.

**Windows (one click):** double-click `setup_netops.bat`. It creates the virtual environment, installs dependencies, runs migrations, loads demo data, runs the checks and tests, and writes `logs\setup_log.txt`.

**Manual (any OS):**

```bash
python -m venv venv
# Windows PowerShell:  .\venv\Scripts\Activate.ps1
# macOS/Linux:         source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser      # for Django Admin
```

## Running the Application

**Windows:** double-click `start_netops.bat`. It opens your browser automatically.

**Manual:**

```bash
python manage.py runserver
```

- Dashboard: <http://127.0.0.1:8000/>
- Admin: <http://127.0.0.1:8000/admin/>
- Stop the server: `CTRL + C`

Useful commands:

```bash
python manage.py seed_demo           # create demo assets if missing (safe to repeat)
python manage.py seed_demo --reset   # same as the Reset Demo button
python manage.py test monitoring     # run the automated tests
```

## Demo Workflow

1. Open the dashboard and point out the KPI cards, the infrastructure table and the charts.
2. Click **SIMULATE NETWORK EVENT**. A banner explains what changed and which incident was created.
3. Show the new incident in **Active Incidents**: severity, affected asset, description and recommended action.
4. Click the asset name to open its detail page and show its metrics, recommendation and history.
5. Click **Mark as Investigating**. The status changes and is saved in SQLite.
6. Click **Resolve**. The incident leaves Active Incidents and appears in Recently Resolved with a resolved time.
7. Click **RESET DEMO** to rehearse again.

## Project Structure

```
manage.py                 Django command-line entry point
requirements.txt          Python dependencies
setup_netops.bat          Windows one-click setup (venv, install, migrate, seed, test)
start_netops.bat          Windows one-click server start
netops/                   Django PROJECT (settings, root URLs, WSGI/ASGI)
monitoring/               Django APP
  models.py               InfrastructureAsset, Incident
  services.py             Monitoring engine, recommendations, simulation, seed/reset
  views.py                Dashboard, asset detail, simulate, reset, investigate, resolve
  urls.py                 App URL patterns
  admin.py                Django Admin configuration
  tests.py                22 automated tests
  templatetags/netops_tags.py   metric_level filter (colours values by threshold)
  management/commands/seed_demo.py   `python manage.py seed_demo [--reset]`
  migrations/             Database schema history
templates/                base.html, monitoring/dashboard.html, asset_detail.html, _incident_table.html
static/                   css/styles.css (NOC theme), js/dashboard.js (Chart.js)
```

## Future Improvements

- Real **SNMP** polling of routers and switches
- **ICMP/ping** reachability checks against approved internal targets
- Integration with real **monitoring APIs** and cloud provider metrics
- **Prometheus** as the metrics source and **Grafana** for long-term dashboards
- **Authentication** and **role-based access control** (viewer / engineer / admin)
- **Email / SMS / Slack** alerting and on-call escalation
- **Historical time-series storage** for trends and SLA reporting
- **Automated background monitoring** (scheduled checks with a task queue)
- **Docker** packaging and **cloud deployment** with PostgreSQL
- A **REST API** for integrations
- **Predictive anomaly detection** on historical metrics

## Disclaimer

This project is an independent portfolio prototype created for educational and demonstration purposes. Infrastructure names, metrics, IP addresses, incidents, and locations are fictional demo data and do not represent the systems of any real organisation.
