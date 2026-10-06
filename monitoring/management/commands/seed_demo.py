"""
Usage:
    python manage.py seed_demo          # create demo assets if missing (safe to repeat)
    python manage.py seed_demo --reset  # restore the original demo state
"""
from django.core.management.base import BaseCommand

from monitoring.models import Incident, InfrastructureAsset
from monitoring.services import seed_demo_data


class Command(BaseCommand):
    help = "Load the fictional NetOps demo infrastructure (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete all incidents and restore every demo asset to its original metrics.",
        )

    def handle(self, *args, **options):
        created = seed_demo_data(reset=options["reset"])
        self.stdout.write(self.style.SUCCESS(
            f"Demo data ready: {InfrastructureAsset.objects.count()} assets "
            f"({created} newly created), "
            f"{Incident.objects.filter(status__in=Incident.ACTIVE_STATUSES).count()} active incidents."
        ))
