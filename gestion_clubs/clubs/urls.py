# clubs/urls.py

from django.urls import path
from .views import (
    ListeClubsView,
    CreerClubView,
    DetailClubView,
    ValiderClubView,
    SuspendreClubView,
    ArchiverClubView,
    ListeMembresView,
    AjouterMembreView,
    RetirerMembreView,
    GererRolesMembreView,
    ListeRolesClubView,
    ListePublicationsView,
    CreerPublicationView,
    PublicationsEnAttenteView,
    ValiderPublicationView,
    PublicationsClubView,
    StatistiquesView,
)

urlpatterns = [

    # ╔══════════════════════════════════════════════════════════════╗
    # ║  RÈGLE IMPORTANTE : les routes STATIQUES doivent toujours   ║
    # ║  être déclarées AVANT les routes dynamiques (<int:pk>).     ║
    # ║  Django lit les URLs de haut en bas et s'arrête à la        ║
    # ║  première correspondance trouvée.                           ║
    # ╚══════════════════════════════════════════════════════════════╝

    # ── 1. Routes statiques globales ─────────────────────────────
    path('', ListeClubsView.as_view(), name='liste_clubs'),
    path('creer/', CreerClubView.as_view(), name='creer_club'),
    path('statistiques/', StatistiquesView.as_view(), name='statistiques'),

    # ── 2. Publications globales (statiques, sans <pk>) ───────────
    # Ces routes DOIVENT être avant <int:pk>/ sinon Django
    # essaie de convertir "publications" en entier → erreur 404
    path('publications/', ListePublicationsView.as_view(), name='liste_publications'),
    path('publications/en-attente/', PublicationsEnAttenteView.as_view(), name='publications_en_attente'),
    path('publications/<int:pub_pk>/valider/', ValiderPublicationView.as_view(), name='valider_publication'),

    # ── 3. Routes dynamiques avec <int:pk> (EN DERNIER) ──────────
    path('<int:pk>/', DetailClubView.as_view(), name='detail_club'),
    path('<int:pk>/valider/', ValiderClubView.as_view(), name='valider_club'),
    path('<int:pk>/suspendre/', SuspendreClubView.as_view(), name='suspendre_club'),
    path('<int:pk>/archiver/', ArchiverClubView.as_view(), name='archiver_club'),

    # ── Rôles du club ─────────────────────────────────────────────
    path('<int:pk>/roles/', ListeRolesClubView.as_view(), name='liste_roles_club'),

    # ── Membres du club ───────────────────────────────────────────
    path('<int:pk>/membres/', ListeMembresView.as_view(), name='liste_membres'),
    path('<int:pk>/membres/ajouter/', AjouterMembreView.as_view(), name='ajouter_membre'),
    path('<int:pk>/membres/<int:user_pk>/retirer/', RetirerMembreView.as_view(), name='retirer_membre'),
    path('<int:pk>/membres/<int:user_pk>/roles/', GererRolesMembreView.as_view(), name='gerer_roles'),

    # ── Publications du club ───────────────────────────────────────
    # "creer" AVANT la liste pour éviter le même problème
    path('<int:pk>/publications/creer/', CreerPublicationView.as_view(), name='creer_publication'),
    path('<int:pk>/publications/', PublicationsClubView.as_view(), name='publications_club'),
]