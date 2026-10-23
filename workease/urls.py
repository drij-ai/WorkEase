from django.contrib import admin
from django.urls import path, include, re_path
from django.http import JsonResponse


def health_check(request):
    """Production health check probe for Render or monitoring services."""
    return JsonResponse({"status": "healthy"}, status=200)


urlpatterns = [
    re_path(r'^health/?$', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
]