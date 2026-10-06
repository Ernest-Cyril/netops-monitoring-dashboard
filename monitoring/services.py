"""
NetOps business logic ("service layer").

Keeping this logic here (instead of in views.py) means:
  * views stay small: they only handle HTTP requests/responses
  * the rules can be unit-tested without a browser
  * the simulated metrics could later be swapped for real telemetry
    (SNMP, Prometheus, APIs) without touching the dashboard code.

Sections:
  1. Thresholds and classification   (is a value Healthy / Warning / Critical?)
  2. Rule-based recommendations      (what should the engineer do?)
  3. Asset evaluation + incidents    (update status, create incidents, no duplicates)
  4. Network event simulation        (randomly change metrics for the demo)
  5. Demo data (seed / reset)
"""
import random
from typing import Optional
from dataclasses import dataclass, field

from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from .models import Incident, InfrastructureAsset

Status = InfrastructureAsset.Status
Metric = Incident.Metric

# ---------------------------------------------------------------------------
# 1. THRESHOLDS AND CLASSIFICATION
# ---------------------------------------------------------------------------
# metric -> (warning_from, critical_above)
#   value <  warning_from              -> Healthy
#   warning_from <= value <= critical  -> Warning
#   value >  critical_above            -> Critical
THRESHOLDS = {
    Metric.CPU: (70.0, 85.0),       # percent
    Metric.MEMORY: (75.0, 90.0),    # percent
    Metric.LATENCY: (100.0, 250.0), # milliseconds
}

# Higher number = more severe. Used to pick "the worst" status.
STATUS_RANK = {
    Status.HEALTHY: 0,
    Status.WARNING: 1,
    Status.CRITICAL: 2,
    Status.OFFLINE: 3,
}


def classify_value(value, warning_from, critical_above):
    """Return Healthy / Warning / Critical for one numeric value."""
    if value is None:  # metric not applicable to this asset (e.g. CPU of a fibre link)
        return Status.HEALTHY
    if value > critical_above:
        return Status.CRITICAL
    if value >= warning_from:
        return Status.WARNING
    return Status.HEALTHY


def classify_metric(metric, value):
    """Classify a value for a named metric using THRESHOLDS."""
    warning_from, critical_above = THRESHOLDS[metric]
    return classify_value(value, warning_from, critical_above)


def worst_status(statuses):
    """The most severe status wins (e.g. [Healthy, Critical, Warning] -> Critical)."""
    return max(statuses, key=lambda s: STATUS_RANK[s], default=Status.HEALTHY)


# ---------------------------------------------------------------------------
# 2. RULE-BASED RECOMMENDATIONS  (simple if/then rules -- NOT AI)
# ---------------------------------------------------------------------------
RECOMMENDATIONS = {
    Metric.CPU: (
        "Review high-utilisation processes and available compute capacity. "
        "Consider scaling resources if utilisation remains elevated."
    ),
    Metric.MEMORY: (
        "Review memory-intensive processes and available memory capacity. "
        "Check for memory leaks and consider adding capacity if usage stays high."
    ),
    Metric.LATENCY: (
        "Check network connectivity, packet loss, routing, and upstream link health."
    ),
    Metric.OFFLINE: (
        "Verify device connectivity and power status. Escalate to the "
        "infrastructure team if the asset remains unreachable."
    ),
}

INCIDENT_TITLES = {
    Metric.CPU: "High CPU Utilisation",
    Metric.MEMORY: "High Memory Utilisation",
    Metric.LATENCY: "High Network Latency",
    Metric.OFFLINE: "Asset Offline",
}

METRIC_UNITS = {Metric.CPU: "%", Metric.MEMORY: "%", Metric.LATENCY: " ms"}


def get_recommendation(metric):
    return RECOMMENDATIONS[metric]


