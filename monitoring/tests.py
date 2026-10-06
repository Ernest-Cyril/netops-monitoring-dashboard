"""
Automated tests for NetOps.  Run with:  python manage.py test monitoring
"""
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from . import services
from .models import Incident, InfrastructureAsset

Status = InfrastructureAsset.Status
Metric = Incident.Metric


class ThresholdClassificationTests(TestCase):
    def test_cpu_thresholds(self):
        self.assertEqual(services.classify_metric(Metric.CPU, 50), Status.HEALTHY)
        self.assertEqual(services.classify_metric(Metric.CPU, 70), Status.WARNING)
        self.assertEqual(services.classify_metric(Metric.CPU, 85), Status.WARNING)
        self.assertEqual(services.classify_metric(Metric.CPU, 92), Status.CRITICAL)

    def test_memory_thresholds(self):
        self.assertEqual(services.classify_metric(Metric.MEMORY, 74.9), Status.HEALTHY)
        self.assertEqual(services.classify_metric(Metric.MEMORY, 80), Status.WARNING)
        self.assertEqual(services.classify_metric(Metric.MEMORY, 95), Status.CRITICAL)

    def test_latency_thresholds(self):
        self.assertEqual(services.classify_metric(Metric.LATENCY, 40), Status.HEALTHY)
        self.assertEqual(services.classify_metric(Metric.LATENCY, 150), Status.WARNING)
        self.assertEqual(services.classify_metric(Metric.LATENCY, 300), Status.CRITICAL)

    def test_missing_metric_is_healthy(self):
        self.assertEqual(services.classify_metric(Metric.CPU, None), Status.HEALTHY)

    def test_most_severe_status_wins(self):
        self.assertEqual(services.worst_status([Status.HEALTHY, Status.CRITICAL, Status.WARNING]), Status.CRITICAL)
        self.assertEqual(services.worst_status([Status.HEALTHY, Status.WARNING]), Status.WARNING)
        self.assertEqual(services.worst_status([]), Status.HEALTHY)


def make_asset(**overrides):
    data = dict(name="Test Server", asset_type=InfrastructureAsset.AssetType.SERVER, location="Ikeja",
                ip_address="10.0.0.5", cpu_usage=30, memory_usage=40, latency=20, uptime=99.9)
    data.update(overrides)
    return InfrastructureAsset.objects.create(**data)


class IncidentCreationTests(TestCase):
    def test_critical_cpu_creates_incident_and_sets_status(self):
        asset = make_asset(cpu_usage=92)
        result = services.run_monitoring_check(asset)
        asset.refresh_from_db()
        self.assertEqual(asset.status, Status.CRITICAL)
        self.assertEqual(len(result.created), 1)
        incident = result.created[0]
        self.assertEqual(incident.title, "High CPU Utilisation")
        self.assertEqual(incident.severity, Incident.Severity.CRITICAL)
        self.assertIn("scaling resources", incident.recommended_action)

    def test_healthy_asset_creates_no_incident(self):
        asset = make_asset()
        services.run_monitoring_check(asset)
        self.assertEqual(Incident.objects.count(), 0)
        self.assertEqual(asset.status, Status.HEALTHY)

    def test_offline_asset(self):
        asset = make_asset(is_reachable=False, cpu_usage=None, memory_usage=None, latency=None)
        result = services.run_monitoring_check(asset)
        self.assertEqual(asset.status, Status.OFFLINE)
        self.assertEqual(result.created[0].title, "Asset Offline")

    def test_duplicate_incidents_are_prevented(self):
        asset = make_asset(latency=180)
        services.run_monitoring_check(asset)
        services.run_monitoring_check(asset)
        services.run_monitoring_check(asset)
        self.assertEqual(Incident.objects.filter(asset=asset, metric=Metric.LATENCY).count(), 1)

    def test_warning_escalates_to_critical_without_duplicate(self):
        asset = make_asset(latency=180)
        services.run_monitoring_check(asset)
        asset.latency = 400
        services.run_monitoring_check(asset)
        incidents = Incident.objects.filter(asset=asset, metric=Metric.LATENCY)
        self.assertEqual(incidents.count(), 1)
        self.assertEqual(incidents.first().severity, Incident.Severity.CRITICAL)

    def test_new_incident_allowed_after_resolution(self):
        asset = make_asset(latency=180)
        first = services.run_monitoring_check(asset).created[0]
        services.resolve_incident(first)
        services.run_monitoring_check(asset)
        self.assertEqual(Incident.objects.filter(asset=asset).count(), 2)


