"""
Database models for NetOps.

InfrastructureAsset  -> one monitored thing (router, server, fibre link ...)
Incident             -> a problem detected on an asset (one asset has many incidents)

All data stored here is SIMULATED demo data.
"""
from django.db import models
from django.urls import reverse
from django.utils import timezone


class InfrastructureAsset(models.Model):
    """A piece of (fictional) infrastructure that NetOps monitors."""

    class AssetType(models.TextChoices):
        SERVER = "SERVER", "Server"
        ROUTER = "ROUTER", "Router"
        FIBRE_LINK = "FIBRE_LINK", "Fibre Link"
        CLOUD_NODE = "CLOUD_NODE", "Cloud Node"
        DATA_CENTRE = "DATA_CENTRE", "Data Centre"
        DATABASE = "DATABASE", "Database"

    class Status(models.TextChoices):
        HEALTHY = "HEALTHY", "Healthy"
        WARNING = "WARNING", "Warning"
        CRITICAL = "CRITICAL", "Critical"
        OFFLINE = "OFFLINE", "Offline"

    name = models.CharField(max_length=120, unique=True)
    asset_type = models.CharField(max_length=20, choices=AssetType.choices)
    location = models.CharField(max_length=100)
    ip_address = models.GenericIPAddressField(protocol="IPv4")
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.HEALTHY
    )

    # Metrics. CPU / memory are nullable because e.g. a fibre link has no CPU.
    cpu_usage = models.FloatField(null=True, blank=True, help_text="Percent (0-100)")
    memory_usage = models.FloatField(null=True, blank=True, help_text="Percent (0-100)")
    latency = models.FloatField(null=True, blank=True, help_text="Milliseconds")
    uptime = models.FloatField(default=100.0, help_text="Availability percent (last 30 days)")

    # False when the simulation knocks the asset offline (unreachable).
    is_reachable = models.BooleanField(default=True)

    last_checked = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("monitoring:asset_detail", args=[self.pk])

    @property
    def has_compute_metrics(self):
        """True for assets where CPU/memory make sense (servers, nodes, DBs...)."""
        return self.cpu_usage is not None or self.memory_usage is not None


class Incident(models.Model):
    """A problem detected by the monitoring engine on one asset."""

    class Severity(models.TextChoices):
        WARNING = "WARNING", "Warning"
        CRITICAL = "CRITICAL", "Critical"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        INVESTIGATING = "INVESTIGATING", "Investigating"
        RESOLVED = "RESOLVED", "Resolved"

    class Metric(models.TextChoices):
        """Which problem caused the incident. Used for duplicate prevention."""
        CPU = "CPU", "CPU"
        MEMORY = "MEMORY", "Memory"
        LATENCY = "LATENCY", "Latency"
        OFFLINE = "OFFLINE", "Offline"

    ACTIVE_STATUSES = [Status.OPEN, Status.INVESTIGATING]

    asset = models.ForeignKey(
        InfrastructureAsset, on_delete=models.CASCADE, related_name="incidents"
    )
    severity = models.CharField(max_length=10, choices=Severity.choices)
    metric = models.CharField(max_length=10, choices=Metric.choices)
    title = models.CharField(max_length=150)
    description = models.TextField()
    recommended_action = models.TextField()
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"INC-{self.pk:04d} {self.title} ({self.asset.name})"

    @property
    def reference(self):
        """Human-friendly ID such as INC-0007."""
        return f"INC-{self.pk:04d}"

    @property
    def is_active(self):
        return self.status in self.ACTIVE_STATUSES
