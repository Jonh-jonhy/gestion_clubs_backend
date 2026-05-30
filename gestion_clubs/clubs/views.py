# clubs/views.py

from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import models as django_models


from accounts.models import Utilisateur
from .models import Club, RoleClub, Adhesion
from accounts.models import Utilisateur, Notification, creer_notification
from .serializers import (
    ClubLectureSerializer,
    ClubCreationSerializer,
    AdhesionLectureSerializer,
    AjoutMembreSerializer,
    GestionRolesSerializer,
    RoleClubSerializer,
)
from .permissions import (
    EstAdministrateur,
    EstPresidentDuClub,
    EstPresidentOuAdministrateur,
    EstMembreDuClub,
)


# ──────────────────────────────────────────────────────────────────
# VUE : LISTE DES CLUBS PUBLICS
# GET /api/clubs/
# Accessible à tous (visiteurs inclus).
# Retourne uniquement les clubs validés.
# ──────────────────────────────────────────────────────────────────
class ListeClubsView(generics.ListAPIView):
    """
    Retourne la liste de tous les clubs validés.
    Accessible sans authentification (page publique).
    """
    serializer_class   = ClubLectureSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Club.objects.filter(statut=Club.VALIDE)


# ──────────────────────────────────────────────────────────────────
# VUE : CRÉATION D'UN CLUB
# POST /api/clubs/creer/
# Tout utilisateur connecté peut soumettre une demande.
# Le club est créé avec le statut EN_ATTENTE.
# L'admin reçoit une notification (à implémenter plus tard).
# ──────────────────────────────────────────────────────────────────
class CreerClubView(generics.CreateAPIView):
    """
    Permet à un utilisateur connecté de soumettre
    une demande de création de club.
    """
    serializer_class   = ClubCreationSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            club = serializer.save()

            # ── Notification à tous les administrateurs ───────────────
            # On notifie chaque admin qu'un nouveau club attend validation
            admins = Utilisateur.objects.filter(
                role=Utilisateur.ADMINISTRATEUR
            )
            for admin in admins:
                creer_notification(
                    destinataire=admin,
                    type_notification=Notification.CLUB_SOUMIS,
                    titre=f"Nouveau club en attente : {club.nom}",
                    message=(
                        f"{request.user.get_full_name()} a soumis une demande "
                        f"de création du club '{club.nom}' ({club.get_filiere_display()}). "
                        f"Mission : {club.mission[:100]}..."
                    )
                )

            return Response({
                "message": (
                    "Demande de création envoyée. "
                    "En attente de validation par l'administrateur."
                ),
                "club": ClubLectureSerializer(club).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────────────────────────
# VUE : DÉTAIL D'UN CLUB
# GET /api/clubs/<pk>/
# Accessible à tous pour les clubs validés.
# ──────────────────────────────────────────────────────────────────
class DetailClubView(generics.RetrieveAPIView):
    """
    Retourne les détails d'un club spécifique.
    """
    serializer_class   = ClubLectureSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Club.objects.filter(statut=Club.VALIDE)


# ──────────────────────────────────────────────────────────────────
# VUE : VALIDATION D'UN CLUB
# POST /api/clubs/<pk>/valider/
# Réservée à l'administrateur.
# Change le statut EN_ATTENTE → VALIDE.
# Crée automatiquement les rôles par défaut du club.
# Nomme le créateur comme président.
# ──────────────────────────────────────────────────────────────────
class ValiderClubView(APIView):
    """
    L'administrateur valide un club en attente.
    Actions automatiques après validation :
    1. Statut → VALIDE
    2. Création des 4 rôles par défaut (Président, Secrétaire, etc.)
    3. Le créateur devient automatiquement Président
    4. Son rôle système passe à MEMBRE
    """
    permission_classes = [EstAdministrateur]

    def post(self, request, pk):
        club = get_object_or_404(Club, pk=pk, statut=Club.EN_ATTENTE)

        # ── 1. Validation du club ─────────────────────────────────
        club.statut         = Club.VALIDE
        club.date_validation = timezone.now()
        club.valide_par     = request.user
        club.save()

        # ── Notification au créateur ──────────────────────────────────
        creer_notification(
            destinataire=club.createur,
            type_notification=Notification.CLUB_VALIDE,
            titre=f"Votre club '{club.nom}' a été validé !",
            message=(
                f"Félicitations ! Votre club '{club.nom}' a été validé "
                f"par l'administrateur. Vous êtes automatiquement "
                f"nommé Président. Vous pouvez maintenant ajouter "
                f"des membres et créer des publications."
            )
        )

        # ── 2. Création des rôles par défaut ──────────────────────
        # Chaque club validé reçoit automatiquement ses 4 rôles
        permissions_par_role = {
            RoleClub.PRESIDENT: [
                'ajouter_membre',
                'retirer_membre',
                'attribuer_role',
                'publier',
                'gerer_activites',
            ],
            RoleClub.SECRETAIRE: [
                'publier',
                'gerer_activites',
            ],
            RoleClub.TRESORIER: [
                'gerer_finances',
            ],
            RoleClub.MEMBRE: [],
        }

        roles_crees = {}
        for libelle, permissions in permissions_par_role.items():
            role, _ = RoleClub.objects.get_or_create(
                libelle=libelle,
                club=club,
                defaults={'permissions': permissions}
            )
            roles_crees[libelle] = role

        # ── 3. Le créateur devient président ──────────────────────
        adhesion, _ = Adhesion.objects.get_or_create(
            utilisateur=club.createur,
            club=club,
            defaults={'ajoute_par': request.user}
        )

        # On lui attribue le rôle président via notre méthode métier
        adhesion.attribuer_role(roles_crees[RoleClub.PRESIDENT])

        # ── 4. Promotion du créateur en MEMBRE système ────────────
        club.createur.promouvoir_en_membre()

        return Response({
            "message": f"Le club '{club.nom}' a été validé avec succès.",
            "club": ClubLectureSerializer(club).data
        }, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────
# VUE : SUSPENSION / ARCHIVAGE D'UN CLUB
# POST /api/clubs/<pk>/suspendre/
# POST /api/clubs/<pk>/archiver/
# Réservées à l'administrateur.
# ──────────────────────────────────────────────────────────────────
class SuspendreClubView(APIView):
    """Suspend un club validé."""
    permission_classes = [EstAdministrateur]

    def post(self, request, pk):
        club = get_object_or_404(Club, pk=pk, statut=Club.VALIDE)
        club.statut = Club.SUSPENDU
        club.save()

        # ── Notification au président du club ─────────────────────────
        adhesion_president = Adhesion.objects.filter(
            club=club,
            est_actif=True,
            roles_club__libelle=RoleClub.PRESIDENT
        ).first()

        if adhesion_president:
            creer_notification(
                destinataire=adhesion_president.utilisateur,
                type_notification=Notification.CLUB_SUSPENDU,
                titre=f"Votre club '{club.nom}' a été suspendu",
                message=(
                    f"Le club '{club.nom}' a été suspendu par "
                    f"l'administrateur. Contactez l'administration "
                    f"pour plus d'informations."
                )
            )

        return Response({
            "message": f"Le club '{club.nom}' a été suspendu."
        }, status=status.HTTP_200_OK)


class ArchiverClubView(APIView):
    """Archive un club (action irréversible depuis l'API)."""
    permission_classes = [EstAdministrateur]

    def post(self, request, pk):
        club = get_object_or_404(Club, pk=pk)
        club.statut = Club.ARCHIVE
        club.save()

        return Response({
            "message": f"Le club '{club.nom}' a été archivé."
        }, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────
# VUE : LISTE DES MEMBRES D'UN CLUB
# GET /api/clubs/<pk>/membres/
# Accessible aux membres du club et à l'admin.
# ──────────────────────────────────────────────────────────────────
class ListeMembresView(generics.ListAPIView):
    """
    Retourne la liste des membres actifs d'un club.
    Réservée aux membres du club et à l'administrateur.
    """
    serializer_class   = AdhesionLectureSerializer
    permission_classes = [EstPresidentOuAdministrateur | EstMembreDuClub]

    def get_queryset(self):
        club_id = self.kwargs.get('pk')
        return Adhesion.objects.filter(
            club_id=club_id,
            est_actif=True
        ).select_related('utilisateur', 'ajoute_par')


# ──────────────────────────────────────────────────────────────────
# VUE : AJOUT D'UN MEMBRE
# POST /api/clubs/<pk>/membres/ajouter/
# Réservée au président du club.
# ──────────────────────────────────────────────────────────────────
class AjouterMembreView(APIView):
    """
    Le président ajoute un utilisateur à son club.
    Il envoie l'email de l'utilisateur et les rôles à attribuer.
    """
    permission_classes = [EstPresidentDuClub]

    def post(self, request, pk):
        club = get_object_or_404(Club, pk=pk, statut=Club.VALIDE)

        serializer = AjoutMembreSerializer(
            data=request.data,
            context={'club': club, 'request': request}
        )

        if serializer.is_valid():
            # Récupère l'utilisateur par son email
            utilisateur = Utilisateur.objects.get(
                email=serializer.validated_data['email']
            )

            # Vérifie que l'utilisateur n'est pas déjà membre
            if Adhesion.objects.filter(
                utilisateur=utilisateur,
                club=club,
                est_actif=True
            ).exists():
                return Response(
                    {"error": "Cet utilisateur est déjà membre du club."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Création de l'adhésion
            adhesion = Adhesion.objects.create(
                utilisateur=utilisateur,
                club=club,
                ajoute_par=request.user
            )
            # Notification au nouveau membre
            creer_notification(
                destinataire=utilisateur,
                type_notification=Notification.MEMBRE_AJOUTE,
                titre=f"Vous avez été ajouté au club '{club.nom}'",
                message=(
                    f"{request.user.get_full_name()} vous a ajouté "
                    f"au club '{club.nom}'. Bienvenue !"
                )
            )            
            # Attribution des rôles si fournis
            roles_ids = serializer.validated_data.get('roles_ids', [])
            if roles_ids:
                roles = RoleClub.objects.filter(id__in=roles_ids, club=club)
                for role in roles:
                    adhesion.attribuer_role(role)

            return Response({
                "message": f"{utilisateur.get_full_name()} a été ajouté au club.",
                "adhesion": AdhesionLectureSerializer(adhesion).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────────────────────────
# VUE : RETIRER UN MEMBRE
# DELETE /api/clubs/<pk>/membres/<user_pk>/retirer/
# Réservée au président du club.
# ──────────────────────────────────────────────────────────────────
class RetirerMembreView(APIView):
    """
    Le président retire un membre de son club.
    L'adhésion n'est pas supprimée mais désactivée (est_actif=False)
    pour garder l'historique.
    """
    permission_classes = [EstPresidentDuClub]

    def delete(self, request, pk, user_pk):
        club     = get_object_or_404(Club, pk=pk, statut=Club.VALIDE)
        adhesion = get_object_or_404(
            Adhesion,
            club=club,
            utilisateur_id=user_pk,
            est_actif=True
        )

        # Empêche le président de se retirer lui-même
        if adhesion.utilisateur == request.user:
            return Response(
                {"error": "Vous ne pouvez pas vous retirer vous-même du club."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Désactivation de l'adhésion (soft delete)
        adhesion.est_actif = False
        adhesion.date_fin  = timezone.now().date()
        adhesion.save()

        return Response(
            {"message": f"{adhesion.utilisateur.get_full_name()} a été retiré du club."},
            status=status.HTTP_200_OK
        )


# ──────────────────────────────────────────────────────────────────
# VUE : GESTION DES RÔLES D'UN MEMBRE
# PUT /api/clubs/<pk>/membres/<user_pk>/roles/
# Président : peut modifier les rôles simples
# Administrateur : peut aussi transférer le rôle président
# ──────────────────────────────────────────────────────────────────
class GererRolesMembreView(APIView):
    """
    Modifie les rôles d'un membre dans un club.
    - Le président peut attribuer/retirer les rôles simples.
    - Seul l'administrateur peut transférer le rôle de président.
    """
    permission_classes = [EstPresidentOuAdministrateur]

    def put(self, request, pk, user_pk):
        club     = get_object_or_404(Club, pk=pk, statut=Club.VALIDE)
        adhesion = get_object_or_404(
            Adhesion,
            club=club,
            utilisateur_id=user_pk,
            est_actif=True
        )

        serializer = GestionRolesSerializer(
            data=request.data,
            context={'club': club, 'request': request}
        )

        if serializer.is_valid():
            roles_ids    = serializer.validated_data['roles_ids']
            nouveaux_roles = RoleClub.objects.filter(
                id__in=roles_ids,
                club=club
            )

            # Remplacement complet des rôles via notre méthode métier
            adhesion.remplacer_tous_les_roles(nouveaux_roles)

            return Response({
                "message": "Rôles mis à jour avec succès.",
                "adhesion": AdhesionLectureSerializer(adhesion).data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# clubs/views.py — ajoute ces imports en haut

from .models import Club, RoleClub, Adhesion, Publication   # ← ajoute Publication
from .serializers import (
    # ... tes imports existants ...
    PublicationLectureSerializer,
    PublicationCreationSerializer,
    ValidationPublicationSerializer,
)
from .permissions import (
    # ... tes imports existants ...
    PeutPublier,
)


# ──────────────────────────────────────────────────────────────────
# VUE : LISTE DES RÔLES D'UN CLUB
# GET /api/clubs/<pk>/roles/
# Permet au président de voir les rôles disponibles
# avant d'ajouter un membre afin de connaître les IDs exacts.
# ──────────────────────────────────────────────────────────────────
class ListeRolesClubView(generics.ListAPIView):
    """
    Retourne tous les rôles disponibles dans un club.
    Le président consulte cette liste pour connaître
    les IDs à utiliser lors de l'ajout d'un membre.

    Exemple de réponse :
    [
        {"id": 1, "libelle": "president", "libelle_display": "Président"},
        {"id": 2, "libelle": "secretaire", "libelle_display": "Secrétaire"},
        {"id": 3, "libelle": "tresorier", "libelle_display": "Trésorier"},
        {"id": 4, "libelle": "membre", "libelle_display": "Membre"}
    ]
    """
    serializer_class   = RoleClubSerializer
    permission_classes = [EstPresidentOuAdministrateur]

    def get_queryset(self):
        club_id = self.kwargs.get('pk')
        return RoleClub.objects.filter(club_id=club_id)


# ──────────────────────────────────────────────────────────────────
# VUE : LISTE DES PUBLICATIONS PUBLIQUES
# GET /api/publications/
# Accessible à tous (visiteurs inclus).
# Retourne uniquement les publications validées.
# ──────────────────────────────────────────────────────────────────
class ListePublicationsView(generics.ListAPIView):
    """
    Retourne toutes les publications validées, tous clubs confondus.
    C'est la page d'accueil publique de la plateforme.
    """
    serializer_class   = PublicationLectureSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Publication.objects.filter(
            statut=Publication.PUBLIEE
        ).select_related('auteur', 'club')

        # Filtrage optionnel par club via query param
        # Exemple : /api/publications/?club=1
        club_id = self.request.query_params.get('club')
        if club_id:
            queryset = queryset.filter(club_id=club_id)

        return queryset


# ──────────────────────────────────────────────────────────────────
# VUE : CRÉER UNE PUBLICATION
# POST /api/clubs/<pk>/publications/creer/
# Réservée au président et au secrétaire du club.
# ──────────────────────────────────────────────────────────────────


class CreerPublicationView(APIView):
    """
    Le président ou le secrétaire crée une publication
    pour son club. Elle est mise EN_ATTENTE jusqu'à
    validation par l'administrateur.

    Méthode : POST
    URL : /api/clubs/<pk>/publications/creer/
    Permission : PeutPublier (président ou secrétaire)
    """
    permission_classes = [PeutPublier]

    def post(self, request, pk):
        club = get_object_or_404(Club, pk=pk, statut=Club.VALIDE)

        serializer = PublicationCreationSerializer(
            data=request.data,
            context={'request': request, 'club': club}
        )

        if serializer.is_valid():
            publication = serializer.save()

            # ── Notification à tous les administrateurs ───────────
            admins = Utilisateur.objects.filter(role=Utilisateur.ADMINISTRATEUR)
            for admin in admins:
                creer_notification(
                    destinataire=admin,
                    type_notification=Notification.PUBLICATION_SOUMISE,
                    titre=f"Nouvelle publication en attente : {publication.titre}",
                    message=(
                        f"{request.user.get_full_name()} du club "
                        f"'{club.nom}' a soumis une publication "
                        f"intitulée '{publication.titre}' en attente de validation."
                    )
                )

            return Response({
                "message": (
                    "Publication soumise avec succès. "
                    "En attente de validation par l'administrateur."
                ),
                "publication": PublicationLectureSerializer(publication).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# ──────────────────────────────────────────────────────────────────
# VUE : LISTE DES PUBLICATIONS EN ATTENTE
# GET /api/publications/en-attente/
# Réservée à l'administrateur.
# ──────────────────────────────────────────────────────────────────
class PublicationsEnAttenteView(generics.ListAPIView):
    """
    L'administrateur consulte toutes les publications
    en attente de validation.
    """
    serializer_class   = PublicationLectureSerializer
    permission_classes = [EstAdministrateur]

    def get_queryset(self):
        return Publication.objects.filter(
            statut=Publication.EN_ATTENTE
        ).select_related('auteur', 'club')


# ──────────────────────────────────────────────────────────────────
# VUE : VALIDER OU REJETER UNE PUBLICATION
# POST /api/publications/<pub_pk>/valider/
# Réservée à l'administrateur.
# ──────────────────────────────────────────────────────────────────
# clubs/views.py 

class ValiderPublicationView(APIView):
    """
    L'administrateur valide ou rejette une publication.

    Méthode : POST
    URL : /api/clubs/publications/<pub_pk>/valider/
    Permission : EstAdministrateur uniquement

    Body attendu :
        { "action": "publier" }
        { "action": "rejeter", "motif_rejet": "..." }
    """
    permission_classes = [EstAdministrateur]

    def post(self, request, pub_pk):
        publication = get_object_or_404(
            Publication,
            pk=pub_pk,
            statut=Publication.EN_ATTENTE
        )

        serializer = ValidationPublicationSerializer(data=request.data)

        if serializer.is_valid():
            action = serializer.validated_data['action']

            if action == 'publier':
                publication.statut          = Publication.PUBLIEE
                publication.date_validation = timezone.now()
                publication.valide_par      = request.user
                publication.motif_rejet     = None
                publication.save()

                # Notification à l'auteur
                creer_notification(
                    destinataire=publication.auteur,
                    type_notification=Notification.PUBLICATION_VALIDEE,
                    titre=f"Publication '{publication.titre}' publiée !",
                    message=(
                        f"Votre publication '{publication.titre}' "
                        f"pour le club '{publication.club.nom}' "
                        f"a été validée et est maintenant visible publiquement."
                    )
                )

                return Response({
                    "message": f"La publication '{publication.titre}' a été publiée.",
                    "publication": PublicationLectureSerializer(publication).data
                }, status=status.HTTP_200_OK)

            elif action == 'rejeter':
                publication.statut      = Publication.REJETEE
                publication.motif_rejet = serializer.validated_data['motif_rejet']
                publication.valide_par  = request.user
                publication.save()

                # Notification à l'auteur avec le motif
                creer_notification(
                    destinataire=publication.auteur,
                    type_notification=Notification.PUBLICATION_REJETEE,
                    titre=f"Publication '{publication.titre}' rejetée",
                    message=(
                        f"Votre publication '{publication.titre}' "
                        f"a été rejetée. Motif : {publication.motif_rejet}"
                    )
                )

                return Response({
                    "message": f"La publication '{publication.titre}' a été rejetée.",
                    "publication": PublicationLectureSerializer(publication).data
                }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# ──────────────────────────────────────────────────────────────────
# VUE : PUBLICATIONS D'UN CLUB SPÉCIFIQUE
# GET /api/clubs/<pk>/publications/
# Membres du club : voient toutes les publications (même en attente)
# Visiteurs : voient uniquement les publications publiées
# ──────────────────────────────────────────────────────────────────
class PublicationsClubView(generics.ListAPIView):
    """
    Retourne les publications d'un club spécifique.
    Le filtre dépend du profil de l'utilisateur connecté.
    """
    serializer_class   = PublicationLectureSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        club_id = self.kwargs.get('pk')
        user    = self.request.user

        # Les membres du club et l'admin voient tout
        if user.is_authenticated:
            est_membre = Adhesion.objects.filter(
                utilisateur=user,
                club_id=club_id,
                est_actif=True
            ).exists()

            if est_membre or user.est_administrateur:
                return Publication.objects.filter(
                    club_id=club_id
                ).select_related('auteur', 'club')

        # Les visiteurs ne voient que les publications publiées
        return Publication.objects.filter(
            club_id=club_id,
            statut=Publication.PUBLIEE
        ).select_related('auteur', 'club')


# clubs/views.py 

from django.db.models import Count

# ──────────────────────────────────────────────────────────────────
# VUE : STATISTIQUES GÉNÉRALES
# GET /api/clubs/statistiques/
# Réservée à l'administrateur.
# ──────────────────────────────────────────────────────────────────
class StatistiquesView(APIView):
    """
    Retourne les statistiques globales de la plateforme.
    Utilisé pour le tableau de bord de l'administrateur.

    Méthode : GET
    URL : /api/clubs/statistiques/
    Permission : EstAdministrateur uniquement
    """
    permission_classes = [EstAdministrateur]

    def get(self, request):
        # ── Statistiques des clubs ────────────────────────────────
        total_clubs      = Club.objects.count()
        clubs_valides    = Club.objects.filter(statut=Club.VALIDE).count()
        clubs_en_attente = Club.objects.filter(statut=Club.EN_ATTENTE).count()
        clubs_suspendus  = Club.objects.filter(statut=Club.SUSPENDU).count()

        # ── Statistiques des utilisateurs ─────────────────────────
        total_utilisateurs = Utilisateur.objects.count()
        total_membres      = Utilisateur.objects.filter(
            role=Utilisateur.MEMBRE
        ).count()
        total_visiteurs    = Utilisateur.objects.filter(
            role=Utilisateur.VISITEUR
        ).count()

        # ── Statistiques des publications ─────────────────────────
        total_publications      = Publication.objects.count()
        publications_publiees   = Publication.objects.filter(
            statut=Publication.PUBLIEE
        ).count()
        publications_en_attente = Publication.objects.filter(
            statut=Publication.EN_ATTENTE
        ).count()

        # ── Top 5 clubs par nombre de membres actifs ──────────────
        # On utilise django_models.Q pour filtrer dans l'annotation
        classement_clubs = Club.objects.filter(
            statut=Club.VALIDE
        ).annotate(
            nb_membres=Count(
                'adhesions',
                filter=django_models.Q(adhesions__est_actif=True)
            )
        ).order_by('-nb_membres').values(
            'id', 'nom', 'filiere', 'nb_membres'
        )[:5]

        return Response({
            "clubs": {
                "total":      total_clubs,
                "valides":    clubs_valides,
                "en_attente": clubs_en_attente,
                "suspendus":  clubs_suspendus,
            },
            "utilisateurs": {
                "total":     total_utilisateurs,
                "membres":   total_membres,
                "visiteurs": total_visiteurs,
            },
            "publications": {
                "total":      total_publications,
                "publiees":   publications_publiees,
                "en_attente": publications_en_attente,
            },
            "top_clubs": list(classement_clubs),
        }, status=status.HTTP_200_OK)