class IncidentLifecycleViewTests(TestCase):
    def setUp(self):
        asset = make_asset(cpu_usage=95)
        self.incident = services.run_monitoring_check(asset).created[0]

    def test_mark_investigating(self):
        self.client.post(reverse("monitoring:incident_investigate", args=[self.incident.pk]))
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, Incident.Status.INVESTIGATING)

    def test_resolve_sets_resolved_at_and_removes_from_active(self):
        self.client.post(reverse("monitoring:incident_resolve", args=[self.incident.pk]))
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.status, Incident.Status.RESOLVED)
        self.assertIsNotNone(self.incident.resolved_at)
        response = self.client.get(reverse("monitoring:dashboard"))
        self.assertEqual(response.context["kpis"]["active_incidents"], 0)

    def test_get_request_cannot_change_data(self):
        response = self.client.get(reverse("monitoring:incident_resolve", args=[self.incident.pk]))
        self.assertEqual(response.status_code, 405)


class DashboardAndDemoTests(TestCase):
    def setUp(self):
        services.seed_demo_data()

    def test_seed_is_idempotent(self):
        services.seed_demo_data()
        self.assertEqual(InfrastructureAsset.objects.count(), len(services.DEMO_ASSETS))

    def test_initial_demo_state(self):
        # Cloud Node 02 (CPU 78%) and Backup Server (138 ms) start in Warning
        self.assertEqual(InfrastructureAsset.objects.filter(status=Status.WARNING).count(), 2)
        self.assertEqual(Incident.objects.count(), 2)

    def test_dashboard_kpis_match_database(self):
        response = self.client.get(reverse("monitoring:dashboard"))
        self.assertEqual(response.status_code, 200)
        kpis = response.context["kpis"]
        self.assertEqual(kpis["total"], 8)
        self.assertEqual(kpis["healthy"], 6)
        self.assertEqual(kpis["warning"], 2)
        self.assertEqual(kpis["active_incidents"], 2)
        self.assertContains(response, "SIMULATE NETWORK EVENT")
        self.assertContains(response, 'id="chart-data"')

    def test_dashboard_refresh_does_not_create_incidents(self):
        for _ in range(3):
            self.client.get(reverse("monitoring:dashboard"))
        self.assertEqual(Incident.objects.count(), 2)

    def test_asset_detail_page(self):
        asset = InfrastructureAsset.objects.get(name="Backup Server")
        response = self.client.get(reverse("monitoring:asset_detail", args=[asset.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "192.168.10.40")
        self.assertContains(response, "High Network Latency")

    def test_simulation_changes_metrics_and_creates_incident(self):
        # Force a deterministic critical CPU event on one compute asset
        target = InfrastructureAsset.objects.get(name="Application Server 01")
        with mock.patch("monitoring.services.random.random", return_value=0.9), \
             mock.patch("monitoring.services.random.sample", return_value=[target]), \
             mock.patch("monitoring.services._pick", return_value="critical"), \
             mock.patch("monitoring.services.random.choice", return_value=Metric.CPU):
            response = self.client.post(reverse("monitoring:simulate_event"), follow=True)
        target.refresh_from_db()
        self.assertEqual(target.status, Status.CRITICAL)
        self.assertGreater(target.cpu_usage, 85)
        self.assertTrue(Incident.objects.filter(asset=target, title="High CPU Utilisation").exists())
        self.assertContains(response, "New incident created")

    def test_random_simulation_always_produces_a_problem(self):
        for _ in range(20):
            outcomes = services.simulate_network_event()
            self.assertIn(outcomes[0][2].new_status, [Status.WARNING, Status.CRITICAL, Status.OFFLINE])

    def test_reset_restores_original_state(self):
        for _ in range(5):
            services.simulate_network_event()
        self.client.post(reverse("monitoring:reset_demo"))
        self.assertEqual(Incident.objects.count(), 2)
        self.assertEqual(InfrastructureAsset.objects.get(name="Cloud Node 02").cpu_usage, 78.0)
        self.assertEqual(InfrastructureAsset.objects.filter(status=Status.HEALTHY).count(), 6)
        # incident numbering restarts so every rehearsal begins at INC-0001
        self.assertEqual(sorted(i.reference for i in Incident.objects.all()), ["INC-0001", "INC-0002"])
