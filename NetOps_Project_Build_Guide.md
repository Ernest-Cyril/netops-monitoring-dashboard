# NetOps — Project Build Guide

**Project:** NetOps — Network & Infrastructure Monitoring Dashboard
**Author:** Ernest-Cyril Divine Onyeze
**Built:** 6 October 2026, on Windows (Python 3.9.13, Django 4.2.30, Git 2.55)
**Purpose of this guide:** to explain, from a beginner's point of view, exactly how NetOps was built, how every part works, and how to explain it confidently in an interview.

> **Read this first: what is real and what is simulated**
>
> - **Implemented and working:** the Django web app, SQLite database, dashboard, KPIs, charts, threshold engine, automatic incidents, duplicate prevention, incident lifecycle, simulation, reset, asset pages, admin, and 22 automated tests.
> - **Simulated:** every metric (CPU, memory, latency, uptime), every asset and every IP address. NetOps does **not** connect to, ping or scan any real network.
> - **Future improvements only:** SNMP, Prometheus, Grafana, real alerts, authentication for the dashboard, Docker, cloud deployment, and so on. These are **not** built.

---

## Table of Contents

1. Understanding the Problem
2. Understanding the Technology Stack
3. Development Environment Setup
4. Creating the Django Project
5. Database Design
6. Infrastructure Monitoring Concepts
7. Creating Demo Infrastructure
8. Building the Monitoring Engine
9. Automatic Incident Detection
10. Building the Dashboard Backend
11. Building the Dashboard Interface
12. Building the Charts
13. Asset Detail Page
14. Simulate Network Event
15. Incident Management
16. Reset Demo
17. Django Admin
18. Testing and Debugging
19. Complete Application Architecture
20. Complete NetOps Workflow
21. Running the Finished Project
22. Interview Demonstration Guide
23. Likely Technical Interview Questions
24. Limitations
25. Future Improvements
26. Beginner Revision Cheat Sheets

---

## Phase 1 — Understanding the Problem

### What is NetOps?
NetOps is a web application that shows the health of an organisation's IT infrastructure on one screen. That infrastructure includes routers, fibre links, servers, cloud nodes, a data centre and a database. It watches each asset's numbers (metrics), decides whether each asset is **Healthy, Warning, Critical or Offline**, and opens an **incident** (a trouble ticket) automatically when something goes wrong.

### What business problem does it address?
A company that depends on its network (an ISP, a bank, a telecom operator, a logistics firm) loses money and customer trust every minute something is down. Problems include:

- **Too many things to watch:** dozens or thousands of devices.
- **Slow detection:** a human checking devices one by one finds problems late.
- **Noise:** the same problem reported again and again (duplicate alerts).
- **No ownership:** nobody knows whether someone is already working on an issue.

NetOps answers this with **automatic detection** (thresholds), **automatic ticketing** (incidents), **de-duplication**, and a simple **lifecycle** (Open → Investigating → Resolved).

### Who would use it?
- **NOC engineers:** watch the dashboard and respond to incidents.
- **Infrastructure / network engineers:** investigate and fix problems.
- **Team leads / managers:** read the KPIs (how many critical assets, average uptime).

### What is a Network Operations Centre (NOC)?
A NOC is a team (often a room full of screens) that monitors an organisation's networks and infrastructure **24/7**. Its job is to **detect, triage, escalate and track** problems before customers notice them. NetOps imitates the main screen a NOC engineer would look at.

### Why does infrastructure monitoring matter?
- You cannot fix what you cannot see.
- Early warnings (for example, CPU at 78%) let teams act **before** an outage (CPU at 99%, server crashes).
- Uptime is often promised to customers in an **SLA (Service Level Agreement)**, so it must be measured.

### What the prototype DOES
- Stores 8 fictional assets and their metrics in SQLite.
- Classifies every asset against fixed thresholds.
- Creates incidents automatically, with severity and a recommended action, and prevents duplicates.
- Lets you mark incidents Investigating and Resolved (saved to the database).
- Simulates network events on demand, and resets to a known demo state.
- Shows KPIs, a health table, three charts and per-asset detail pages.

### What the prototype does NOT do
- It does not collect real telemetry, ping devices, use SNMP or connect to Prometheus.
- It does not run checks in the background on a timer. Checks run when you click **Simulate** or **Reset**, or run `seed_demo`.
- It does not send emails, SMS or Slack alerts.
- It does not require a login for the dashboard (only Django Admin requires a login).
- It is not deployed to the internet; it runs locally.

### Why simulated data?
1. **Safety and ethics:** scanning or pinging networks you do not own is not acceptable.
2. **Confidentiality:** real infrastructure details must never appear in a portfolio.
3. **Demonstration:** simulation lets you *cause* a problem on demand in an interview.
4. **Good design:** because the logic is in `services.py`, the simulated data source could be replaced by a real one later without rewriting the dashboard.

---

## Phase 2 — Understanding the Technology Stack

| Technology | What it is | Why we chose it | Where NetOps uses it |
|---|---|---|---|
| **Python** | A popular, readable programming language | Easy to read, huge ecosystem, the language Django is written in | All backend logic: `models.py`, `services.py`, `views.py`, tests |
| **Django** | A "batteries-included" Python web framework | Gives us URL routing, an ORM, templates, a free admin panel, CSRF security and testing out of the box | The whole web application |
| **SQLite** | A database stored in a single file | Zero setup, built into Python, perfect for a prototype | `db.sqlite3` stores assets and incidents |
| **HTML** | The structure of web pages | Every web page needs it | `templates/*.html` |
| **CSS** | Styles (colours, spacing, layout) | Gives the dark NOC look | `static/css/styles.css` |
| **Bootstrap 5** | A CSS framework of ready-made components (grid, tables, alerts, buttons) | Professional, responsive layout quickly | Grid, tables, alerts and buttons in all templates (stored locally in `static/vendor`) |
| **JavaScript** | The programming language that runs in the browser | Needed to draw charts | `static/js/dashboard.js` |
| **Chart.js** | A JavaScript charting library | Simple, good-looking charts with little code | Latency bar chart, status doughnut, CPU bar chart |

### How they communicate: Frontend → Backend → Database

```
[Browser]  HTML + CSS + Bootstrap + Chart.js        ← FRONTEND (what the user sees)
    │  1. User opens http://127.0.0.1:8000/ or clicks a button (HTTP request)
    ▼
[Django]   urls.py → views.py → services.py          ← BACKEND (Python logic)
    │  2. View asks the ORM for data / services change data
    ▼
[SQLite]   db.sqlite3                                 ← DATABASE (stored data)
    │  3. Data returned to Django
    ▼
[Django]   renders a template into finished HTML (+ JSON for charts)
    │  4. HTTP response sent back
    ▼
[Browser]  displays the page; dashboard.js reads the JSON and draws charts
```

- The **browser never talks to SQLite directly**. Only Django does, through the **ORM** (Object-Relational Mapper), which turns Python code like `InfrastructureAsset.objects.all()` into SQL like `SELECT * FROM monitoring_infrastructureasset`.
- **Bootstrap, Bootstrap Icons, Chart.js and the fonts are stored inside the project** in `static/vendor/` and served by Django like our own CSS and JS. The page makes **no requests to the internet**, so NetOps works with Wi-Fi switched off. (They were first loaded from a CDN, a Content Delivery Network; see Problem 5 in Phase 18 for why that changed.)

---

## Phase 3 — Development Environment Setup

### What was on the laptop
| Tool | Check command | Result found |
|---|---|---|
| Python | `python --version` | Python 3.9.13 |
| Git | `git --version` | git version 2.55.0.windows.5 |
| VS Code | (opened from Start menu) | Installed; used to view and edit the files |
| Terminal | PowerShell / Command Prompt | Built into Windows |

### Project folder
`C:\Users\Dell\Documents\NetOps — Network & Infrastructure Monitoring Dashboard`

All project files live directly in this folder (where `manage.py` is).

### The one-click setup script: `setup_netops.bat`
Because the project was built partly through automation, the setup steps were put in a Windows batch file. A **batch file** (`.bat`) is a text file of Command Prompt commands that run in order when you double-click it. It saves all its output to `logs\setup_log.txt`, so errors can be read afterwards.

Here is what it runs, and what each command means:

| Command | What it does | Why |
|---|---|---|
| `python -m venv venv` | Creates a **virtual environment** in a folder called `venv` | Keeps NetOps's packages separate from other Python projects |
| `venv\Scripts\python.exe -m pip install --upgrade pip` | Updates pip, Python's package installer | Avoids old-installer problems |
| `venv\Scripts\python.exe -m pip install -r requirements.txt` | Installs every package listed in `requirements.txt` | Installs Django |
| `venv\Scripts\python.exe manage.py makemigrations monitoring` | Turns `models.py` into a migration file | Describes the database tables |
| `venv\Scripts\python.exe manage.py migrate` | Creates or updates the tables in `db.sqlite3` | Builds the database |
| `venv\Scripts\python.exe manage.py seed_demo` | Loads the 8 demo assets | Demo data |
| `call _local_create_admin.bat` | Creates the admin user (local only) | Django Admin login |
| `venv\Scripts\python.exe manage.py check` | Django's built-in configuration check | Finds mistakes early |
| `venv\Scripts\python.exe manage.py test monitoring -v 2` | Runs the 22 automated tests | Proves the logic works |

> Calling `venv\Scripts\python.exe` directly is the same as "activating" the virtual environment and then typing `python`. It always uses the project's own Python and packages.

### What is a virtual environment, and why use one?
A **virtual environment** is a private copy of Python for one project. Without it, every project on your laptop shares one set of packages. If project A needs Django 3 and NetOps needs Django 4.2, they would conflict. With `venv`, NetOps has its own Django and nothing else is affected. The `venv` folder is **not** committed to Git, because anyone can recreate it from `requirements.txt`.

### Activating the venv manually (PowerShell)
```powershell
cd "C:\Users\Dell\Documents\NetOps — Network & Infrastructure Monitoring Dashboard"
.\venv\Scripts\Activate.ps1
```
Your prompt then starts with `(venv)`. If PowerShell says *"running scripts is disabled on this system"*, run this once:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
Alternatively, use Command Prompt (`cmd`) and run `venv\Scripts\activate.bat`.