# ---------------------------------------------------------------------------
# 3. ASSET EVALUATION + INCIDENT CREATION
# ---------------------------------------------------------------------------
@dataclass
class Breach:
    """One metric that crossed a threshold."""
    metric: str
    level: str          # Status.WARNING / Status.CRITICAL / Status.OFFLINE
    value: Optional[float]

    @property
    def severity(self):
        """Incident severity: Offline and Critical are both 'Critical'."""
        return Incident.Severity.WARNING if self.level == Status.WARNING else Incident.Severity.CRITICAL

    def describe(self, asset):
        if self.metric == Metric.OFFLINE:
            return f"{asset.name} ({asset.ip_address}) is not responding to monitoring checks."
        warning_from, critical_above = THRESHOLDS[self.metric]
        unit = METRIC_UNITS[self.metric]
        limit = critical_above if self.level == Status.CRITICAL else warning_from
        comparison = "above" if self.level == Status.CRITICAL else "at or above"
        return (
            f"{Metric(self.metric).label} on {asset.name} is {self.value:.0f}{unit}, "
            f"{comparison} the {Status(self.level).label.lower()} threshold of {limit:.0f}{unit}."
        )


def find_breaches(asset):
    """Return a list of Breach objects for every metric outside healthy limits."""
    if not asset.is_reachable:
        return [Breach(Metric.OFFLINE, Status.OFFLINE, None)]

    breaches = []
    for metric, value in (
        (Metric.CPU, asset.cpu_usage),
        (Metric.MEMORY, asset.memory_usage),
        (Metric.LATENCY, asset.latency),
    ):
        level = classify_metric(metric, value)
        if level != Status.HEALTHY:
            breaches.append(Breach(metric, level, value))
    return breaches


def determine_status(asset):
    """Overall asset status = the most severe status of its metrics."""
    return worst_status([b.level for b in find_breaches(asset)])


def get_current_recommendations(asset):
    """Recommendations for the asset's CURRENT breaches (used on the detail page)."""
    return [
        {"title": INCIDENT_TITLES[b.metric], "level": b.level, "text": get_recommendation(b.metric)}
        for b in find_breaches(asset)
    ]


def create_incident_if_needed(asset, breach):
    """
    Create an incident for a breach UNLESS an unresolved (Open/Investigating)
    incident already exists for the same asset + metric.

    Returns (incident, created: bool).
    If a Warning incident already exists and the problem became Critical,
    the existing incident is escalated instead of creating a duplicate.
    """
    existing = (
        Incident.objects.filter(
            asset=asset, metric=breach.metric, status__in=Incident.ACTIVE_STATUSES
        )
        .order_by("-created_at")
        .first()
    )
    if existing:
        if breach.severity == Incident.Severity.CRITICAL and existing.severity == Incident.Severity.WARNING:
            existing.severity = Incident.Severity.CRITICAL
            existing.description = breach.describe(asset) + " (Escalated from Warning.)"
            existing.save(update_fields=["severity", "description"])
        return existing, False

    incident = Incident.objects.create(
        asset=asset,
        metric=breach.metric,
        severity=breach.severity,
        title=INCIDENT_TITLES[breach.metric],
        description=breach.describe(asset),
        recommended_action=get_recommendation(breach.metric),
    )
    return incident, True


@dataclass
class CheckResult:
    """What happened when one asset was checked (used for user messages)."""
    asset: InfrastructureAsset
    previous_status: str
    new_status: str
    created: list = field(default_factory=list)
    duplicates_skipped: int = 0


def run_monitoring_check(asset):
    """
    The monitoring engine for ONE asset:
      1. find threshold breaches
      2. set the overall status (worst metric wins)
      3. save the asset with a new last_checked time
      4. create incidents (without duplicates)
    """
    previous_status = asset.status
    breaches = find_breaches(asset)
    asset.status = worst_status([b.level for b in breaches])
    asset.last_checked = timezone.now()
    asset.save()

    result = CheckResult(asset=asset, previous_status=previous_status, new_status=asset.status)
    for breach in breaches:
        incident, created = create_incident_if_needed(asset, breach)
        if created:
            result.created.append(incident)
        else:
            result.duplicates_skipped += 1
    return result


def run_all_checks():
    """Run the monitoring engine against every asset."""
    return [run_monitoring_check(asset) for asset in InfrastructureAsset.objects.all()]


