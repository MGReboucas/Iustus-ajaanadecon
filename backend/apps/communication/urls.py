from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/overview", views.OverviewView.as_view()),
    path("cases/<uuid:case_id>/messages", views.MessagesView.as_view()),
    path("notifications", views.NotificationsView.as_view()),
    path("notifications/<uuid:notification_id>/read", views.NotificationReadView.as_view()),
]