### `requirements.txt`
```
Django>=4.2,<5.3
tzdata>=2024.1
```
- **Django>=4.2,<5.3**: pip picks the newest Django your Python supports. On Python 3.9 that is **Django 4.2 LTS** (installed: 4.2.30); on Python 3.10+ it is **Django 5.2 LTS**. The NetOps code works on both.
- **tzdata**: time-zone data. Windows doesn't ship the IANA time-zone database, and Django needs it for `Africa/Lagos`.
- Django automatically pulls in its own dependencies: `asgiref`, `sqlparse` and `typing_extensions`.

### Git
`_local_git_commit.bat` ran:
```
git init -b main      # create a new repository with a branch called main
git add -A            # stage every file (except those in .gitignore)
git commit -m "..."   # save a snapshot
```
First commit: `b5676a9`, 32 files.

### `.gitignore`: what is NOT committed and why
| Ignored | Reason |
|---|---|
| `venv/` | Large and recreatable from `requirements.txt` |
| `__pycache__/`, `*.pyc` | Python's compiled cache files |
| `db.sqlite3` | The live database changes with every click. Recreate it with `migrate` + `seed_demo` (or `setup_netops.bat`) |
| `.env` | Would hold secrets in a real project |
| `logs/` | Local script output |
| `_local_*` | Local-only helpers (for example the admin-creation script, which contains the demo password) |
| `.vscode/`, `.idea/` | Personal editor settings |

**Decision about `db.sqlite3`:** excluding it keeps the repository clean and avoids committing changing data. Setup stays easy because `seed_demo` (and `setup_netops.bat`) rebuild the exact demo state in seconds.

---

## Phase 4 — Creating the Django Project

### Django PROJECT vs Django APP
| | Project (`netops/`) | App (`monitoring/`) |
|---|---|---|
| What | The whole website's **configuration** | One **feature area** with its own models, views and URLs |
| Contains | `settings.py`, root `urls.py`, `wsgi.py`, `asgi.py` | `models.py`, `views.py`, `services.py`, `urls.py`, `admin.py`, `tests.py` |
| Analogy | The building | A department inside the building |

A project can contain many apps (for example, a future `alerts` app or `accounts` app). NetOps has one app: `monitoring`.

### Final folder structure
```
NetOps — Network & Infrastructure Monitoring Dashboard/
├── manage.py                    ← command-line entry point
├── requirements.txt
├── README.md
├── .gitignore
├── setup_netops.bat             ← one-click setup (Windows)
├── start_netops.bat             ← one-click start (Windows)
├── netops/                      ← PROJECT package
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── monitoring/                  ← APP package
│   ├── models.py
│   ├── services.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   ├── tests.py
│   ├── templatetags/netops_tags.py
│   ├── management/commands/seed_demo.py
│   └── migrations/0001_initial.py
├── templates/
│   ├── base.html
│   └── monitoring/
│       ├── dashboard.html
│       ├── asset_detail.html
│       └── _incident_table.html
└── static/
    ├── css/styles.css
    ├── css/fonts.css            ← @font-face rules for the local fonts
    ├── js/dashboard.js
    └── vendor/                  ← local copies of third-party libraries
        ├── bootstrap/           (bootstrap.min.css, bootstrap.bundle.min.js, v5.3.3)
        ├── bootstrap-icons/     (bootstrap-icons.min.css + fonts/, v1.11.3)
        ├── chartjs/             (chart.umd.min.js, v4.4.4)
        └── fonts/               (Inter 400–700, JetBrains Mono 400/600, .woff2)
```
(`venv/`, `db.sqlite3` and `logs/` are created on your laptop but not committed.)

### `manage.py`
A small script Django gives every project. It sets `DJANGO_SETTINGS_MODULE=netops.settings` and passes your command to Django. You use it for everything: `runserver`, `migrate`, `test`, `seed_demo`, `createsuperuser`.

### `netops/settings.py`: the important lines
| Setting | Value | Meaning |
|---|---|---|
| `INSTALLED_APPS` | Django's built-ins + `"django.contrib.humanize"` + `"monitoring"` | Tells Django our app exists (otherwise its models, templates and commands are ignored) |
| `TEMPLATES["DIRS"]` | `[BASE_DIR / "templates"]` | Where to find `base.html` and the other templates |
| `DATABASES` | SQLite at `BASE_DIR / "db.sqlite3"` | Our database file |
| `TIME_ZONE` | `"Africa/Lagos"` | Times are shown in Lagos time |
| `STATICFILES_DIRS` | `[BASE_DIR / "static"]` | Where the CSS and JS live |
| `MESSAGE_TAGS` | Django's `ERROR` → Bootstrap `danger` | Gives flash messages the right Bootstrap colour |
| `SECRET_KEY` | Read from the `DJANGO_SECRET_KEY` env var, with a dev-only fallback | Signs sessions and CSRF tokens. Must be secret in production |
| `DEBUG` | `True` by default | Detailed error pages for development. Must be `False` in production |
| `ALLOWED_HOSTS` | `127.0.0.1`, `localhost`, `testserver` | Which host names Django will answer to |

### Project `urls.py` vs app `urls.py`
- `netops/urls.py` (the **front door**):
  ```python
  urlpatterns = [
      path("admin/", admin.site.urls),
      path("", include("monitoring.urls")),
  ]
  ```
  `/admin/` goes to Django Admin; everything else goes to the monitoring app. This file also renames the admin header to "NetOps Administration".
