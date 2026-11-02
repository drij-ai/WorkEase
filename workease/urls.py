from django.contrib import admin
from django.urls import path, include, re_path
from django.http import JsonResponse
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from core.api_urls import router as api_router


def health_check(request):
    """Production health check probe for Render or monitoring services."""
    return JsonResponse({"status": "healthy"}, status=200)


urlpatterns = [
    re_path(r'^health/?$', health_check, name='health_check'),
    path('admin/', admin.site.urls),
    # WorkEase RESTful API v1
    path('api/v1/', include(api_router.urls)),
    # OpenAPI Schema & Interactive Swagger / ReDoc Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # Core Application Routes
    path('', include('core.urls')),
]
