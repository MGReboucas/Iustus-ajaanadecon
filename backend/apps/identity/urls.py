from django.urls import path

from . import mobile, views

urlpatterns = [
    path("mobile/auth/login", mobile.MobileLoginView.as_view()),
    path("mobile/auth/recovery", mobile.MobileRecoveryView.as_view()),
    path("mobile/auth/logout", mobile.MobileLogoutView.as_view()),
    path("mobile/dashboard", mobile.MobileDashboardView.as_view()),
    path("mobile/cases/<uuid:case_id>/proposals", mobile.MobileProposalsView.as_view()),
    path("mobile/cases/<uuid:case_id>/proposals/<uuid:proposal_id>/decision", mobile.MobileProposalDecisionView.as_view()),
    path("mobile/cases", mobile.MobileCasesView.as_view()),
    path("mobile/cases/<uuid:case_id>", mobile.MobileCaseView.as_view()),
    path("mobile/cases/<uuid:case_id>/timeline", mobile.MobileTimelineView.as_view()),
    path("mobile/cases/<uuid:case_id>/messages", mobile.MobileMessagesView.as_view()),
    path("auth/csrf", views.CSRFView.as_view()),
    path("auth/register", views.RegisterView.as_view()),
    path("auth/verify", views.VerifyView.as_view()),
    path("auth/resend", views.ResendView.as_view()),
    path("auth/login", views.LoginView.as_view()),
    path("auth/logout", views.LogoutView.as_view()),
    path("auth/recovery", views.RecoveryView.as_view()),
    path("auth/reset", views.ResetView.as_view()),
    path("auth/mfa/enroll", views.EnrollView.as_view()),
    path("auth/mfa/verify", views.MFAView.as_view()),
    path("auth/invitations/accept", views.AcceptInviteView.as_view()),
    path("admin/invitations", views.InviteView.as_view()),
    path("me", views.MeView.as_view()),
    path("dashboard/client", views.ClientDashboardView.as_view()),
    path("dashboard/team", views.TeamDashboardView.as_view()),
]