- `monitoring/urls.py` (the **app's own routes**):
  | URL | View | Method |
  |---|---|---|
  | `/` | `dashboard` | GET |
  | `/assets/<id>/` | `asset_detail` | GET |
  | `/simulate/` | `simulate_event` | POST |
  | `/reset/` | `reset_demo` | POST |
  | `/incidents/<id>/investigate/` | `incident_investigate` | POST |
  | `/incidents/<id>/resolve/` | `incident_resolve` | POST |

  `app_name = "monitoring"` lets templates write `{% url 'monitoring:dashboard' %}` instead of hard-coding paths.

### `monitoring/apps.py`
Registers the app with Django and gives it the human-readable name "Infrastructure Monitoring" (shown in Admin).

---

## Phase 5 — Database Design

### Key ideas
- **Model:** a Python class that describes a database table. Each attribute is a **field** (a column).
- **Primary key (`id`):** a unique number Django adds to every row automatically (`BigAutoField`).
- **Foreign key:** a column that points to a row in another table. This is how an incident knows which asset it belongs to.
- **Migration:** a file Django generates that describes how to create or change tables. `makemigrations` writes it; `migrate` applies it to `db.sqlite3`. Our migration is `monitoring/migrations/0001_initial.py`, which creates two tables.
- **`db.sqlite3`:** the actual database file in the project folder.
- **TextChoices:** a list of allowed values. For example, `status` can only be `HEALTHY`, `WARNING`, `CRITICAL` or `OFFLINE`. The database stores the code (`"WARNING"`); the screen shows the label ("Warning").

### Model 1: `InfrastructureAsset` (table `monitoring_infrastructureasset`)
| Field | Type | Meaning / example |
|---|---|---|
| `id` | BigAutoField (PK) | 1, 2, 3… |
| `name` | CharField(120), **unique** | "Lagos Core Router". Unique, so seeding can never create duplicates |
| `asset_type` | CharField + choices | SERVER, ROUTER, FIBRE_LINK, CLOUD_NODE, DATA_CENTRE, DATABASE |
| `location` | CharField | "Lekki", "Victoria Island", "Ikeja", "Lagos" |
| `ip_address` | GenericIPAddressField(IPv4) | "10.10.0.1". Django validates the format |
| `status` | CharField + choices, default HEALTHY | HEALTHY / WARNING / CRITICAL / OFFLINE, **calculated by the engine** |
| `cpu_usage` | FloatField, **nullable** | 41.0 (%). Empty for a fibre link or data centre |
| `memory_usage` | FloatField, **nullable** | 52.0 (%) |
| `latency` | FloatField, nullable | 12.0 (ms). Empty when the asset is offline |
| `uptime` | FloatField, default 100 | 99.98 (% availability over 30 days) |
| `is_reachable` | BooleanField, default True | False means the asset is Offline |
| `last_checked` | DateTimeField | When the engine last evaluated it |
| `created_at` | DateTimeField(auto_now_add) | When the row was created |

Extra code on the model:
- `get_absolute_url()` returns `/assets/<id>/`. Templates use it for links.
- `has_compute_metrics` is True when CPU or memory exists.
- `Meta.ordering = ["name"]` lists assets alphabetically.

### Model 2: `Incident` (table `monitoring_incident`)
| Field | Type | Meaning / example |
|---|---|---|
| `id` | BigAutoField (PK) | Shown as **INC-0001** by the `reference` property |
| `asset` | **ForeignKey → InfrastructureAsset**, `on_delete=CASCADE`, `related_name="incidents"` | Which asset has the problem |
| `severity` | WARNING / CRITICAL | How serious it is |
| `metric` | CPU / MEMORY / LATENCY / OFFLINE | **Which problem** it is. Used for duplicate prevention |
| `title` | CharField | "High CPU Utilisation" |
| `description` | TextField | "CPU on Cloud Node 02 is 78%, at or above the warning threshold of 70%." |
| `recommended_action` | TextField | The rule-based recommendation |
| `status` | OPEN / INVESTIGATING / RESOLVED, default OPEN | Lifecycle stage |
| `created_at` | DateTimeField (default now) | When it was raised |
| `resolved_at` | DateTimeField, nullable | Filled in when resolved |

Extra code:
- `ACTIVE_STATUSES = [OPEN, INVESTIGATING]`: "active" means not yet resolved.
- `reference` returns `INC-` plus the id padded to 4 digits.
- `is_active` is True if the status is Open or Investigating.
- `Meta.ordering = ["-created_at"]` puts the newest first.

> **Note:** the original spec listed the Incident fields without `metric`. We added `metric` because it makes duplicate prevention simple and exact: "is there an active incident for *this asset* and *this metric*?"

### The relationship: InfrastructureAsset → Incident (one-to-many)
```
InfrastructureAsset (1) ───────< Incident (many)
"Backup Server" (id 8)    INC-0001  High Network Latency   (asset_id = 8)
                          INC-0005  Asset Offline          (asset_id = 8)
```
- One asset can have **many** incidents; each incident belongs to **one** asset.
- From an incident: `incident.asset.name` gives "Backup Server".
- From an asset: `asset.incidents.all()` lists all its incidents (thanks to `related_name="incidents"`).
- `on_delete=CASCADE`: if an asset is deleted, its incidents are deleted too.

---

## Phase 6 — Infrastructure Monitoring Concepts

| Term | Simple meaning | In NetOps |
|---|---|---|
| **CPU usage** | How busy the processor is (%) | `cpu_usage`. **Simulated** |
| **Memory usage** | How much RAM is in use (%) | `memory_usage`. **Simulated** |
| **Latency** | Delay for data to travel and come back, in milliseconds | `latency`. **Simulated** |
| **Uptime** | % of time the asset was available (here, over 30 days) | `uptime`. **Simulated** |
| **Downtime** | Time it was *not* available (100% − uptime) | Offline events reduce uptime slightly |
| **IP address** | A device's network address | Private ranges only: `10.x`, `172.16.x`, `192.168.x` |
| **Server** | A computer that provides services | "Application Server 01", "Backup Server" |
| **Router** | Forwards traffic between networks | "Lagos Core Router" |
| **Fibre link** | An optical cable connection between sites | "Fibre Link — Lekki to Victoria Island" (latency only) |
| **Cloud node** | A virtual machine in a cloud platform | "Cloud Node 01/02" |
| **Data centre** | A facility housing servers and network equipment | "Lekki Data Centre" (latency only) |
| **Database** | A system that stores data | "Customer Database" |
| **Metric** | A measured number | CPU, memory, latency, uptime |
| **Threshold** | The limit where a metric becomes a problem | For example, CPU ≥ 70% is Warning and > 85% is Critical |
| **Healthy** | All metrics within limits | Green badge |
| **Warning** | At least one metric in the warning band | Amber badge |
| **Critical** | At least one metric beyond the critical limit | Red badge |
| **Offline** | Asset not responding | Grey badge; `is_reachable=False` |
| **Incident** | A recorded problem that needs attention | `Incident` row, e.g. INC-0003 |
| **Severity** | How serious an incident is | Warning or Critical (Offline counts as Critical) |
| **Telemetry** | Metrics automatically collected from devices | In NetOps, **simulated** by `simulate_network_event()` |
| **Packet loss** | Data packets that never arrive | Not measured. Mentioned in the latency recommendation |
| **NOC** | Network Operations Centre: the 24/7 monitoring team | The users NetOps is designed for |
| **SLA** | A promise of availability, e.g. 99.9% | Why uptime matters (not implemented as a feature) |

---

## Phase 7 — Creating Demo Infrastructure

### The demo assets (`DEMO_ASSETS` in `monitoring/services.py`)
| Asset | Type | Location | IP | CPU | Mem | Latency | Uptime | Initial status |
|---|---|---|---|---|---|---|---|---|
| Lagos Core Router | Router | Lagos | 10.10.0.1 | 41 | 52 | 12 ms | 99.98 | Healthy |
| Lekki Data Centre | Data Centre | Lekki | 10.20.0.10 | — | — | 8 ms | 99.99 | Healthy |
| Cloud Node 01 | Cloud Node | Victoria Island | 172.16.1.11 | 48 | 61 | 22 ms | 99.95 | Healthy |
| Cloud Node 02 | Cloud Node | Victoria Island | 172.16.1.12 | **78** | 66 | 25 ms | 99.91 | **Warning** (CPU) |
| Fibre Link — Lekki to Victoria Island | Fibre Link | Lekki | 10.30.0.2 | — | — | 18 ms | 99.97 | Healthy |
| Application Server 01 | Server | Ikeja | 192.168.10.21 | 55 | 63 | 31 ms | 99.93 | Healthy |
| Customer Database | Database | Lekki | 192.168.20.5 | 37 | 69 | 14 ms | 99.99 | Healthy |
| Backup Server | Server | Ikeja | 192.168.10.40 | 29 | 47 | **138 ms** | 99.62 | **Warning** (latency) |

Two assets deliberately **start in Warning**, so the dashboard opens with two realistic incidents (INC-0001 High Network Latency on Backup Server, and INC-0002 High CPU Utilisation on Cloud Node 02) rather than looking empty.

### Why private IPs and fictional names?
`10.0.0.0/8`, `172.16.0.0/12` and `192.168.0.0/16` are **private address ranges** (RFC 1918). They are never routed on the public internet, so they cannot identify any real organisation's public systems. All names are invented.

### The `seed_demo` management command
**File:** `monitoring/management/commands/seed_demo.py`.
A **management command** is a custom `manage.py` command. Django finds any file in `<app>/management/commands/` automatically.
```
python manage.py seed_demo          # create missing demo assets (safe to repeat)
python manage.py seed_demo --reset  # restore the original demo state (same as RESET DEMO)
```
It calls `services.seed_demo_data(reset=...)` and prints, for example:
`Demo data ready: 8 assets (8 newly created), 2 active incidents.`

### `seed_demo_data()` step by step
```python
for data in DEMO_ASSETS:
    if reset:
        InfrastructureAsset.objects.update_or_create(name=data["name"], defaults=defaults)
    else:
        InfrastructureAsset.objects.get_or_create(name=data["name"], defaults=defaults)
run_all_checks()
```
- `get_or_create` means "find the asset with this name, or create it if it doesn't exist." It never makes a second copy.
- `update_or_create` (reset mode) means "find it and overwrite its metrics with the originals."
- `run_all_checks()` runs the monitoring engine, so statuses and starting incidents match the thresholds.
- The whole function is wrapped in `@transaction.atomic`: either everything succeeds or nothing is saved.

### What "idempotent" means
An operation is **idempotent** if running it once or ten times leaves the same result. Running `seed_demo` repeatedly still gives exactly 8 assets. This works because `name` is unique and we use `get_or_create`, and the engine's duplicate prevention stops repeat incidents. The test `test_seed_is_idempotent` proves it.

---

## Phase 8 — Building the Monitoring Engine

**File:** `monitoring/services.py`. This is the most important file in NetOps.

### Why a separate `services.py`?
`views.py` should only deal with web requests (receive a request, return a page). The **business rules**, such as "what counts as Critical?", live in `services.py` because:
1. They can be **unit-tested** without a browser (see `ThresholdClassificationTests`).
2. They can be **reused**: the same engine runs from the Simulate button, the Reset button and the `seed_demo` command.
3. Real telemetry (SNMP, Prometheus) could later feed the **same** engine.

This pattern is called a **service layer** (separation of concerns).

### The thresholds
```python
THRESHOLDS = {
    Metric.CPU: (70.0, 85.0),       # percent
    Metric.MEMORY: (75.0, 90.0),    # percent
    Metric.LATENCY: (100.0, 250.0), # milliseconds
}
```
Each pair is `(warning_from, critical_above)`.

| Metric | Healthy | Warning | Critical |
|---|---|---|---|
| CPU | below 70% | 70% to 85% | above 85% |
| Memory | below 75% | 75% to 90% | above 90% |
| Latency | below 100 ms | 100 to 250 ms | above 250 ms |

### Function 1: `classify_value(value, warning_from, critical_above)`
```python
def classify_value(value, warning_from, critical_above):
    if value is None:            # e.g. CPU of a fibre link -> not applicable
        return Status.HEALTHY
    if value > critical_above:
        return Status.CRITICAL
    if value >= warning_from:
        return Status.WARNING
    return Status.HEALTHY
```
The **order matters**: it checks Critical first, then Warning, then defaults to Healthy.

Worked examples:
- CPU = 92%: is 92 > 85? **Yes**, so **Critical**.
- CPU = 78%: is 78 > 85? No. Is 78 ≥ 70? **Yes**, so **Warning**.
- CPU = 85%: is 85 > 85? No. Is 85 ≥ 70? Yes, so **Warning** (85 itself is still Warning; Critical is *above* 85).
- Latency = 138 ms: is 138 > 250? No. Is 138 ≥ 100? Yes, so **Warning**.
- Latency = 337 ms: is 337 > 250? Yes, so **Critical**.
- CPU = None (fibre link): not applicable, so **Healthy**.

### Function 2: `classify_metric(metric, value)`
Looks up the thresholds for that metric and calls `classify_value`. For example, `classify_metric(Metric.CPU, 92)` returns `CRITICAL`.

### Function 3: `worst_status(statuses)`: the most severe wins
```python
STATUS_RANK = {HEALTHY: 0, WARNING: 1, CRITICAL: 2, OFFLINE: 3}

def worst_status(statuses):
    return max(statuses, key=lambda s: STATUS_RANK[s], default=Status.HEALTHY)
```
Each status gets a number, and `max()` picks the highest.
- `[Healthy, Critical, Warning]` gives **Critical**.
- `[Healthy, Warning]` gives **Warning**.
- `[]` (no problems) gives **Healthy**.

**Why the most severe wins:** an asset is only as healthy as its worst part. A server with perfect latency but 95% CPU is about to fail, so the operator must see Critical, not an average.

### Function 4: `find_breaches(asset)`
Returns a list of `Breach` objects, one per metric outside healthy limits:
```python
if not asset.is_reachable:
    return [Breach(Metric.OFFLINE, Status.OFFLINE, None)]
for metric, value in ((CPU, asset.cpu_usage), (MEMORY, asset.memory_usage), (LATENCY, asset.latency)):
    level = classify_metric(metric, value)
    if level != Status.HEALTHY:
        breaches.append(Breach(metric, level, value))
```
A `Breach` is a small **dataclass** (a simple container) with `metric`, `level` and `value`. It also:
- works out `severity`: Warning stays Warning; Critical and Offline become **Critical**.
- writes a `describe(asset)` sentence, e.g. *"Latency on Backup Server is 138 ms, at or above the warning threshold of 100 ms."*

### Function 5: `determine_status(asset)`
`worst_status([b.level for b in find_breaches(asset)])`: the overall status in one line.

### How each status is reached
```
is_reachable == False                         → OFFLINE
any metric above its critical limit           → CRITICAL
any metric at/above warning (none critical)   → WARNING
otherwise                                     → HEALTHY
```

---

## Phase 9 — Automatic Incident Detection

### The 10-step flow (with the real function names)
| Step | What happens | Where |
|---|---|---|
| 1 | Metrics change | `apply_scenario()` (simulation) or `seed_demo_data()` |
| 2 | NetOps evaluates the asset | `run_monitoring_check(asset)` |
| 3 | Threshold breaches are found | `find_breaches(asset)` |
| 4 | Asset status changes (worst wins) and `last_checked` is updated; asset saved | `run_monitoring_check` → `worst_status` → `asset.save()` |
| 5 | The problem is identified | `Breach.metric` (CPU / MEMORY / LATENCY / OFFLINE) |
| 6 | An incident is created (if not a duplicate) | `create_incident_if_needed(asset, breach)` |
| 7 | Severity assigned | `Breach.severity` |
| 8 | Recommended action attached | `get_recommendation(metric)` → `RECOMMENDATIONS` dict |
| 9 | Stored in SQLite | `Incident.objects.create(...)` |
| 10 | Dashboard displays it | `views._active_incidents()` → `_incident_table.html` |

### `run_monitoring_check(asset)`
```python
previous_status = asset.status
breaches = find_breaches(asset)
asset.status = worst_status([b.level for b in breaches])
asset.last_checked = timezone.now()
asset.save()
for breach in breaches:
    incident, created = create_incident_if_needed(asset, breach)
    ...
return result    # CheckResult: previous/new status, created incidents, duplicates skipped
```
The `CheckResult` is what the Simulate view turns into the coloured message banner.

### Rule-based recommendations (NOT AI)
```python
RECOMMENDATIONS = {
  CPU:     "Review high-utilisation processes and available compute capacity. Consider scaling resources if utilisation remains elevated.",
  MEMORY:  "Review memory-intensive processes and available memory capacity. Check for memory leaks and consider adding capacity if usage stays high.",
  LATENCY: "Check network connectivity, packet loss, routing, and upstream link health.",
  OFFLINE: "Verify device connectivity and power status. Escalate to the infrastructure team if the asset remains unreachable.",
}
```
This is a simple **lookup table**: if the problem is X, recommend Y. It is deterministic and explainable. **Do not call it AI.**

Incident titles: High CPU Utilisation, High Memory Utilisation, High Network Latency, Asset Offline.

### Duplicate incident prevention: `create_incident_if_needed()`
```python
existing = Incident.objects.filter(
    asset=asset, metric=breach.metric, status__in=Incident.ACTIVE_STATUSES
).order_by("-created_at").first()

if existing:
    if breach is CRITICAL and existing is WARNING:
        existing.severity = CRITICAL          # escalate instead of duplicating
        existing.description = ... + " (Escalated from Warning.)"
        existing.save(...)
    return existing, False                    # no new incident

incident = Incident.objects.create(...)       # otherwise create a new one
return incident, True
```
In plain English: **before creating an incident, check whether an Open or Investigating incident already exists for the same asset and the same problem.** If yes, don't create another. If the problem got worse (Warning to Critical), **upgrade** the existing incident's severity instead.

**Why it matters:**
- Without it, every check would create another identical ticket. That is "alert fatigue": engineers start ignoring alerts.
- One problem should mean one ticket, with one owner and one history.
- Once an incident is **Resolved**, a new breach *can* create a fresh incident, because the old one is no longer active (tested in `test_new_incident_allowed_after_resolution`).
- When an asset recovers, its incident is **left open** for the operator to resolve manually, as the spec requires. A human confirms the fix.

**Proof in the live app (6 Oct 2026):** the fibre link was Critical with INC-0005 open. The next simulation pushed its latency to 111.5 ms, and the banner read: *"An existing active incident already tracks this problem (duplicate prevented)."*

---

## Phase 10 — Building the Dashboard Backend

**File:** `monitoring/views.py`. The view function is `dashboard(request)`.

### How Django fetches data from SQLite
```python
assets = list(InfrastructureAsset.objects.all())
```
The ORM turns this into `SELECT ... FROM monitoring_infrastructureasset ORDER BY name`. Each row becomes a Python `InfrastructureAsset` object.

### KPI calculations: `get_kpis()`
All six KPIs are calculated **live** in one database query using **aggregation**:
```python
counts = InfrastructureAsset.objects.aggregate(
    total=Count("id"),
    healthy=Count("id", filter=Q(status=Status.HEALTHY)),
    warning=Count("id", filter=Q(status=Status.WARNING)),
    critical=Count("id", filter=Q(status=Status.CRITICAL)),
    offline=Count("id", filter=Q(status=Status.OFFLINE)),
    avg_uptime=Avg("uptime"),
)
counts["active_incidents"] = Incident.objects.filter(status__in=Incident.ACTIVE_STATUSES).count()
counts["avg_uptime"] = round(counts["avg_uptime"] or 0, 2)
```
| KPI | Calculation |
|---|---|
| Total Assets | Count of all assets |
| Healthy / Warning / Critical Assets | Count where status = … (`Q` is a filter condition) |
| Offline (shown under Critical) | Count where status = OFFLINE |
| Active Incidents | Incidents with status Open **or** Investigating |
| Average Uptime | `AVG(uptime)` rounded to 2 decimals |

Nothing is hard-coded. The test `test_dashboard_kpis_match_database` checks the numbers.

### Active incidents query: `_active_incidents()`
Filters Open + Investigating incidents, uses `select_related("asset")` (fetches each incident's asset in the **same** query, avoiding the "N+1 queries" problem), and sorts **Critical first, then newest** using a `Case/When` expression.

### Passing data to the template
```python
context = {
    "assets": assets,
    "kpis": kpis,
    "active_incidents": _active_incidents(),
    "resolved_incidents": ...[:5],          # 5 most recently resolved
    "chart_data": build_chart_data(assets, kpis),
    "thresholds": services.THRESHOLDS,
}
return render(request, "monitoring/dashboard.html", context)
```
`render()` combines the template with the **context** (a dictionary) and returns HTML. In the template, `{{ kpis.total }}` becomes `8`.

### Important rule: viewing never changes data
The dashboard view is **read-only**. Refreshing the page does **not** run the engine and cannot create incidents (`test_dashboard_refresh_does_not_create_incidents`). Only POST actions change data.

---

## Phase 11 — Building the Dashboard Interface

### `templates/base.html`: the shared layout
- Loads Bootstrap 5, Bootstrap Icons, our `fonts.css` (Inter and JetBrains Mono) and our `styles.css`, all **from `static/`** with `{% static '...' %}`. Nothing is loaded from the internet.
- `data-bs-theme="dark"` turns on Bootstrap's dark mode.
- **Navbar:** NETOPS logo and title, the subtitle "Network & Infrastructure Monitoring", a pulsing **DEMO ENVIRONMENT** pill, and an Admin link.
- **Messages (floating notifications):** loops over Django's flash messages and shows each as a dismissible Bootstrap alert (`alert-success`, `alert-warning`, `alert-danger`, `alert-info`) inside a `.message-stack` container that is **fixed to the bottom-left of the screen** (`position: fixed` in `styles.css`). Because it floats, the notification is visible even when the page reopens scrolled down to the incidents table (`#incidents`) after Investigate or Resolve. It sits at the bottom-left so it never covers the Simulate/Reset buttons (top-right) or the Resolve buttons (right). A small script closes the notifications automatically after **12 seconds**; the X closes them at once.
- `{% block content %}` is where each page inserts its own content. This is **template inheritance**: write the layout once, reuse it everywhere.
- Footer disclaimer: "All infrastructure, metrics and incidents are fictional, simulated demo data."

### `templates/monitoring/dashboard.html`: sections, top to bottom
1. **Heading + action buttons.** Each button is inside a `<form method="post">` with `{% csrf_token %}`:
   - **SIMULATE NETWORK EVENT** posts to `/simulate/`.
   - **RESET DEMO** posts to `/reset/`, with a JavaScript `confirm()` pop-up so it can't be clicked by accident.
2. **KPI cards:** six Bootstrap columns (`col-6 col-md-4 col-xl-2`): 2 per row on phones, 3 on tablets, 6 on desktops.
3. **Infrastructure Health table:** `{% for asset in assets %}` makes one row per asset, with:
   - an asset name **link** to `{{ asset.get_absolute_url }}`
   - a **status badge**: `<span class="status-badge status-{{ asset.status|lower }}">`, so `CRITICAL` becomes the CSS class `status-critical` (red)
   - **coloured metrics**: `metric-{{ asset.cpu_usage|metric_level:'CPU' }}` colours the value amber or red if it breaches a threshold
   - "—" when a metric is not applicable (`{% if asset.cpu_usage is not None %}`)
4. **Three chart canvases** (Phase 12).
5. **Active Incidents:** `{% include "monitoring/_incident_table.html" ... %}`.
6. **Recently Resolved:** the last 5 resolved incidents with created and resolved times.
7. `{{ chart_data|json_script:"chart-data" }}`: chart data for JavaScript.

### `_incident_table.html`: a reusable partial
Used on **both** the dashboard and the asset page (written once, included twice). It shows ID, asset, severity badge, title + description, status, created time, recommended action, and buttons:
- **Mark as Investigating**: shown only when the status is Open.
- **Resolve**: shown when the status is not Resolved.

Each button posts a hidden `next` field so you return to the same page afterwards.

### Custom template filter: `monitoring/templatetags/netops_tags.py`
```python
@register.filter
def metric_level(value, metric):
    if value is None:
        return "na"
    return services.classify_metric(metric, value).lower()
```
The template **reuses the same threshold engine** to decide colours. Thresholds are defined in one place only.

### `static/css/styles.css`
Defines colour tokens (`--healthy` green, `--warning` amber, `--critical` red, `--offline` grey, `--investigating` purple), the KPI cards with a coloured left bar, panels, dark tables, status badges, metric colours, and mobile tweaks (`@media (max-width: 576px)`).

### How template variables insert database data
`{{ asset.ip_address }}` → `10.10.0.1`. `{{ asset.get_status_display }}` → "Warning" (the label for code `WARNING`). `{{ asset.last_checked|date:"d M H:i:s" }}` → "06 Oct 15:10:17". Django **auto-escapes** variables, so data can never inject HTML.

---

## Phase 12 — Building the Charts

### Charts implemented
1. **Network Latency by Asset:** a bar chart; bars coloured green/amber/red by the latency thresholds. Offline assets have no bar (null), and the tooltip says "Offline — no data".
2. **Infrastructure Status Distribution:** a doughnut chart of Healthy / Warning / Critical / Offline counts.
3. **CPU by Compute Asset:** a horizontal bar chart (0–100%) for assets that have CPU data, coloured by the CPU thresholds.

### Complete data flow
```
SQLite (assets table)
  → Django view: build_chart_data(assets, kpis) builds Python lists/dicts
  → Template: {{ chart_data|json_script:"chart-data" }}
        produces <script id="chart-data" type="application/json">{...}</script>
  → Browser: dashboard.js →  JSON.parse(document.getElementById("chart-data").textContent)
  → Chart.js: new Chart(canvas, {type: "bar", data: ...})
  → Chart drawn
```
`build_chart_data()` returns:
```python
{
  "latency": {"labels": [...names], "values": [...latency], "statuses": [...]},
  "status":  {"labels": ["Healthy","Warning","Critical","Offline"], "values": [counts...]},
  "cpu":     {"labels": [...], "values": [...]},   # only assets with CPU
  "thresholds": {"latency_warning": 100, "latency_critical": 250, "cpu_warning": 70, "cpu_critical": 85},
}
```
### Why `json_script`?
It is Django's **safe** way to pass data to JavaScript: it escapes characters such as `<` so data can never break out of the script tag (it prevents XSS). **No chart value is hard-coded in JavaScript.** Even the colour thresholds come from Python.

### `static/js/dashboard.js` highlights
- Exits quietly if the data or Chart.js is missing.
- Sets dark-theme defaults (`Chart.defaults.color`, `borderColor`).
- `colourFor(value, warningFrom, criticalAbove)` mirrors the Python threshold logic for bar colours.
- `shortLabel()` shortens long asset names on the axes, while tooltips show the full name.

---

## Phase 13 — Asset Detail Page

### Request journey
```
Browser clicks "Backup Server"  →  GET /assets/8/
  → netops/urls.py: "" → include("monitoring.urls")
  → monitoring/urls.py: path("assets/<int:pk>/", views.asset_detail)  (pk = 8)
  → views.asset_detail(request, pk=8)
       asset = get_object_or_404(InfrastructureAsset, pk=8)   # 404 page if not found
       incidents = asset.incidents.all()                       # via the ForeignKey
       recommendations = services.get_current_recommendations(asset)
  → render("monitoring/asset_detail.html", context)
  → Browser shows the page
```
`<int:pk>` is a **URL converter**: it captures the number from the URL and passes it to the view.

### What the page shows
- **Back to dashboard** link, the asset name and a large status badge.
- **Asset Information:** type, location, IP, reachability, last checked, date added.
- **Current Metrics** tiles: CPU, memory, latency, uptime, each with its threshold reminder ("warn ≥70 · crit >85") and a coloured border when breached. For fibre links and the data centre, a note explains that only latency is monitored.
- **Recommended Action (rule-based):** recommendations for the asset's **current** breaches, or "All metrics are within thresholds. No action required."
- **Incidents for this Asset:** the full history (all statuses), with working Investigate/Resolve buttons that return you to this page.

---

## Phase 14 — Simulate Network Event

This is the main demonstration feature.

### The complete sequence
| # | Stage | Exact code |
|---|---|---|
| 1 | User clicks **SIMULATE NETWORK EVENT** | `<form method="post" action="{% url 'monitoring:simulate_event' %}">` in `dashboard.html` |
| 2 | Browser sends `POST /simulate/` with the CSRF token | Django's `CsrfViewMiddleware` checks the token |
| 3 | Django routes the request | `monitoring/urls.py` → `views.simulate_event` (decorated with `@require_POST`) |
| 4 | Simulation logic runs | `services.simulate_network_event()` (inside `@transaction.atomic`) |
| 5 | Assets selected | 1 asset, or 2 assets (50% chance): `random.sample(assets, count)` |
| 6 | Scenario chosen | First asset: `PRIMARY_SCENARIOS` = warning 40 / critical 45 / offline 15. Second asset: `SECONDARY_SCENARIOS` = recover 50 / warning 30 / critical 20 |
| 7 | Metrics changed | `apply_scenario(asset, scenario)` |
| 8 | Thresholds evaluated | `run_monitoring_check(asset)` → `find_breaches` |
| 9 | Status determined | `worst_status(...)`, and `asset.save()` writes to SQLite |
| 10 | Incident created if necessary | `create_incident_if_needed` (with duplicate prevention) |
| 11 | Message built | `views.simulate_event` creates one message per affected asset using `format_html` (safe) |
| 12 | Redirect | `redirect("monitoring:dashboard")`: the browser loads `/` again (**Post/Redirect/Get** pattern, so refreshing won't resubmit) |
| 13 | Updated dashboard shown | New KPIs, table, charts, incident list and the coloured banner |

### What `apply_scenario()` does
- **recover:** all applicable metrics get random healthy values, the asset is reachable, and uptime rises by 0.01%.
- **warning:** start healthy, then push **one** random applicable metric into its warning band (e.g. CPU 71–84%, latency 110–240 ms).
- **critical:** the same, but into the critical band (e.g. CPU 87–99%, latency 270–650 ms), with a tiny uptime reduction.
- **offline:** `is_reachable=False`, CPU/memory/latency cleared, uptime reduced by 0.2–0.8%.

Fibre links and the data centre only ever get **latency** events (`_applicable_metrics`). Routers, servers, cloud nodes and databases can get CPU, memory or latency events.

### Why it's demo-friendly
The **first asset always gets a problem** (warning, critical or offline), so **every click produces a visible event**. The test `test_random_simulation_always_produces_a_problem` checks this 20 times in a row.

### Message colours
Green = asset Healthy (recovered), Amber = Warning, Red = Critical or Offline.
Example from the live test: *"**Fibre Link — Lekki to Victoria Island** latency rose to 336.9 ms → status **Critical**. New incident created: INC-0003 (High Network Latency)."*

---

## Phase 15 — Incident Management

### The lifecycle
```
 OPEN ──(Mark as Investigating)──► INVESTIGATING ──(Resolve)──► RESOLVED
   └───────────────────(Resolve directly)──────────────────────────┘
```
### Mark as Investigating
`POST /incidents/<id>/investigate/` → `views.incident_investigate` → `services.mark_investigating(incident)`:
```python
if incident.status == Incident.Status.OPEN:
    incident.status = Incident.Status.INVESTIGATING
    incident.save(update_fields=["status"])
```
The incident stays **active** (it still counts in Active Incidents) but now shows a purple "Investigating" label, and the Investigate button disappears.

### Resolve
`POST /incidents/<id>/resolve/` → `views.incident_resolve` → `services.resolve_incident(incident)`:
```python
if incident.status != Incident.Status.RESOLVED:
    incident.status = Incident.Status.RESOLVED
    incident.resolved_at = timezone.now()
    incident.save(update_fields=["status", "resolved_at"])
```
- `resolved_at` records **when** it was fixed (used to measure time to resolve).
- It disappears from **Active Incidents**, the KPI drops by 1, and it appears under **Recently Resolved**.

### Safety details
- Both actions accept **POST only** (`@require_POST`). A GET request returns **405 Method Not Allowed** (tested), so a link or a web crawler can never change data.
- `_redirect_back()` only follows the `next` URL if it is on the same host (`url_has_allowed_host_and_scheme`). This prevents "open redirect" tricks.

### Why lifecycle tracking matters
It shows **who is working on what**, prevents two engineers fixing the same thing, and the timestamps (`created_at`, `resolved_at`) allow metrics like MTTR (Mean Time To Resolve).

---

## Phase 16 — Reset Demo

`POST /reset/` → `views.reset_demo` → `services.seed_demo_data(reset=True)`:
1. **Delete all incidents.**
2. **Restart incident numbering** (`_restart_incident_numbering()`), so the next incident is INC-0001 again. SQLite remembers the last used ID in an internal table called `sqlite_sequence`, and we clear the incident entry. This only runs on SQLite.
3. **Delete any non-demo assets** (for example, ones you added in Admin).
4. **Restore every demo asset's original metrics** (`update_or_create`) and set them reachable.
5. **Run the engine** (`run_all_checks()`), which recreates the two starting incidents: INC-0001 (Backup Server latency) and INC-0002 (Cloud Node 02 CPU).
6. Show the message "Demo environment reset: original assets, metrics and incidents restored."

The whole reset is one database **transaction**: all or nothing. A browser `confirm()` dialog prevents accidental clicks.

**Why it's useful:** you can rehearse the interview demo as many times as you like and always start from the same clean state. It is also available as `python manage.py seed_demo --reset`.

---

## Phase 17 — Django Admin

### What it is
Django Admin is an automatic, password-protected management website that Django generates from your models. It lets an administrator view, search, filter, add, edit and delete records without writing any extra pages.

### Access
- URL: **http://127.0.0.1:8000/admin/** (or the "Admin" link in the NetOps navbar).
- Username: **admin**. The demo password was set by the local, git-ignored helper `_local_create_admin.bat`. It is **not** written in this guide.
- Change the password at any time: `venv\Scripts\python.exe manage.py changepassword admin`
- Create another admin: `venv\Scripts\python.exe manage.py createsuperuser`

### What's registered (`monitoring/admin.py`)
**Infrastructure assets**
- List columns: name, type, location, IP, status, CPU, memory, latency, uptime, last checked.
- Filters: status, asset type, location. Search: name, IP, location.
- **Inline incidents:** each asset's edit page lists its incidents.

**Incidents**
- List columns: id, title, asset, severity, status, created, resolved.
- Filters: status, severity, metric. Search: title, asset name, description.
- Date drill-down (`date_hierarchy`) by creation date.

Admin header text: "NetOps Administration".

> Note: editing a metric directly in Admin saves the number but does **not** run the monitoring engine. The status updates on the next Simulate/Reset. Use Admin to inspect data, and the dashboard to drive the demo.

---

## Phase 18 — Testing and Debugging

### Automated tests (`monitoring/tests.py`): 22 tests, all passing on the laptop
Run with: `venv\Scripts\python.exe manage.py test monitoring -v 2` (or double-click `_local_run_tests.bat`, output in `logs\test_log.txt`).

Django creates a **separate temporary test database** for each run, so tests never touch your demo data.

| Test class | What it proves |
|---|---|
| `ThresholdClassificationTests` (5) | CPU/memory/latency boundaries (70 → Warning, 85 → Warning, 92 → Critical, etc.), missing metric = Healthy, worst status wins |
| `IncidentCreationTests` (6) | Critical CPU creates the right incident, title, severity and recommendation; healthy asset → no incident; offline → "Asset Offline"; **3 checks → still 1 incident** (duplicate prevention); Warning→Critical **escalation** without a duplicate; a new incident is allowed after resolution |
| `IncidentLifecycleViewTests` (3) | Investigate button sets INVESTIGATING; Resolve sets RESOLVED + `resolved_at` and active KPI = 0; a **GET** to resolve returns **405** |
| `DashboardAndDemoTests` (8) | Seed is idempotent; initial state (2 Warning, 2 incidents); KPIs match the DB (8/6/2/2); refreshing the dashboard creates no incidents; asset page shows IP and incident; forced simulation → Critical CPU + incident + message; 20 random simulations always produce a problem; Reset restores metrics, statuses and INC-0001/INC-0002 |

`unittest.mock.patch` is used in one test to make the random simulation **deterministic** (it forces a Critical CPU event) so the test always gives the same result.

### Manual checks performed in Chrome on the laptop (6 Oct 2026)
| Check | Result |
|---|---|
| Django starts (`runserver`) | ✅ |
| `manage.py check` | ✅ "System check identified no issues" |
| Migrations | ✅ `0001_initial` created and applied |
| Demo data seeded | ✅ "8 assets (8 newly created), 2 active incidents" |
| Dashboard loads; KPIs 8 / 6 / 2 / 0 / 2 / 99.92% | ✅ |
| Asset table, badges, coloured metrics | ✅ |
| All 3 charts render with live data | ✅ No console errors |
| Simulate → Fibre Link latency 336.9 ms → Critical → INC-0003 created, KPIs updated | ✅ |
| Mark as Investigating → status "Investigating", button hidden | ✅ |
| Resolve → removed from Active (3→2), shown in Recently Resolved with resolved time | ✅ |
| Asset detail page (Fibre Link) with metrics, recommendation, history | ✅ |
| 4 more simulations: Critical CPU, Critical latency, Offline, recovery, **duplicate prevented** | ✅ |
| Reset Demo → 8/6/2/0/2, IDs back to INC-0001/0002 | ✅ |
| Django Admin login, asset list with filters, incident list | ✅ |
| Static CSS/JS load, no broken links | ✅ |
| **Offline check:** all 14 page requests served from `127.0.0.1`; 0 external requests; fonts, icons and all 3 charts load | ✅ |
| **Notifications:** visible bottom-left after Simulate, Investigate and Resolve (even when the page jumps to `#incidents`); auto-close after 12 s | ✅ |
| Simulate escalation seen live: Backup Server Warning → Critical, INC-0001 escalated (no duplicate) | ✅ |
| 22/22 tests re-run after these changes | ✅ |

### Problems encountered: Problem → Cause → Fix → Result
1. **Django would not install.**
   - *Problem:* `pip` said "No matching distribution found for Django<5.3,>=5.2".
   - *Cause:* the laptop has **Python 3.9.13**; Django 5.x requires Python 3.10+.
   - *Fix:* changed `requirements.txt` to `Django>=4.2,<5.3` so pip picks **Django 4.2 LTS** on Python 3.9 (and 5.2 on newer Python). Replaced the Python 3.10-only type hint `float | None` with `Optional[float]` in `services.py`.
   - *Result:* Django 4.2.30 installed, and all tests passed.
2. **Incident numbers kept growing after Reset.**
   - *Problem:* after Reset, the starting incidents were INC-0007 and INC-0008 instead of INC-0001/0002.
   - *Cause:* SQLite's `AUTOINCREMENT` never reuses IDs; it stores the last ID in `sqlite_sequence`.
   - *Fix:* `_restart_incident_numbering()` clears the incident entry in `sqlite_sequence` during reset. Added a test assertion.
   - *Result:* every reset starts at INC-0001.
3. **Message wording.** The simulation banner said "cpu rose to…". Fixed to "CPU rose to…".
4. **Confirmation messages were off-screen.**
   - *Problem:* after Mark as Investigating or Resolve, the confirmation message wasn't visible.
   - *Cause:* those buttons redirect back to `/#incidents`, so the browser scrolls down to the incident table, while the message was printed at the **top** of the page.
   - *Fix:* messages now render in a `.message-stack` container fixed to the **bottom-left** of the screen (CSS `position: fixed`), with a 12-second auto-close script in `base.html`.
   - *Result:* every action's message is visible wherever the page is scrolled.
5. **The app needed internet for its styling and charts.**
   - *Problem:* Bootstrap, Bootstrap Icons, Chart.js and Google Fonts were loaded from CDNs, so with no internet the dashboard would lose its styling and charts.
   - *Cause:* external `<link>` and `<script>` URLs in `base.html` and `dashboard.html`.
   - *Fix:* downloaded the exact versions (Bootstrap 5.3.3, Bootstrap Icons 1.11.3, Chart.js 4.4.4, Inter and JetBrains Mono from Fontsource) into `static/vendor/` on the laptop. Added `static/css/fonts.css` with `@font-face` rules, switched the templates to `{% static %}` paths, and removed the source-map comments (which would cause harmless 404s in the browser's developer tools).
   - *Result:* the browser's network log shows every request going to `127.0.0.1` and **zero** external requests.

> Tip: if the server window shows an error, read the **last line** of the traceback first. It usually names the file and line.

---

## Phase 19 — Complete Application Architecture

```
User / Browser
      ↓   (HTTP: GET pages, POST actions with CSRF token)
HTML + Bootstrap + Chart.js        templates/, static/
      ↓
Django (URL routing + views)       netops/urls.py → monitoring/urls.py → monitoring/views.py
      ↓
Python business logic              monitoring/services.py
      ↓
Django ORM (models)                monitoring/models.py
      ↓
SQLite                             db.sqlite3
```
| Connection | What happens |
|---|---|
| Browser → Django | The browser sends an HTTP request to the dev server on `127.0.0.1:8000` |
| URLs → View | Django matches the path against `urlpatterns` and calls the matching view function |
| View → Services | Views call service functions for any logic (simulate, reset, resolve…) |
| Services/Views → ORM | Python objects and querysets (`objects.filter`, `.save()`) |
| ORM → SQLite | The ORM writes the SQL and runs it on `db.sqlite3` |
| View → Template | `render()` fills HTML templates with context data |
| Template → Browser | Finished HTML (with JSON for charts) is sent back; Chart.js draws the charts |

### Django's Model → View → Template (MVT), in plain words
- **Model** = *the data and its shape* (`InfrastructureAsset`, `Incident`). Like the columns of a spreadsheet.
- **View** = *the worker* that gets a request, fetches or changes data, and chooses what to show. Like a waiter taking an order.
- **Template** = *the presentation*: HTML with placeholders that get filled in. Like the plate the food is served on.

(Django's "View" plays the role of the "Controller" in classic MVC; Django's "Template" is MVC's "View".) NetOps adds a **service layer** between views and models for the business rules.

---

## Phase 20 — Complete NetOps Workflow

```
Infrastructure Asset           (row in SQLite, e.g. Customer Database)
        ↓
Metrics                        (CPU 93.7%, memory 62%, latency 37 ms; simulated)
        ↓
Monitoring Engine              run_monitoring_check()
        ↓
Threshold Evaluation           classify_metric(): 93.7 > 85 → CRITICAL
        ↓
Healthy / Warning / Critical / Offline   worst_status() → asset.status = CRITICAL
        ↓
Incident                       create_incident_if_needed() → INC-0004 "High CPU Utilisation"
        ↓                      (+ severity Critical + rule-based recommendation)
Open                           visible in Active Incidents
        ↓   engineer clicks Mark as Investigating
Investigating                  still active, owner is working on it
        ↓   engineer clicks Resolve
Resolved                       resolved_at stored; moved to Recently Resolved
```
Every arrow is real code, and every state is saved in SQLite.

---

## Phase 21 — Running the Finished Project (from a cold start)

### Easiest way
1. Open File Explorer → **Documents** → **NetOps — Network & Infrastructure Monitoring Dashboard**.
2. Double-click **`start_netops.bat`**. A black window opens (that's the server) and your browser opens NetOps after about 3 seconds.
3. To stop: click the black window and press **CTRL + C**, then close it.

### Manual way (VS Code or PowerShell)
1. **Open a terminal:** in VS Code, *File → Open Folder* → the NetOps folder, then *Terminal → New Terminal*. Or open PowerShell from the Start menu.
2. **Go to the project folder** (`cd` = change directory; the quotes are needed because of the spaces):
   ```powershell
   cd "C:\Users\Dell\Documents\NetOps — Network & Infrastructure Monitoring Dashboard"
   ```
3. **Activate the virtual environment** (use the project's own Python and Django):
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```
   The prompt now starts with `(venv)`. (If blocked, see Phase 3, or use `cmd` with `venv\Scripts\activate.bat`.)
4. **Start the Django development server:**
   ```powershell
   python manage.py runserver
   ```
   Wait for `Starting development server at http://127.0.0.1:8000/`.
5. **Open the browser** (Chrome).
6. **Go to NetOps:** http://127.0.0.1:8000/
7. **Admin (optional):** http://127.0.0.1:8000/admin/ (user `admin`)
8. **Stop the server:** press **CTRL + C** in the terminal. Run `deactivate` to leave the venv.

### If something is wrong
| Symptom | Fix |
|---|---|
| "This site can't be reached" | The server isn't running. Repeat step 4 |
| "Couldn't import Django" | The venv isn't active. Repeat step 3 (or run `setup_netops.bat`) |
| "no such table" | `python manage.py migrate` then `python manage.py seed_demo` |
| Dashboard empty / odd state | Click **RESET DEMO** (or `python manage.py seed_demo --reset`) |
| "Port 8000 is already in use" | A server is already running in another window: use that, or close it |
| Charts/styling missing | Press **CTRL + F5** to hard-refresh. Check that `static\vendor\` exists (it's in Git). No internet is needed |

### Fresh computer (rebuild from Git)
```powershell
git clone <your-repo-url>
cd <folder>
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```
(On Windows, `setup_netops.bat` does all of this except `createsuperuser`.)

---

## Phase 22 — Interview Demonstration Guide

### Before the interview (5 minutes)
- Start the server (`start_netops.bat`) and click **RESET DEMO**.
- Zoom the browser to about 90% so the KPIs and buttons fit on one screen.
- Have VS Code open on `monitoring/services.py` (show `THRESHOLDS`, `classify_value`, `create_incident_if_needed`).

### Step-by-step
| Step | Do | Point at | Say |
|---|---|---|---|
| 1 | Open http://127.0.0.1:8000/ | Header + DEMO ENVIRONMENT | "This dashboard provides a central view of infrastructure health across servers, routers, fibre links, cloud nodes and other assets. Everything here is simulated demo data." |
| 2 | — | KPI cards | "The operations team can immediately see overall infrastructure health, uptime and active incidents. Every number is calculated live from the database." |
| 3 | Scroll | Table, coloured values, charts | "Current operational metrics are evaluated against defined monitoring thresholds. For example, CPU at 70% is a warning and above 85% is critical. That's why Cloud Node 02 at 78% is amber." |
| 4 | Click **SIMULATE NETWORK EVENT** | The banner | "This simulates telemetry changing on one or two assets." |
| 5 | — | Banner + new red/amber row + KPI change | "The monitoring engine detected a threshold breach and automatically created an incident." |
| 6 | Scroll to Active Incidents (or click the asset name) | Severity, asset, title/description, recommended action | "Each incident records the problem, severity, affected asset and a rule-based recommended action. It's a simple rules table, not AI." |
| 7 | Click **Mark as Investigating** | Status turns purple | "That change is saved to SQLite. The incident is still active, but now it's clear someone owns it." |
| 8 | Click **Resolve** | Disappears from Active; appears in Recently Resolved | "Resolving records a resolved time and removes it from the active count." |
| 9 | (Optional) Click Simulate a few more times | "duplicate prevented" banner | "If the same problem is detected again while an incident is open, NetOps doesn't create a duplicate. If it worsens, it escalates the existing one." |
| 10 | Explain the future | — | "In a production environment, the simulated metrics could be replaced with telemetry from SNMP, Prometheus, monitoring APIs or other infrastructure sources. The threshold and incident logic would stay the same." |

**Technical terms to use:** threshold, telemetry, severity, incident lifecycle, de-duplication, service layer, ORM, migrations, POST/Redirect/GET, CSRF, transaction, idempotent seed command.

**Do NOT claim:** that it monitors real infrastructure, that it uses AI or machine learning, that it is production-ready or deployed, that it does real-time background monitoring, or that it integrates with Prometheus or SNMP today.

### 60–90 second explanation
> "NetOps is a Django prototype of a Network Operations Centre dashboard. I built it to show how an infrastructure team could monitor routers, fibre links, servers, cloud nodes and databases from one screen.
>
> Each asset is stored in SQLite through Django models, with CPU, memory, latency and uptime metrics. The core is a monitoring engine in a separate service layer. It compares every metric against defined thresholds. CPU above 85%, for example, is critical. The most severe metric decides the asset's overall status.
>
> When a threshold is breached, NetOps automatically opens an incident with a severity and a rule-based recommended action. It checks for an existing active incident for the same asset and problem first, so there are no duplicate alerts, and a warning that gets worse is escalated rather than duplicated. Engineers move incidents from Open to Investigating to Resolved, and every change is saved with timestamps.
>
> Because I can't monitor real infrastructure in a portfolio project, the metrics are simulated. A Simulate Network Event button generates realistic failures, and Reset Demo restores a known state. The charts use Chart.js with data passed safely from Django, and the business logic is covered by 22 automated tests.
>
> In production, I'd replace the simulator with SNMP or Prometheus telemetry, run checks on a schedule, move to PostgreSQL, and add authentication, role-based access and alerting."

---

## Phase 23 — Likely Technical Interview Questions

For each question: **B** = beginner-friendly explanation, **T** = technically accurate answer, **I** = short interview-ready answer.

**1. Why Django?**
- B: Django gives you most of what a web app needs already built.
- T: It's a batteries-included framework: ORM, migrations, templates, an auto-generated admin, CSRF protection, messages and a test runner. That let me focus on the monitoring logic instead of plumbing.
- I: "Django let me build a secure, database-backed app quickly, with an admin panel and a test framework included, so my time went into the monitoring logic."

**2. Why SQLite?**
- B: It's a database in a single file, with nothing to install.
- T: Zero-configuration, ships with Python, fully SQL and ACID-compliant. Ideal for a single-user local prototype.
- I: "It's zero-setup and perfect for a local prototype. Because I use the Django ORM, switching databases is mostly a settings change."

**3. Why not PostgreSQL?**
- B: PostgreSQL is a database server, which is more to install and run.
- T: PostgreSQL is better for concurrency, large data and production features (time-series extensions like TimescaleDB, replication). For a 2-hour local prototype it added setup cost without demo benefit.
- I: "For production I'd use PostgreSQL. Here, SQLite kept setup to zero, and the ORM makes migrating straightforward."

**4. What is latency?**
- B: How long data takes to get there and back.
- T: Round-trip delay, measured in milliseconds. High latency signals congestion, routing problems or a degraded link.
- I: "Round-trip delay in milliseconds. NetOps warns at 100 ms and goes critical above 250 ms."

**5. What is a threshold?**
- B: A line that, once crossed, means something is wrong.
- T: A configured boundary on a metric that maps values to states. NetOps uses two per metric (warning and critical), defined once in `THRESHOLDS`.
- I: "A defined limit on a metric. For CPU, 70% is a warning and over 85% is critical."

**6. How are incidents generated?**
- B: When a number crosses a line, NetOps writes a ticket automatically.
- T: `run_monitoring_check()` finds breaches, sets the worst status, and for each breach `create_incident_if_needed()` creates an incident with severity, description and recommendation, unless an active one exists for that asset and metric.
- I: "The engine evaluates metrics, and any breach creates an incident with severity and a recommended action, with de-duplication by asset and metric."

**7. How do you prevent duplicate incidents?**
- B: Before writing a ticket, NetOps checks if one is already open for that problem.
- T: It queries for an Incident with the same asset and metric and status in (Open, Investigating). If one exists, it doesn't create another, and it escalates severity if needed. This is tested.
- I: "One active incident per asset per problem. Repeat detections are suppressed, and worsening problems escalate the existing incident."

**8. How does Django communicate with SQLite?**
- B: Django translates Python into database commands.
- T: Through the ORM. Models map to tables, querysets compile to SQL, and the sqlite3 backend executes it. Migrations keep the schema in sync with the models.
- I: "Through the ORM. I write Python like `Incident.objects.filter(...)` and Django generates and runs the SQL."

**9. What happens when Simulate Network Event is clicked?**
- B: The button changes some numbers, then NetOps checks them and reacts.
- T: The form POSTs to `/simulate/` with a CSRF token. The view calls `simulate_network_event()`, which picks 1–2 assets, applies a weighted scenario, runs the engine (status + incidents) inside a transaction, saves to SQLite, adds a message, and redirects back to the dashboard (Post/Redirect/Get).
- I: "It POSTs to a view that generates simulated telemetry, runs the threshold engine, creates incidents if needed, saves everything in one transaction and redirects with a summary message."

**10. Why is the data simulated?**
- B: Monitoring someone's real network without permission isn't allowed, and I don't have one to monitor.
- T: For ethics, legality and confidentiality, and so failures can be triggered on demand. The service layer isolates the data source.
- I: "So it's safe and demonstrable on demand. The architecture allows real telemetry to replace the simulator."

**11. How would you connect NetOps to real infrastructure?**
- B: Replace the fake number generator with real measurements.
- T: Add collectors (SNMP polling, ICMP checks or Prometheus queries) that write metrics, then call the same `run_monitoring_check()` on a schedule (cron, Celery Beat or a management command), and store history in a time-series table.
- I: "I'd add a collector (SNMP, ping or the Prometheus API) feeding the same engine on a schedule. The thresholds and incident logic stay unchanged."

**12. What would you change for production?**
- T/I: "PostgreSQL; `DEBUG=False`; a secret key from environment variables; proper `ALLOWED_HOSTS`; HTTPS; login and role-based access on the dashboard; a WSGI server like Gunicorn behind Nginx; static files served properly; scheduled background checks; alerting; logging and monitoring of the app itself; Docker; and a CI pipeline that runs the tests."

**13. How would Prometheus fit in?**
- B: Prometheus is a popular tool that collects metrics from systems.
- T: Prometheus scrapes exporters (e.g. node_exporter) and stores time series. NetOps could query its HTTP API (PromQL) for CPU, memory and latency per asset, then apply its own incident workflow. Alternatively, Prometheus Alertmanager could push alerts to a NetOps webhook.
- I: "Prometheus would be the telemetry source. NetOps would query its API or receive Alertmanager webhooks, then handle incident management."

**14. What is SNMP?**
- B: A standard way to ask network devices how they're doing.
- T: Simple Network Management Protocol. Managers poll agents on routers and switches for OIDs (CPU, interface counters, uptime) and can receive traps. Using v3 adds authentication and encryption.
- I: "A standard protocol for polling network devices for metrics like CPU and interface stats. I'd use SNMPv3 for security."

**15. How would you secure this application?**
- T/I: "Require login for the dashboard with role-based permissions (viewer vs engineer); keep CSRF on, which NetOps already uses for every POST; POST-only state changes, which are already in place; `DEBUG=False`; secrets in environment variables; HTTPS; restricted `ALLOWED_HOSTS`; strong admin passwords; an audit trail of who changed each incident; and dependency updates."

**16. How would you scale it?**
- T/I: "Move to PostgreSQL; run collectors as background workers; store metrics in a time-series database; paginate and index queries; cache KPIs; run multiple app instances behind a load balancer; and push live updates with WebSockets instead of page reloads."

**17. Why put logic in `services.py` instead of views?**
- I: "Separation of concerns. Views handle HTTP; services hold business rules that are reusable from views, commands and tests, and independent of where the data comes from."

**18. What is CSRF and how does NetOps use it?**
- B: A trick where another website makes your browser submit a form without you knowing.
- T: Cross-Site Request Forgery. Django's middleware requires a secret token in every POST form, and `{% csrf_token %}` adds it.
- I: "Every button that changes data is a POST form with Django's CSRF token, so other sites can't forge actions."

**19. How do you pass data from Django to Chart.js safely?**
- I: "With Django's `json_script` filter. It serialises Python data into an escaped JSON script tag, and the JavaScript parses it. No values are hard-coded and there's no XSS risk."

**20. How did you test it?**
- I: "22 Django tests: threshold boundaries, worst-status logic, incident creation, de-duplication, escalation, the lifecycle views, POST-only enforcement, KPI accuracy, simulation and reset. I also walked through the full demo manually in Chrome."

---

## Phase 24 — Limitations (honest)

1. **Simulated metrics:** no real telemetry; the values are random within defined bands.
2. **No real infrastructure connection:** no SNMP, ICMP, Prometheus or API integration.
3. **SQLite:** fine for one user locally; not designed for many concurrent writers.
4. **No background monitoring:** checks run only on Simulate, Reset or `seed_demo`, not on a timer, and the page does not auto-refresh.
5. **Dashboard has no login:** anyone who can reach the local server can click actions. Only Django Admin requires authentication. There is no role-based access.
6. **No alert notifications:** no email, SMS or Slack.
7. **No metric history:** only the *current* value of each metric is stored, so there are no trend charts.
8. **Not deployed:** it runs on the local development server (`runserver`), which is not a production server; `DEBUG` is on.
9. **No audit trail:** it doesn't record *who* investigated or resolved an incident.
10. **Library updates are manual:** Bootstrap, Chart.js and the fonts are stored at fixed versions in `static/vendor`. Updating them means downloading new files (the local helper `_local_download_vendor.bat` does this).
11. **Editing metrics in Admin doesn't re-evaluate status** until the next Simulate or Reset.
12. **Django 4.2 on this laptop:** Python 3.9 limits Django to 4.2 LTS, whose support has ended. Upgrading Python to 3.12 would install the supported Django 5.2 LTS with no code changes.

---

## Phase 25 — Future Improvements

| Improvement | What it would contribute |
|---|---|
| **PostgreSQL** | Production-grade concurrency, reliability and scale |
| **Prometheus** | Real metric collection from exporters, used as the telemetry source |
| **Grafana** | Rich historical dashboards alongside NetOps's incident workflow |
| **SNMP polling** | Real CPU, interface and uptime data from routers and switches |
| **ICMP/ping checks** | Real reachability and latency for approved internal targets |
| **Real infrastructure / cloud APIs** | Metrics from cloud providers and vendor platforms |
| **Background workers** (Celery/cron) | Automatic checks every N seconds without clicking |
| **Real-time updates** (WebSockets/HTMX polling) | The dashboard updates live without reloading |
| **Alerts: email / SMS / Slack** | Notify on-call engineers immediately |
| **Authentication** | Only staff can view or act |
| **Role-based access control** | Viewer vs Engineer vs Admin permissions |
| **Audit trail / assignee field** | Who owns and who resolved each incident |
| **Historical metrics** (time-series storage) | Trends, SLA reports, capacity planning |
| **Docker** | Identical setup on any machine |
| **Cloud deployment** | Accessible to a team, with HTTPS |
| **REST API** (Django REST Framework) | Integrations with other tools |
| **Predictive anomaly detection** | Spot unusual patterns before thresholds are crossed (requires history first) |
| **Configurable thresholds per asset** | Different limits for different hardware |

---

# Phase 26 — Beginner Revision Cheat Sheets

## Technology Cheat Sheet
| Technology | Purpose in NetOps |
|---|---|
| Python | Language for all backend logic |
| Django | Web framework: URLs, views, ORM, templates, admin, tests |
| SQLite | Stores assets and incidents in `db.sqlite3` |
| HTML | Page structure (templates) |
| CSS | Dark NOC styling (`styles.css`) |
| Bootstrap 5 | Responsive grid, tables, alerts, buttons |
| JavaScript | Reads chart JSON and draws charts (`dashboard.js`) |
| Chart.js | Latency bar, status doughnut, CPU bar charts |
| Git | Version control (`main` branch, first commit `b5676a9`) |
| venv / pip | Isolated Python environment and package installer |

## Infrastructure Terminology Cheat Sheet
| Term | Simple meaning | Example in NetOps |
|---|---|---|
| CPU | Processor busyness | Cloud Node 02 at 78% → Warning |
| Memory | RAM in use | Warning at 75%+, Critical above 90% |
| Latency | Round-trip delay | Backup Server 138 ms → Warning |
| Uptime | % of time available | Average uptime KPI 99.92% |
| Threshold | Limit that triggers a state | CPU > 85% = Critical |
| Healthy / Warning / Critical / Offline | Asset states | Green / amber / red / grey badges |
| Incident | Recorded problem | INC-0001 High Network Latency |
| Severity | How serious | Warning or Critical |
| Telemetry | Collected metrics | Simulated by the Simulate button |
| NOC | 24/7 monitoring team | The intended users |
| Private IP | Internal-only address | 10.10.0.1, 172.16.1.11, 192.168.10.21 |

## Important Files Cheat Sheet
| File | Purpose | When it runs / is used |
|---|---|---|
| `manage.py` | Runs Django commands | Every command you type |
| `netops/settings.py` | Configuration | On every startup |
| `netops/urls.py` | Front-door routing (`/admin/`, app) | Every request |
| `monitoring/urls.py` | App routes | Every request to NetOps pages/actions |
| `monitoring/models.py` | Table definitions | Migrations, and every database access |
| `monitoring/services.py` | Thresholds, incidents, recommendations, simulation, seed/reset | Simulate, Reset, `seed_demo`, tests, colour filter |
| `monitoring/views.py` | Handle requests, build context | Every page load and button click |
| `monitoring/admin.py` | Admin configuration | When using /admin/ |
| `monitoring/tests.py` | 22 automated tests | `manage.py test monitoring` |
| `monitoring/templatetags/netops_tags.py` | `metric_level` colour filter | When templates render metrics |
| `monitoring/management/commands/seed_demo.py` | Demo data command | `manage.py seed_demo [--reset]` |
| `monitoring/migrations/0001_initial.py` | Creates the 2 tables | `manage.py migrate` |
| `templates/base.html` | Shared layout, navbar, messages | Every page |
| `templates/monitoring/dashboard.html` | Main dashboard | GET `/` |
| `templates/monitoring/asset_detail.html` | Asset page | GET `/assets/<id>/` |
| `templates/monitoring/_incident_table.html` | Reusable incident table | Dashboard + asset pages |
| `static/css/styles.css` | Theme + floating notification position | Every page |
| `static/css/fonts.css` | Local font definitions | Every page |
| `static/vendor/` | Local Bootstrap, Bootstrap Icons, Chart.js, fonts (works offline) | Every page |
| `static/js/dashboard.js` | Charts | Dashboard |
| `requirements.txt` | Dependencies | `pip install -r` |
| `setup_netops.bat` / `start_netops.bat` | One-click setup / start | Double-click |
| `db.sqlite3` | The database | Always (not in Git) |

## Important Commands Cheat Sheet
| Command | Meaning | When to use it |
|---|---|---|
| `cd "C:\Users\Dell\Documents\NetOps — Network & Infrastructure Monitoring Dashboard"` | Go to the project | First, in any new terminal |
| `python -m venv venv` | Create a virtual environment | Once per machine |
| `.\venv\Scripts\Activate.ps1` | Activate the venv (PowerShell) | Every new terminal |
| `pip install -r requirements.txt` | Install dependencies | After creating the venv |
| `python manage.py makemigrations` | Create migrations from model changes | After editing `models.py` |
| `python manage.py migrate` | Apply migrations to the DB | After makemigrations / on new setup |
| `python manage.py seed_demo` | Load demo assets | New setup |
| `python manage.py seed_demo --reset` | Reset demo state | Before a demo |
| `python manage.py runserver` | Start the dev server | To use the app |
| `CTRL + C` | Stop the server | When done |
| `python manage.py test monitoring` | Run tests | After any change |
| `python manage.py check` | Configuration check | When something seems wrong |
| `python manage.py createsuperuser` | Create an admin user | New setup |
| `python manage.py changepassword admin` | Change the admin password | Any time |
| `git status` / `git add -A` / `git commit -m "..."` | Save a snapshot | After changes |
| `deactivate` | Leave the venv | When done |

## NetOps Architecture Cheat Sheet (one page)
NetOps is a **Django** web application with one app, **`monitoring`**. A user's **browser** sends HTTP requests to Django's development server. **`netops/urls.py`** sends `/admin/` to Django Admin and everything else to **`monitoring/urls.py`**, which maps each path to a **view**.

**Read-only pages** (GET): the **dashboard** and **asset detail** views read from the database through the **Django ORM** and pass a **context** dictionary to a **template**. The dashboard view calculates the six **KPIs** with a single aggregate query, lists active incidents (Critical first), lists the last five resolved incidents, and builds **chart data**. The template renders HTML with Bootstrap, and `json_script` safely embeds the chart data, which **`dashboard.js`** turns into three **Chart.js** charts.

**Actions** (POST + CSRF): **Simulate**, **Reset**, **Investigate** and **Resolve** are POST-only views. They call functions in **`services.py`**, the **service layer** that holds all business rules:
- **Thresholds** (`THRESHOLDS`): CPU 70/85, memory 75/90, latency 100/250.
- **Classification** (`classify_value`), with the **worst status winning** (`worst_status`); unreachable means **Offline**.
- **Monitoring check** (`run_monitoring_check`): sets the status and `last_checked`, saves, and creates incidents.
- **Incident creation with de-duplication** (`create_incident_if_needed`): one active incident per asset+metric, with escalation from Warning to Critical.
- **Rule-based recommendations** (`RECOMMENDATIONS`).
- **Simulation** (`simulate_network_event`): 1–2 assets, weighted scenarios, the first always a problem.
- **Lifecycle** (`mark_investigating`, `resolve_incident`), with `resolved_at` timestamps.
- **Seed/Reset** (`seed_demo_data`): idempotent; reset clears incidents, restarts numbering and restores metrics.

After an action, the view adds a **flash message** and **redirects** (Post/Redirect/Get). Data lives in **SQLite** (`db.sqlite3`) in two tables, **InfrastructureAsset** (1) → **Incident** (many), linked by a **ForeignKey**. **Django Admin** provides authenticated management of both. **22 tests** verify the logic.

## Interview Cheat Sheet
- **Start:** `start_netops.bat` → **RESET DEMO** → zoom to 90%.
- **One-liner:** "A Django NOC dashboard that detects threshold breaches on simulated infrastructure telemetry, auto-creates de-duplicated incidents with rule-based recommendations, and manages them through Open → Investigating → Resolved."
- **Thresholds:** CPU 70 / 85 · Memory 75 / 90 · Latency 100 / 250 ms · Offline = unreachable.
- **Worst status wins.** Offline > Critical > Warning > Healthy.
- **De-dup key:** same asset + same metric + status Open/Investigating.
- **Where the logic lives:** `monitoring/services.py`.
- **Safety:** POST-only actions + CSRF, `json_script`, `format_html` escaping, transactions.
- **Tests:** 22, all passing.
- **Works offline:** all libraries and fonts are bundled in `static/vendor`, so Wi-Fi problems can't break the demo.
- **Honesty:** simulated data, not AI, not production, no background polling, no dashboard login.
- **Future:** SNMP / Prometheus → same engine; PostgreSQL; scheduled workers; alerts; auth/RBAC; Docker; cloud.
- **Starting state:** 8 assets, 6 healthy, 2 warning, 2 incidents (INC-0001 Backup Server latency, INC-0002 Cloud Node 02 CPU), average uptime 99.92%.

---
*This guide documents the NetOps application exactly as built and tested on 6 October 2026. Infrastructure names, metrics, IP addresses, incidents and locations are fictional demo data and do not represent the systems of any real organisation.*
