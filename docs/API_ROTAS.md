# Inventario de rotas Django

Gerado do roteamento e dos handlers. Nao certifica autorizacao, disponibilidade ou deploy. HEAD/OPTIONS omitidos.

Atualizar: `python backend/manage.py export_api_routes --settings=config.settings.test --output docs/API_ROTAS.md`

Conferir: acrescente `--check` ao comando.

| Metodos | Rota | Implementacao |
| --- | --- | --- |
| POST | `/api/v1/admin/invitations` | `apps.identity.views.InviteView` |
| GET, POST | `/api/v1/admin/service-access` | `apps.cases.admission.AccessView` |
| GET | `/api/v1/admin/users` | `apps.administration.views.UsersView` |
| POST | `/api/v1/admin/users/<uuid:pk>/access` | `apps.administration.views.UserAccessView` |
| GET | `/api/v1/auth/csrf` | `apps.identity.views.CSRFView` |
| POST | `/api/v1/auth/invitations/accept` | `apps.identity.views.AcceptInviteView` |
| POST | `/api/v1/auth/login` | `apps.identity.views.LoginView` |
| POST | `/api/v1/auth/logout` | `apps.identity.views.LogoutView` |
| POST | `/api/v1/auth/mfa/enroll` | `apps.identity.views.EnrollView` |
| POST | `/api/v1/auth/mfa/verify` | `apps.identity.views.MFAView` |
| POST | `/api/v1/auth/recovery` | `apps.identity.views.RecoveryView` |
| POST | `/api/v1/auth/register` | `apps.identity.views.RegisterView` |
| POST | `/api/v1/auth/resend` | `apps.identity.views.ResendView` |
| POST | `/api/v1/auth/reset` | `apps.identity.views.ResetView` |
| POST | `/api/v1/auth/verify` | `apps.identity.views.VerifyView` |
| POST | `/api/v1/billing/activate` | `apps.billing.views.ActivateView` |
| GET | `/api/v1/billing/card-key` | `apps.billing.views.CardKeyView` |
| GET, POST | `/api/v1/billing/checkout` | `apps.billing.views.CheckoutView` |
| GET | `/api/v1/billing/plan` | `apps.billing.views.PlanView` |
| POST | `/api/v1/billing/resend` | `apps.billing.views.ResendAccessView` |
| POST | `/api/v1/billing/webhook` | `apps.billing.views.WebhookView` |
| GET, POST | `/api/v1/cases` | `apps.cases.views.CasesView` |
| GET, PATCH | `/api/v1/cases/<uuid:case_id>` | `apps.cases.views.DetailView` |
| POST | `/api/v1/cases/<uuid:case_id>/assignment` | `apps.cases.views.AssignmentView` |
| GET, POST | `/api/v1/cases/<uuid:case_id>/documents` | `apps.documents.views.DocumentsView` |
| GET, POST | `/api/v1/cases/<uuid:case_id>/documents/uploads` | `apps.documents.views.DocumentsView` |
| POST | `/api/v1/cases/<uuid:case_id>/exports` | `apps.legal.exports.ExportsView` |
| POST | `/api/v1/cases/<uuid:case_id>/mandates` | `apps.legal.mandates.GenerateMandateView` |
| GET, POST | `/api/v1/cases/<uuid:case_id>/messages` | `apps.communication.views.MessagesView` |
| GET, POST | `/api/v1/cases/<uuid:case_id>/proposals` | `apps.legal.proposal_views.ProposalsView` |
| POST | `/api/v1/cases/<uuid:case_id>/proposals/<uuid:proposal_id>/decision` | `apps.legal.proposal_views.ProposalDecisionView` |
| GET, POST | `/api/v1/cases/<uuid:case_id>/requests` | `apps.cases.views.RequestsView` |
| POST | `/api/v1/cases/<uuid:case_id>/requests/<uuid:request_id>/resolve` | `apps.cases.views.RequestActionView` |
| POST | `/api/v1/cases/<uuid:case_id>/requests/<uuid:request_id>/response` | `apps.cases.views.RequestActionView` |
| POST | `/api/v1/cases/<uuid:case_id>/submit` | `apps.cases.views.SubmitView` |
| GET | `/api/v1/cases/<uuid:case_id>/summary` | `apps.cases.views.SummaryView` |
| GET | `/api/v1/cases/<uuid:case_id>/timeline` | `apps.cases.views.TimelineView` |
| POST | `/api/v1/cases/<uuid:case_id>/transitions` | `apps.cases.views.TransitionView` |
| GET, POST | `/api/v1/cases/<uuid:case_id>/workflow` | `apps.legal.views.WorkflowView` |
| GET | `/api/v1/cases/catalog` | `apps.cases.views.CatalogView` |
| GET | `/api/v1/cases/lawyers` | `apps.cases.views.LawyersView` |
| GET | `/api/v1/dashboard/client` | `apps.identity.views.ClientDashboardView` |
| GET | `/api/v1/dashboard/overview` | `apps.communication.views.OverviewView` |
| GET | `/api/v1/dashboard/team` | `apps.identity.views.TeamDashboardView` |
| POST | `/api/v1/documents/<uuid:document_id>/versions` | `apps.documents.views.VersionsView` |
| GET | `/api/v1/documents/<uuid:document_id>/versions/<uuid:version_id>/content` | `apps.documents.views.DownloadContentView` |
| GET | `/api/v1/documents/<uuid:document_id>/versions/<uuid:version_id>/download` | `apps.documents.views.DownloadView` |
| GET | `/api/v1/exports/<uuid:export_id>/content` | `apps.legal.exports.ExportContentView` |
| GET | `/api/v1/health/` | `config.views.health` |
| GET, POST | `/api/v1/legal/mandate-templates` | `apps.legal.mandates.TemplatesView` |
| GET, PATCH | `/api/v1/me` | `apps.identity.views.MeView` |
| GET | `/api/v1/mobile/auth/context` | `apps.identity.mobile_flows.ContextView` |
| POST | `/api/v1/mobile/auth/login` | `apps.identity.mobile.MobileLoginView` |
| POST | `/api/v1/mobile/auth/logout` | `apps.identity.mobile.MobileLogoutView` |
| POST | `/api/v1/mobile/auth/recovery` | `apps.identity.mobile.MobileRecoveryView` |
| POST | `/api/v1/mobile/auth/register` | `apps.identity.mobile_flows.RegisterView` |
| POST | `/api/v1/mobile/auth/resend` | `apps.identity.mobile_flows.ResendView` |
| POST | `/api/v1/mobile/auth/reset` | `apps.identity.mobile_flows.ResetView` |
| POST | `/api/v1/mobile/auth/verify` | `apps.identity.mobile_flows.VerifyView` |
| POST | `/api/v1/mobile/billing/activate` | `apps.identity.mobile_flows.MemberActivateView` |
| GET | `/api/v1/mobile/billing/plan` | `apps.identity.mobile_flows.MobilePlanView` |
| POST | `/api/v1/mobile/billing/resend` | `apps.identity.mobile_flows.MemberResendView` |
| GET, POST | `/api/v1/mobile/cases` | `apps.identity.mobile.MobileCasesView` |
| GET, PATCH | `/api/v1/mobile/cases/<uuid:case_id>` | `apps.identity.mobile.MobileCaseView` |
| GET, POST | `/api/v1/mobile/cases/<uuid:case_id>/documents` | `apps.identity.mobile_flows.DocumentsView` |
| GET, POST | `/api/v1/mobile/cases/<uuid:case_id>/documents/uploads` | `apps.identity.mobile_flows.DocumentsView` |
| GET, POST | `/api/v1/mobile/cases/<uuid:case_id>/messages` | `apps.identity.mobile.MobileMessagesView` |
| GET | `/api/v1/mobile/cases/<uuid:case_id>/proposals` | `apps.identity.mobile.MobileProposalsView` |
| POST | `/api/v1/mobile/cases/<uuid:case_id>/proposals/<uuid:proposal_id>/decision` | `apps.identity.mobile.MobileProposalDecisionView` |
| GET | `/api/v1/mobile/cases/<uuid:case_id>/requests` | `apps.identity.mobile_flows.RequestsView` |
| POST | `/api/v1/mobile/cases/<uuid:case_id>/requests/<uuid:request_id>/response` | `apps.identity.mobile_flows.RespondView` |
| POST | `/api/v1/mobile/cases/<uuid:case_id>/submit` | `apps.identity.mobile_flows.SubmitView` |
| GET | `/api/v1/mobile/cases/<uuid:case_id>/timeline` | `apps.identity.mobile.MobileTimelineView` |
| GET, POST | `/api/v1/mobile/cases/<uuid:case_id>/workflow` | `apps.identity.mobile_flows.WorkView` |
| GET | `/api/v1/mobile/cases/catalog` | `apps.identity.mobile_flows.CatalogView` |
| GET | `/api/v1/mobile/dashboard` | `apps.identity.mobile.MobileDashboardView` |
| POST | `/api/v1/mobile/documents/<uuid:document_id>/versions` | `apps.identity.mobile_flows.VersionsView` |
| GET | `/api/v1/mobile/documents/<uuid:document_id>/versions/<uuid:version_id>/content` | `apps.identity.mobile_flows.DownloadView` |
| PATCH | `/api/v1/mobile/me` | `apps.identity.mobile_flows.ProfileView` |
| GET | `/api/v1/mobile/notifications` | `apps.identity.mobile_flows.NoticesView` |
| POST | `/api/v1/mobile/notifications/<uuid:notification_id>/read` | `apps.identity.mobile_flows.ReadNoticeView` |
| GET, POST | `/api/v1/mobile/privacy/requests` | `apps.identity.mobile_flows.PrivacyRequestsView` |
| POST | `/api/v1/mobile/uploads/<uuid:upload_id>/authorize` | `apps.identity.mobile_flows.AuthorizeView` |
| POST | `/api/v1/mobile/uploads/<uuid:upload_id>/complete` | `apps.identity.mobile_flows.CompleteView` |
| POST | `/api/v1/mobile/uploads/<uuid:upload_id>/content` | `apps.identity.mobile_flows.UploadContentView` |
| GET | `/api/v1/notifications` | `apps.communication.views.NotificationsView` |
| POST | `/api/v1/notifications/<uuid:notification_id>/read` | `apps.communication.views.NotificationReadView` |
| GET, POST | `/api/v1/privacy/requests` | `apps.privacy.views.RequestsView` |
| POST | `/api/v1/privacy/requests/<uuid:pk>/resolve` | `apps.privacy.views.ResolveView` |
| GET | `/api/v1/ready` | `config.views.readiness` |
| POST | `/api/v1/uploads/<uuid:upload_id>/authorize` | `apps.documents.views.AuthorizeUploadView` |
| POST | `/api/v1/uploads/<uuid:upload_id>/complete` | `apps.documents.views.CompleteView` |
| POST | `/api/v1/uploads/<uuid:upload_id>/content` | `apps.documents.views.ContentView` |
