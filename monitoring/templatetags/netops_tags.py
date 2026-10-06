"""Small template helpers for colouring metrics by threshold."""
from django import template

from monitoring import services

register = template.Library()


@register.filter
def metric_level(value, metric):
    """
    Usage in a template:  {{ asset.cpu_usage|metric_level:"CPU" }}
    Returns 'healthy', 'warning' or 'critical' (used as a CSS class suffix).
    """
    if value is None:
        return "na"
    return services.classify_metric(metric, value).lower()
