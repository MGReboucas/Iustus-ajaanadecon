from django.urls import path
from .views import WorkflowView
urlpatterns = [path("cases/<uuid:case_id>/workflow", WorkflowView.as_view())]
