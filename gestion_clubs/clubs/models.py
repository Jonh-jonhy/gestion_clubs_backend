# clubs/models.py

from django.db import models
from accounts.models import Utilisateur


# ──────────────────────────────────────────────────────────────────
# MODÈLE CLUB
# Représente un club ou une association de l'institut.
# Un club est créé par un utilisateur (le futur président)
# et doit être validé par l'administrateur avant d'être actif.
# ──────────────────────────────────────────────────────────────────
class Club(models.Model):

    # ── Statuts possibles d'un club ───────────────────────────────
    EN_ATTENTE = 'en_attente'
    VALIDE     = 'valide'
    SUSPENDU   = 'suspendu'
    ARCHIVE    = 'archive'

    STATUT_CHOICES = [
        (EN_ATTENTE, 'En attente de validation'),
        (VALIDE,     'Validé'),
        (SUSPENDU,   'Suspendu'),
        (ARCHIVE,    'Archivé'),
    ]

    # ── Filiere possibles d'un club ───────────────────────────────
    GENIE_LOGICIEL      = 'genie_logiciel'
    RESEAUX_TELECOM     = 'reseaux_telecom'
    GENIE_CIVIL         = 'genie_civil'
    COMPTABILITE        = 'comptabilite'
    MARKETING           = 'marketing'
    TOUTES_FILIERES     = 'toutes_filieres'

    FILIERE_CHOICES = [
        (GENIE_LOGICIEL,  'Génie Logiciel'),
        (RESEAUX_TELECOM, 'Réseaux & Télécommunications'),
        (GENIE_CIVIL,     'Génie Civil'),
        (COMPTABILITE,    'Comptabilité'),
        (MARKETING,       'Marketing'),
        (TOUTES_FILIERES, 'Toutes filières'),
    ]

    # ── Champs du modèle ──────────────────────────────────────────
    nom = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Nom du club"
    )
    mission = models.TextField(
        verbose_name="Mission / Description du club"
    )
    logo = models.ImageField(
        upload_to='clubs/logos/',   # Stocké dans media/clubs/logos/
        null=True,
        blank=True,
        verbose_name="Logo du club"
    )
    filiere = models.CharField(
        max_length=150,
        choices=FILIERE_CHOICES,
        default=GENIE_LOGICIEL,
        verbose_name="Filière associée"
    )
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=EN_ATTENTE,         # Tout club commence en attente
        verbose_name="Statut du club"
    )

    # ── Relations ─────────────────────────────────────────────────
    # Le créateur du club (qui deviendra président après validation)
    createur = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,  # Si le créateur est supprimé, le club reste
        null=True,
        related_name='clubs_crees',
        verbose_name="Créateur du club"
    )

    # ── Métadonnées ───────────────────────────────────────────────
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    date_validation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de validation par l'admin"
    )
    valide_par = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clubs_valides',
        verbose_name="Administrateur ayant validé"
    )

    class Meta:
        verbose_name = "Club"
        verbose_name_plural = "Clubs"
        db_table = "clubs"
        ordering = ['-date_creation']   # Les plus récents en premier

    def __str__(self):
        return f"{self.nom} ({self.get_statut_display()})"

    @property
    def nombre_membres(self):
        """Retourne le nombre de membres actifs du club."""
        return self.adhesions.filter(est_actif=True).count()


# ──────────────────────────────────────────────────────────────────
# MODÈLE ROLE CLUB
# Définit les rôles possibles AU SEIN d'un club.
# Différent du rôle système (visiteur/membre/admin).
# Exemples : Président, Secrétaire, Trésorier, Membre simple
# ──────────────────────────────────────────────────────────────────
class RoleClub(models.Model):

    # ── Rôles prédéfinis ──────────────────────────────────────────
    PRESIDENT   = 'president'
    SECRETAIRE  = 'secretaire'
    TRESORIER   = 'tresorier'
    MEMBRE      = 'membre'

    ROLE_CHOICES = [
        (PRESIDENT,  'Président'),
        (SECRETAIRE, 'Secrétaire'),
        (TRESORIER,  'Trésorier'),
        (MEMBRE,     'Membre'),
    ]

    libelle = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        verbose_name="Intitulé du rôle"
    )
    permissions = models.JSONField(
        default=list,
        verbose_name="Permissions associées",
        help_text="Ex: ['ajouter_membre', 'publier', 'valider_cotisation']"
    )
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,  # Si le club est supprimé, les rôles aussi
        related_name='roles',
        verbose_name="Club concerné"
    )

    class Meta:
        verbose_name = "Rôle dans le club"
        verbose_name_plural = "Rôles dans les clubs"
        db_table = "roles_club"
        # Un rôle donné ne peut exister qu'une fois par club
        unique_together = ['libelle', 'club']

    def __str__(self):
        return f"{self.get_libelle_display()} — {self.club.nom}"


