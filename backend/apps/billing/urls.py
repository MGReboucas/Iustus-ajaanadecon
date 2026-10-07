from django.urls import path
from .views import PlanView, CardKeyView, CheckoutView, ActivateView, ResendAccessView, WebhookView

urlpatterns = [
    path("billing/plan", PlanView.as_view()),
    path("billing/card-key", CardKeyView.as_view()),
    path("billing/checkout", CheckoutView.as_view()),
    path("billing/activate", ActivateView.as_view()),
    path("billing/resend", ResendAccessView.as_view()),
    path("billing/webhook", WebhookView.as_view()),
]
