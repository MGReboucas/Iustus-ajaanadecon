from django.urls import include, path

from .views import health

urlpatterns = [
    path("api/v1/health/", health, name="health"),
    path("api/v1/", include("apps.identity.urls")),
    path("api/v1/", include("apps.cases.urls")),
    path("api/v1/", include("apps.documents.urls")),
]