# ──────────────────────────────────────────────────────────────────
# MODÈLE ADHÉSION
# Table de liaison entre Utilisateur et Club.
# Représente l'appartenance d'un membre à un club,
# avec son rôle spécifique dans ce club.
# C'est le Président qui crée ces adhésions.
# ──────────────────────────────────────────────────────────────────
class Adhesion(models.Model):

    # ── Relations ─────────────────────────────────────────────────
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='adhesions',
        verbose_name="Membre"
    )
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name='adhesions',
        verbose_name="Club"
    )
    roles_club = models.ManyToManyField(
        RoleClub,
        blank=True,                 # Un membre peut n'avoir aucun rôle spécial
        related_name='adhesions',
        verbose_name="Rôles dans le club"
    )

    # ── Qui a ajouté ce membre ? ──────────────────────────────────
    ajoute_par = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='membres_ajoutes',
        verbose_name="Ajouté par (président)"
    )

    # ── Métadonnées ───────────────────────────────────────────────
    date_debut = models.DateField(
        auto_now_add=True,
        verbose_name="Date d'adhésion"
    )
    date_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de fin (si exclu ou parti)"
    )
    est_actif = models.BooleanField(
        default=True,
        verbose_name="Adhésion active",
        help_text="False si le membre a quitté ou été exclu du club"
    )

    class Meta:
        verbose_name = "Adhésion"
        verbose_name_plural = "Adhésions"
        db_table = "adhesions"
        # Un utilisateur ne peut être membre qu'une fois par club
        unique_together = ['utilisateur', 'club']

    def __str__(self):
        return f"{self.utilisateur.get_full_name()} → {self.club.nom}"

    def save(self, *args, **kwargs):
        """
        Override de save() :
        Quand une adhésion est créée, on vérifie si l'utilisateur
        est encore visiteur. Si oui, on le promeut automatiquement
        en MEMBRE au niveau système.
        """
        super().save(*args, **kwargs)

        # Promotion automatique visiteur → membre
        self.utilisateur.promouvoir_en_membre()

    def attribuer_role(self, role_club):
        """
        Attribue un rôle à ce membre.
        Si c'est le rôle PRÉSIDENT, on le retire d'abord
        à l'ancien président pour garantir l'unicité.

        Exemple d'utilisation dans une view :
            adhesion.attribuer_role(role_president)
        """
        if role_club.libelle == RoleClub.PRESIDENT:
            # On cherche l'adhésion de l'actuel président
            anciennes_adhesions = Adhesion.objects.filter(
                club=self.club,
                est_actif=True,
                roles_club=role_club
            ).exclude(pk=self.pk)   # On exclut l'adhésion actuelle

            # On retire le rôle président à l'ancien président
            for ancienne in anciennes_adhesions:
                ancienne.roles_club.remove(role_club)

        # On attribue le rôle au membre actuel
        self.roles_club.add(role_club)

    def retirer_role(self, role_club):
        """
        Retire un rôle spécifique à ce membre.

        Exemple d'utilisation :
            adhesion.retirer_role(role_tresorier)
        """
        self.roles_club.remove(role_club)

    def remplacer_tous_les_roles(self, nouveaux_roles):
        """
        Remplace tous les rôles du membre par une nouvelle liste.
        Utile quand le président redéfinit complètement les rôles
        d'un membre en une seule opération.

        nouveaux_roles : QuerySet ou liste d'objets RoleClub

        Exemple :
            adhesion.remplacer_tous_les_roles([role_secretaire, role_tresorier])
        """
        # Vérification : si on attribue le rôle président,
        # on l'enlève d'abord à l'actuel président
        for role in nouveaux_roles:
            if role.libelle == RoleClub.PRESIDENT:
                Adhesion.objects.filter(
                    club=self.club,
                    est_actif=True,
                    roles_club=role
                ).exclude(pk=self.pk).update()

                # Retrait du rôle président chez l'ancien
                anciennes = Adhesion.objects.filter(
                    club=self.club,
                    roles_club=role
                ).exclude(pk=self.pk)
                for a in anciennes:
                    a.roles_club.remove(role)

        # Remplacement complet des rôles
        self.roles_club.set(nouveaux_roles)

    @property
    def est_president(self):
        """Vérifie si ce membre est président de ce club."""
        return self.roles_club.filter(libelle=RoleClub.PRESIDENT).exists()

    @property
    def liste_roles(self):
        """Retourne la liste lisible des rôles du membre."""
        return [r.get_libelle_display() for r in self.roles_club.all()]


