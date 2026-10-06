"""Project-level URL configuration: admin + the monitoring app."""
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "NetOps Administration"
admin.site.site_title = "NetOps Admin"
admin.site.index_title = "Infrastructure & Incident Data"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("monitoring.urls")),
]
