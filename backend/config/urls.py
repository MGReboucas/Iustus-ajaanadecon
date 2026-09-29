from django.urls import include, path

from .views import health
from apps.cases.admission import AccessView

urlpatterns = [
    path("api/v1/admin/service-access", AccessView.as_view()),
    path("api/v1/", include("apps.legal.urls")),
    path("api/v1/health/", health, name="health"),
    path("api/v1/", include("apps.identity.urls")),
    path("api/v1/", include("apps.cases.urls")),
    path("api/v1/", include("apps.documents.urls")),
    path("api/v1/", include("apps.communication.urls")),
]