# clubs/models.py 

# ──────────────────────────────────────────────────────────────────
# MODÈLE PUBLICATION
# Représente une publication faite par un club.
# Seuls le président et le secrétaire peuvent en créer.
# Chaque publication doit être validée par l'administrateur
# avant d'être visible publiquement.
# ──────────────────────────────────────────────────────────────────
class Publication(models.Model):

    # ── Statuts possibles d'une publication ───────────────────────
    EN_ATTENTE = 'en_attente'
    PUBLIEE    = 'publiee'
    REJETEE    = 'rejetee'
    ARCHIVEE   = 'archivee'

    STATUT_CHOICES = [
        (EN_ATTENTE, 'En attente de validation'),
        (PUBLIEE,    'Publiée'),
        (REJETEE,    'Rejetée'),
        (ARCHIVEE,   'Archivée'),
    ]

    # ── Champs principaux ─────────────────────────────────────────
    titre = models.CharField(
        max_length=200,
        verbose_name="Titre de la publication"
    )
    description = models.TextField(
        verbose_name="Contenu / Description"
    )
    image = models.ImageField(
        upload_to='publications/images/',  # media/publications/images/
        null=True,
        blank=True,
        verbose_name="Image de la publication"
    )

    # ── Dates (pour les événements) ───────────────────────────────
    date_debut = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de début de l'événement"
    )
    date_fin = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de fin de l'événement"
    )

    # ── Statut de validation ──────────────────────────────────────
    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default=EN_ATTENTE,
        verbose_name="Statut de la publication"
    )

    # ── Motif de rejet (rempli par l'admin si rejetée) ────────────
    motif_rejet = models.TextField(
        null=True,
        blank=True,
        verbose_name="Motif de rejet",
        help_text="Rempli par l'administrateur en cas de rejet"
    )

    # ── Relations ─────────────────────────────────────────────────
    # Le club auquel appartient cette publication
    club = models.ForeignKey(
        Club,
        on_delete=models.CASCADE,
        related_name='publications',
        verbose_name="Club"
    )

    # L'auteur (président ou secrétaire)
    auteur = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        related_name='publications_creees',
        verbose_name="Auteur"
    )

    # L'admin qui a validé ou rejeté
    valide_par = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='publications_validees',
        verbose_name="Validé/Rejeté par"
    )

    # ── Métadonnées ───────────────────────────────────────────────
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création"
    )
    date_validation = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de validation"
    )

    class Meta:
        verbose_name = "Publication"
        verbose_name_plural = "Publications"
        db_table = "publications"
        ordering = ['-date_creation']  # Les plus récentes en premier

    def __str__(self):
        return f"{self.titre} — {self.club.nom} ({self.get_statut_display()})"

    @property
    def est_evenement(self):
        """
        Retourne True si la publication est un événement
        (elle a une date de début et de fin).
        """
        return self.date_debut is not None and self.date_fin is not None