# ---------------------------------------------------------------------------
# 4. NETWORK EVENT SIMULATION  (fake telemetry for the demo)
# ---------------------------------------------------------------------------
# Value ranges used when generating a metric at a given level.
VALUE_BANDS = {
    Metric.CPU: {Status.HEALTHY: (18, 62), Status.WARNING: (71, 84), Status.CRITICAL: (87, 99)},
    Metric.MEMORY: {Status.HEALTHY: (30, 70), Status.WARNING: (76, 89), Status.CRITICAL: (91, 98)},
    Metric.LATENCY: {Status.HEALTHY: (4, 60), Status.WARNING: (110, 240), Status.CRITICAL: (270, 650)},
}

# Scenario weights. The FIRST asset in every event always gets a problem,
# so the interview demo never needs 20 clicks to show an incident.
PRIMARY_SCENARIOS = {"warning": 40, "critical": 45, "offline": 15}
SECONDARY_SCENARIOS = {"recover": 50, "warning": 30, "critical": 20}


def _random_value(metric, level):
    low, high = VALUE_BANDS[metric][level]
    return round(random.uniform(low, high), 1)


def _pick(weighted):
    return random.choices(list(weighted), weights=list(weighted.values()), k=1)[0]


def _applicable_metrics(asset):
    metrics = [Metric.LATENCY]
    if asset.cpu_usage is not None or asset.asset_type in COMPUTE_TYPES:
        metrics += [Metric.CPU, Metric.MEMORY]
    return metrics


COMPUTE_TYPES = {
    InfrastructureAsset.AssetType.SERVER,
    InfrastructureAsset.AssetType.CLOUD_NODE,
    InfrastructureAsset.AssetType.DATABASE,
    InfrastructureAsset.AssetType.ROUTER,
}


def apply_scenario(asset, scenario):
    """
    Change an asset's metrics according to a scenario:
      recover  -> all metrics healthy
      warning  -> one metric pushed into the Warning band
      critical -> one metric pushed into the Critical band
      offline  -> asset unreachable (no metrics)
    Returns a short text describing the change.
    """
    applicable = _applicable_metrics(asset)

    if scenario == "offline":
        asset.is_reachable = False
        asset.cpu_usage = asset.memory_usage = asset.latency = None
        asset.uptime = round(max(asset.uptime - random.uniform(0.2, 0.8), 90.0), 2)
        return "went OFFLINE"

    # Reachable again: start from healthy values for every applicable metric
    asset.is_reachable = True
    asset.latency = _random_value(Metric.LATENCY, Status.HEALTHY)
    if Metric.CPU in applicable:
        asset.cpu_usage = _random_value(Metric.CPU, Status.HEALTHY)
        asset.memory_usage = _random_value(Metric.MEMORY, Status.HEALTHY)

    if scenario == "recover":
        asset.uptime = round(min(asset.uptime + 0.01, 100.0), 2)
        return "recovered to normal operating levels"

    level = Status.WARNING if scenario == "warning" else Status.CRITICAL
    metric = random.choice(applicable)
    value = _random_value(metric, level)
    setattr(asset, {Metric.CPU: "cpu_usage", Metric.MEMORY: "memory_usage", Metric.LATENCY: "latency"}[metric], value)
    if level == Status.CRITICAL:
        asset.uptime = round(max(asset.uptime - random.uniform(0.0, 0.05), 90.0), 2)
    label = Metric(metric).label if metric == Metric.CPU else Metric(metric).label.lower()
    return f"{label} rose to {value:g}{METRIC_UNITS[metric]}"


@transaction.atomic
def simulate_network_event():
    """
    Pick 1-2 assets, change their metrics, then run the monitoring engine.
    Returns a list of (asset, change_text, CheckResult) tuples.
    """
    assets = list(InfrastructureAsset.objects.all())
    if not assets:
        return []

    count = 2 if len(assets) > 1 and random.random() < 0.5 else 1
    targets = random.sample(assets, count)

    outcomes = []
    for index, asset in enumerate(targets):
        scenario = _pick(PRIMARY_SCENARIOS if index == 0 else SECONDARY_SCENARIOS)
        change = apply_scenario(asset, scenario)
        result = run_monitoring_check(asset)  # saves asset + creates incidents
        outcomes.append((asset, change, result))
    return outcomes


