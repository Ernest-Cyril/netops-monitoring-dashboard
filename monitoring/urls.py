from django.urls import path

from . import views

app_name = "monitoring"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("assets/<int:pk>/", views.asset_detail, name="asset_detail"),
    path("simulate/", views.simulate_event, name="simulate_event"),
    path("reset/", views.reset_demo, name="reset_demo"),
    path("incidents/<int:pk>/investigate/", views.incident_investigate, name="incident_investigate"),
    path("incidents/<int:pk>/resolve/", views.incident_resolve, name="incident_resolve"),
]
