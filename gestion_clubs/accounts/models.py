from django.db import models

# Create your models here.
# accounts/models.py

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


# ──────────────────────────────────────────────────────────────────
# MANAGER PERSONNALISÉ
# Le Manager contrôle la création des utilisateurs.
# On en a besoin parce qu'on utilise l'email comme identifiant
# au lieu du username (comportement par défaut de Django).
# ──────────────────────────────────────────────────────────────────
class UtilisateurManager(BaseUserManager):

    def create_user(self, email, nom, prenom, password=None, **extra_fields):
        """
        Crée et enregistre un utilisateur standard.
        Cette méthode est appelée lors d'une inscription normale.
        """
        if not email:
            raise ValueError("L'adresse email est obligatoire")

        # Normalise l'email (met le domaine en minuscule)
        email = self.normalize_email(email)

        utilisateur = self.model(
            email=email,
            nom=nom,
            prenom=prenom,
            **extra_fields
        )
        # hash le mot de passe avant de le sauvegarder
        utilisateur.set_password(password)
        utilisateur.save(using=self._db)
        return utilisateur

    def create_superuser(self, email, nom, prenom, password=None, **extra_fields):
        """
        Crée un super administrateur (accès au panneau Django /admin).
        Utilisé uniquement via la commande : python manage.py createsuperuser
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', Utilisateur.ADMINISTRATEUR)
        return self.create_user(email, nom, prenom, password, **extra_fields)


# ──────────────────────────────────────────────────────────────────
# MODÈLE UTILISATEUR PRINCIPAL
# On remplace le modèle User de Django par le nôtre.
# Cela nous donne un contrôle total sur les champs et la logique.
# ──────────────────────────────────────────────────────────────────
class Utilisateur(AbstractBaseUser, PermissionsMixin):
    """
    Représente tout utilisateur du système.
    Correspond à la classe 'Utilisateur' du diagramme de classe.

    Les trois rôles principaux du système :
    - VISITEUR    : peut consulter les publications publiques
    - MEMBRE      : peut rejoindre/créer un club
    - ADMINISTRATEUR : gère et valide les clubs
    """

    # ── Constantes des rôles ──────────────────────────────────────
    VISITEUR = 'visiteur'
    MEMBRE = 'membre'
    ADMINISTRATEUR = 'administrateur'

    ROLE_CHOICES = [
        (VISITEUR, 'Visiteur'),
        (MEMBRE, 'Membre'),
        (ADMINISTRATEUR, 'Administrateur'),
    ]

    # ── Champs du modèle ─────────────────────────────────────────
    # id est automatiquement créé par Django (AutoField)

    email = models.EmailField(
        unique=True,
        verbose_name="Adresse email",
        help_text="Utilisé comme identifiant de connexion"
    )
    nom = models.CharField(
        max_length=100,
        verbose_name="Nom de famille"
    )
    prenom = models.CharField(
        max_length=100,
        verbose_name="Prénom"
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=VISITEUR,       # Par défaut, tout inscrit est un visiteur
        verbose_name="Rôle dans le système"
    )
    photo_profil = models.ImageField(
        upload_to='profils/',   # Les photos seront dans media/profils/
        null=True,
        blank=True,
        verbose_name="Photo de profil"
    )
    date_inscription = models.DateTimeField(
        auto_now_add=True,      # Rempli automatiquement à la création
        verbose_name="Date d'inscription"
    )

    # ── Champs requis par Django pour l'authentification ─────────
    is_active = models.BooleanField(
        default=True,
        verbose_name="Compte actif",
        help_text="Désactivez pour bannir un utilisateur sans le supprimer"
    )
    is_staff = models.BooleanField(
        default=False,
        verbose_name="Accès admin Django",
        help_text="Donne accès au panneau /admin de Django"
    )

    # ── Configuration du Manager ─────────────────────────────────
    objects = UtilisateurManager()

    # Django utilise ce champ comme identifiant de connexion
    USERNAME_FIELD = 'email'

    # Champs obligatoires en plus de email et password
    REQUIRED_FIELDS = ['nom', 'prenom']

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        db_table = "utilisateurs"   # Nom de la table en base de données

    def __str__(self):
        return f"{self.prenom} {self.nom} ({self.email})"

    def get_full_name(self):
        """Retourne le nom complet de l'utilisateur."""
        return f"{self.prenom} {self.nom}"

    @property
    def est_administrateur(self):
        """Vérifie si l'utilisateur est administrateur."""
        return self.role == self.ADMINISTRATEUR

    @property
    def est_membre(self):
        """Vérifie si l'utilisateur est membre."""
        return self.role == self.MEMBRE


    def promouvoir_en_membre(self):
        """
        #Appelée automatiquement quand l'utilisateur rejoint son premier club.
        Change le rôle de VISITEUR à MEMBRE.
        """
        if self.role == self.VISITEUR:
            self.role = self.MEMBRE
            self.save()