# ---------------------------------------------------------------------------
# INCIDENT LIFECYCLE
# ---------------------------------------------------------------------------
def mark_investigating(incident):
    if incident.status == Incident.Status.OPEN:
        incident.status = Incident.Status.INVESTIGATING
        incident.save(update_fields=["status"])
        return True
    return False


def resolve_incident(incident):
    if incident.status != Incident.Status.RESOLVED:
        incident.status = Incident.Status.RESOLVED
        incident.resolved_at = timezone.now()
        incident.save(update_fields=["status", "resolved_at"])
        return True
    return False


# ---------------------------------------------------------------------------
# 5. DEMO DATA  (fictional infrastructure, private IP ranges only)
# ---------------------------------------------------------------------------
A = InfrastructureAsset.AssetType
DEMO_ASSETS = [
    {"name": "Lagos Core Router", "asset_type": A.ROUTER, "location": "Lagos",
     "ip_address": "10.10.0.1", "cpu_usage": 41.0, "memory_usage": 52.0, "latency": 12.0, "uptime": 99.98},
    {"name": "Lekki Data Centre", "asset_type": A.DATA_CENTRE, "location": "Lekki",
     "ip_address": "10.20.0.10", "cpu_usage": None, "memory_usage": None, "latency": 8.0, "uptime": 99.99},
    {"name": "Cloud Node 01", "asset_type": A.CLOUD_NODE, "location": "Victoria Island",
     "ip_address": "172.16.1.11", "cpu_usage": 48.0, "memory_usage": 61.0, "latency": 22.0, "uptime": 99.95},
    {"name": "Cloud Node 02", "asset_type": A.CLOUD_NODE, "location": "Victoria Island",
     "ip_address": "172.16.1.12", "cpu_usage": 78.0, "memory_usage": 66.0, "latency": 25.0, "uptime": 99.91},
    {"name": "Fibre Link — Lekki to Victoria Island", "asset_type": A.FIBRE_LINK, "location": "Lekki",
     "ip_address": "10.30.0.2", "cpu_usage": None, "memory_usage": None, "latency": 18.0, "uptime": 99.97},
    {"name": "Application Server 01", "asset_type": A.SERVER, "location": "Ikeja",
     "ip_address": "192.168.10.21", "cpu_usage": 55.0, "memory_usage": 63.0, "latency": 31.0, "uptime": 99.93},
    {"name": "Customer Database", "asset_type": A.DATABASE, "location": "Lekki",
     "ip_address": "192.168.20.5", "cpu_usage": 37.0, "memory_usage": 69.0, "latency": 14.0, "uptime": 99.99},
    {"name": "Backup Server", "asset_type": A.SERVER, "location": "Ikeja",
     "ip_address": "192.168.10.40", "cpu_usage": 29.0, "memory_usage": 47.0, "latency": 138.0, "uptime": 99.62},
]


def _restart_incident_numbering():
    """After a reset, make the next incident INC-0001 again (SQLite only)."""
    if connection.vendor != "sqlite":
        return
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = %s", [Incident._meta.db_table])
    except DatabaseError:
        pass  # sqlite_sequence does not exist yet: numbering already starts at 1


@transaction.atomic
def seed_demo_data(reset=False):
    """
    Create the demo assets. Idempotent: running it twice never duplicates
    assets, because each asset is matched by its unique name.

    reset=True additionally:
      * deletes ALL incidents
      * deletes any non-demo assets (e.g. ones added through the admin)
      * restores every demo asset's original metrics
    Finally the monitoring engine runs once so the initial statuses and
    initial incidents are consistent with the thresholds.
    """
    created_count = 0
    if reset:
        Incident.objects.all().delete()
        _restart_incident_numbering()
        InfrastructureAsset.objects.exclude(name__in=[a["name"] for a in DEMO_ASSETS]).delete()

    for data in DEMO_ASSETS:
        defaults = {k: v for k, v in data.items() if k != "name"}
        defaults["is_reachable"] = True
        if reset:
            _, created = InfrastructureAsset.objects.update_or_create(name=data["name"], defaults=defaults)
        else:
            _, created = InfrastructureAsset.objects.get_or_create(name=data["name"], defaults=defaults)
        created_count += int(created)

    run_all_checks()
    return created_count
