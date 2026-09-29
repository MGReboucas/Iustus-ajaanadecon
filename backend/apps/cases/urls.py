from django.urls import path
from . import views

urlpatterns = [
    path("cases/catalog", views.CatalogView.as_view()),
    path("cases", views.CasesView.as_view()),
    path("cases/lawyers", views.LawyersView.as_view()),
    path("cases/<uuid:case_id>", views.DetailView.as_view()),
    path("cases/<uuid:case_id>/summary", views.SummaryView.as_view()),
    path("cases/<uuid:case_id>/submit", views.SubmitView.as_view()),
    path("cases/<uuid:case_id>/assignment", views.AssignmentView.as_view()),
    path("cases/<uuid:case_id>/transitions", views.TransitionView.as_view()),
    path("cases/<uuid:case_id>/requests", views.RequestsView.as_view()),
    path("cases/<uuid:case_id>/requests/<uuid:request_id>/response", views.RequestActionView.as_view(), {"action": "response"}),
    path("cases/<uuid:case_id>/requests/<uuid:request_id>/resolve", views.RequestActionView.as_view(), {"action": "resolve"}),
    path("cases/<uuid:case_id>/timeline", views.TimelineView.as_view()),
]