# accounts/models.py 

# ──────────────────────────────────────────────────────────────────
# MODÈLE NOTIFICATION
# Système de notifications internes.
# Une notification est créée automatiquement quand :
# - Un club est soumis à validation (→ admin)
# - Une publication est soumise (→ admin)
# - Un club est validé/rejeté (→ créateur)
# - Une publication est validée/rejetée (→ auteur)
# ──────────────────────────────────────────────────────────────────
class Notification(models.Model):

    # ── Types de notifications ────────────────────────────────────
    CLUB_SOUMIS          = 'club_soumis'
    CLUB_VALIDE          = 'club_valide'
    CLUB_REJETE          = 'club_rejete'
    CLUB_SUSPENDU        = 'club_suspendu'
    PUBLICATION_SOUMISE  = 'publication_soumise'
    PUBLICATION_VALIDEE  = 'publication_validee'
    PUBLICATION_REJETEE  = 'publication_rejetee'
    MEMBRE_AJOUTE        = 'membre_ajoute'

    TYPE_CHOICES = [
        (CLUB_SOUMIS,         'Nouveau club en attente de validation'),
        (CLUB_VALIDE,         'Club validé'),
        (CLUB_REJETE,         'Club rejeté'),
        (CLUB_SUSPENDU,       'Club suspendu'),
        (PUBLICATION_SOUMISE, 'Nouvelle publication en attente'),
        (PUBLICATION_VALIDEE, 'Publication validée'),
        (PUBLICATION_REJETEE, 'Publication rejetée'),
        (MEMBRE_AJOUTE,       'Vous avez été ajouté à un club'),
    ]

    # ── Champs ────────────────────────────────────────────────────
    destinataire = models.ForeignKey(
        'Utilisateur',
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Destinataire"
    )
    type_notification = models.CharField(
        max_length=50,
        choices=TYPE_CHOICES,
        verbose_name="Type de notification"
    )
    titre = models.CharField(
        max_length=200,
        verbose_name="Titre"
    )
    message = models.TextField(
        verbose_name="Contenu du message"
    )
    est_lue = models.BooleanField(
        default=False,
        verbose_name="Notification lue"
    )

    # ── Métadonnées ───────────────────────────────────────────────
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        db_table = "notifications"
        ordering = ['-date_creation']  # Les plus récentes en premier

    def __str__(self):
        return f"{self.get_type_notification_display()} → {self.destinataire.get_full_name()}"


# ──────────────────────────────────────────────────────────────────
# FONCTION UTILITAIRE — CRÉER UNE NOTIFICATION
# Fonction helper appelée depuis les views pour créer
# une notification sans répéter le code partout.
# ──────────────────────────────────────────────────────────────────
def creer_notification(destinataire, type_notification, titre, message):
    """
    Crée une notification pour un utilisateur.

    Paramètres :
        destinataire      : objet Utilisateur
        type_notification : constante de Notification (ex: Notification.CLUB_SOUMIS)
        titre             : str — titre court
        message           : str — message détaillé

    Exemple d'appel depuis une view :
        creer_notification(
            destinataire=admin,
            type_notification=Notification.CLUB_SOUMIS,
            titre="Nouveau club en attente",
            message=f"Le club '{club.nom}' attend votre validation."
        )
    """
    return Notification.objects.create(
        destinataire=destinataire,
        type_notification=type_notification,
        titre=titre,
        message=message
    )