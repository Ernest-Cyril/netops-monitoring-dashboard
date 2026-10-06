"""
Views: receive an HTTP request, ask the database / services for data,
and return an HTML page (or a redirect).

Read-only pages use GET. Anything that CHANGES data (simulate, reset,
investigate, resolve) only accepts POST and is protected by Django's CSRF token.
"""
from django.contrib import messages
from django.db.models import Avg, Case, Count, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import services
from .models import Incident, InfrastructureAsset

Status = InfrastructureAsset.Status


def _active_incidents():
    """Open + Investigating incidents, Critical first, newest first."""
    severity_order = Case(
        When(severity=Incident.Severity.CRITICAL, then=Value(0)),
        default=Value(1),
        output_field=IntegerField(),
    )
    return (
        Incident.objects.filter(status__in=Incident.ACTIVE_STATUSES)
        .select_related("asset")
        .annotate(severity_order=severity_order)
        .order_by("severity_order", "-created_at")
    )


def get_kpis():
    """All KPI numbers are calculated live from the database (nothing hard-coded)."""
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
    return counts


def build_chart_data(assets, kpis):
    """Plain Python lists/dicts that the template converts to safe JSON for Chart.js."""
    compute_assets = [a for a in assets if a.cpu_usage is not None]
    return {
        "latency": {
            "labels": [a.name for a in assets],
            "values": [a.latency for a in assets],  # None -> null (offline)
            "statuses": [a.status for a in assets],
        },
        "status": {
            "labels": ["Healthy", "Warning", "Critical", "Offline"],
            "values": [kpis["healthy"], kpis["warning"], kpis["critical"], kpis["offline"]],
        },
        "cpu": {
            "labels": [a.name for a in compute_assets],
            "values": [a.cpu_usage for a in compute_assets],
        },
        "thresholds": {
            "latency_warning": services.THRESHOLDS[Incident.Metric.LATENCY][0],
            "latency_critical": services.THRESHOLDS[Incident.Metric.LATENCY][1],
            "cpu_warning": services.THRESHOLDS[Incident.Metric.CPU][0],
            "cpu_critical": services.THRESHOLDS[Incident.Metric.CPU][1],
        },
    }


def dashboard(request):
    assets = list(InfrastructureAsset.objects.all())
    kpis = get_kpis()
    context = {
        "assets": assets,
        "kpis": kpis,
        "active_incidents": _active_incidents(),
        "resolved_incidents": Incident.objects.filter(status=Incident.Status.RESOLVED)
        .select_related("asset")
        .order_by("-resolved_at")[:5],
        "chart_data": build_chart_data(assets, kpis),
        "thresholds": services.THRESHOLDS,
    }
    return render(request, "monitoring/dashboard.html", context)


def asset_detail(request, pk):
    asset = get_object_or_404(InfrastructureAsset, pk=pk)
    context = {
        "asset": asset,
        "incidents": asset.incidents.all(),
        "recommendations": services.get_current_recommendations(asset),
    }
    return render(request, "monitoring/asset_detail.html", context)


@require_POST
def simulate_event(request):
    outcomes = services.simulate_network_event()
    if not outcomes:
        messages.error(request, "No assets found. Run 'python manage.py seed_demo' or click Reset Demo.")
        return redirect("monitoring:dashboard")

    for asset, change, result in outcomes:
        if result.created:
            refs = ", ".join(f"{i.reference} ({i.title})" for i in result.created)
            outcome = f"New incident created: {refs}."
        elif result.duplicates_skipped:
            outcome = "An existing active incident already tracks this problem (duplicate prevented)."
        else:
            outcome = "No thresholds breached."
        # format_html escapes the values, so data can never inject HTML
        text = format_html(
            "<strong>{}</strong> {} → status <strong>{}</strong>. {}",
            asset.name, change, Status(result.new_status).label, outcome,
        )
        level = {
            Status.HEALTHY: messages.SUCCESS,
            Status.WARNING: messages.WARNING,
        }.get(result.new_status, messages.ERROR)
        messages.add_message(request, level, text)
    return redirect("monitoring:dashboard")


@require_POST
def reset_demo(request):
    services.seed_demo_data(reset=True)
    messages.info(request, "Demo environment reset: original assets, metrics and incidents restored.")
    return redirect("monitoring:dashboard")


def _redirect_back(request, default_anchor="#incidents"):
    """Return to the page the button was clicked on (dashboard or asset page)."""
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect(f"/{default_anchor}")


@require_POST
def incident_investigate(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    if services.mark_investigating(incident):
        messages.info(request, f"{incident.reference} marked as Investigating.")
    else:
        messages.warning(request, f"{incident.reference} is already {incident.get_status_display()}.")
    return _redirect_back(request)


@require_POST
def incident_resolve(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    if services.resolve_incident(incident):
        messages.success(request, f"{incident.reference} resolved.")
    else:
        messages.warning(request, f"{incident.reference} was already resolved.")
    return _redirect_back(request)
