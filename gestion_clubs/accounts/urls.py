# accounts/urls.py — version complète

from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    InscriptionView,
    DeconnexionView,
    ProfilView,
    ChangerMotDePasseView,
    ListeNotificationsView,
    MarquerNotificationLueView,
    MarquerToutLuView,
)

urlpatterns = [
    # ── Auth ──────────────────────────────────────────────────────
    path('register/', InscriptionView.as_view(), name='inscription'),
    path('login/', TokenObtainPairView.as_view(), name='connexion'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', DeconnexionView.as_view(), name='deconnexion'),
    path('me/', ProfilView.as_view(), name='profil'),
    path('changer-password/', ChangerMotDePasseView.as_view(), name='changer_password'),

    # ── Notifications ─────────────────────────────────────────────
    path('notifications/', ListeNotificationsView.as_view(), name='notifications'),
    path('notifications/lire-tout/', MarquerToutLuView.as_view(), name='notif_lire_tout'),
    path('notifications/<int:pk>/lire/', MarquerNotificationLueView.as_view(), name='notif_lire'),
]