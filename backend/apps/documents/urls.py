from django.urls import path
from . import views

urlpatterns = [
    path("cases/<uuid:case_id>/documents", views.DocumentsView.as_view()),
    path("cases/<uuid:case_id>/documents/uploads", views.DocumentsView.as_view()),
    path("documents/<uuid:document_id>/versions", views.VersionsView.as_view()),
    path("uploads/<uuid:upload_id>/content", views.ContentView.as_view()),
    path("uploads/<uuid:upload_id>/complete", views.CompleteView.as_view()),
    path("documents/<uuid:document_id>/versions/<uuid:version_id>/download", views.DownloadView.as_view()),
    path("documents/<uuid:document_id>/versions/<uuid:version_id>/content", views.DownloadContentView.as_view()),
]
