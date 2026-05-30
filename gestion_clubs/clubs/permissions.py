# clubs/permissions.py

from rest_framework.permissions import BasePermission
from .models import Adhesion, RoleClub


# ──────────────────────────────────────────────────────────────────
# PERMISSION : EST ADMINISTRATEUR SYSTÈME
# Vérifie que l'utilisateur connecté a le rôle administrateur.
# Utilisé pour : valider un club, suspendre, transférer président.
# ──────────────────────────────────────────────────────────────────
class EstAdministrateur(BasePermission):
    """
    Accès réservé aux administrateurs système uniquement.
    """
    message = "Vous devez être administrateur pour effectuer cette action."

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.est_administrateur
        )


# ──────────────────────────────────────────────────────────────────
# PERMISSION : EST PRÉSIDENT DU CLUB
# Vérifie que l'utilisateur connecté est président
# du club concerné par la requête.
# Utilisé pour : ajouter/retirer un membre, gérer les rôles simples.
# ──────────────────────────────────────────────────────────────────
class EstPresidentDuClub(BasePermission):
    """
    Accès réservé au président du club ciblé par la requête.
    Le club est identifié via le paramètre 'pk' dans l'URL.
    """
    message = "Vous devez être président de ce club pour effectuer cette action."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Récupère l'id du club depuis l'URL (ex: /api/clubs/3/membres/)
        club_id = view.kwargs.get('pk')
        if not club_id:
            return False

        # Vérifie qu'il existe une adhésion active avec le rôle président
        return Adhesion.objects.filter(
            utilisateur=request.user,
            club_id=club_id,
            est_actif=True,
            roles_club__libelle=RoleClub.PRESIDENT
        ).exists()


# ──────────────────────────────────────────────────────────────────
# PERMISSION : EST MEMBRE DU CLUB
# Vérifie que l'utilisateur est membre actif du club.
# Utilisé pour : voir les détails internes du club.
# ──────────────────────────────────────────────────────────────────
class EstMembreDuClub(BasePermission):
    """
    Accès réservé aux membres actifs du club ciblé.
    """
    message = "Vous devez être membre de ce club pour accéder à cette ressource."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        club_id = view.kwargs.get('pk')
        if not club_id:
            return False

        return Adhesion.objects.filter(
            utilisateur=request.user,
            club_id=club_id,
            est_actif=True
        ).exists()


# ──────────────────────────────────────────────────────────────────
# PERMISSION : EST PRÉSIDENT OU ADMINISTRATEUR
# Combine les deux permissions ci-dessus.
# Utilisé pour des actions que les deux peuvent faire.
# ──────────────────────────────────────────────────────────────────
class EstPresidentOuAdministrateur(BasePermission):
    """
    Accès autorisé si l'utilisateur est :
    - Président du club concerné, OU
    - Administrateur système
    """
    message = "Vous devez être président du club ou administrateur."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Un administrateur a toujours accès
        if request.user.est_administrateur:
            return True

        # Sinon on vérifie s'il est président du club
        club_id = view.kwargs.get('pk')
        if not club_id:
            return False

        return Adhesion.objects.filter(
            utilisateur=request.user,
            club_id=club_id,
            est_actif=True,
            roles_club__libelle=RoleClub.PRESIDENT
        ).exists()


# clubs/permissions.py 

# ──────────────────────────────────────────────────────────────────
# PERMISSION : PEUT PUBLIER DANS UN CLUB
# Vérifie que l'utilisateur est président OU secrétaire du club.
# ──────────────────────────────────────────────────────────────────
class PeutPublier(BasePermission):
    """
    Accès réservé au président et au secrétaire du club.
    Ces deux rôles ont le droit de créer des publications.
    """
    message = "Seuls le président et le secrétaire peuvent publier."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # L'admin peut tout faire
        if request.user.est_administrateur:
            return True

        club_id = view.kwargs.get('pk')
        if not club_id:
            return False

        # Vérifie que l'utilisateur est président OU secrétaire
        return Adhesion.objects.filter(
            utilisateur=request.user,
            club_id=club_id,
            est_actif=True,
            roles_club__libelle__in=[
                RoleClub.PRESIDENT,
                RoleClub.SECRETAIRE
            ]
        ).exists()