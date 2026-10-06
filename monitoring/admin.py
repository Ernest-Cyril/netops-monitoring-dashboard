from django.contrib import admin

from .models import Incident, InfrastructureAsset


class IncidentInline(admin.TabularInline):
    model = Incident
    extra = 0
    fields = ("title", "severity", "status", "created_at", "resolved_at")
    readonly_fields = ("created_at",)
    show_change_link = True


@admin.register(InfrastructureAsset)
class InfrastructureAssetAdmin(admin.ModelAdmin):
    list_display = (
        "name", "asset_type", "location", "ip_address", "status",
        "cpu_usage", "memory_usage", "latency", "uptime", "last_checked",
    )
    list_filter = ("status", "asset_type", "location")
    search_fields = ("name", "ip_address", "location")
    inlines = [IncidentInline]


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "asset", "severity", "status", "created_at", "resolved_at")
    list_filter = ("status", "severity", "metric")
    search_fields = ("title", "asset__name", "description")
    list_select_related = ("asset",)
    date_hierarchy = "created_at"
