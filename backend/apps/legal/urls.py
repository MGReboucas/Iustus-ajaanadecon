from django.urls import path
from .views import WorkflowView
from .mandates import TemplatesView, GenerateMandateView
from .exports import ExportsView, ExportContentView
urlpatterns = [
    path("cases/<uuid:case_id>/workflow", WorkflowView.as_view()),
    path("legal/mandate-templates", TemplatesView.as_view()),
    path("cases/<uuid:case_id>/mandates", GenerateMandateView.as_view()),
    path("cases/<uuid:case_id>/exports", ExportsView.as_view()),
    path("exports/<uuid:export_id>/content", ExportContentView.as_view()),
]
