# clubs/admin.py

from django.contrib import admin
from .models import Club, RoleClub, Adhesion


# ──────────────────────────────────────────────────────────────────
# INLINE — Affiche les adhésions directement dans la page d'un club
# ──────────────────────────────────────────────────────────────────
class AdhesionInline(admin.TabularInline):
    model = Adhesion
    extra = 0                          # Pas de lignes vides par défaut
    readonly_fields = ('date_debut',)
    fields = ('utilisateur', 'roles_club', 'est_actif', 'ajoute_par', 'date_debut')


# ──────────────────────────────────────────────────────────────────
# INLINE — Affiche les rôles disponibles dans la page d'un club
# ──────────────────────────────────────────────────────────────────
class RoleClubInline(admin.TabularInline):
    model = RoleClub
    extra = 0
    fields = ('libelle', 'permissions')


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display  = (
        'nom', 'filiere', 'statut',
        'createur', 'nombre_membres', 'date_creation'
    )
    list_filter   = ('statut', 'filiere')
    search_fields = ('nom', 'mission')
    readonly_fields = ('date_creation', 'date_validation', 'valide_par')

    # Affiche les rôles et adhésions directement dans le club
    inlines = [RoleClubInline, AdhesionInline]

    # Organisation des champs dans le formulaire
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'mission', 'logo', 'filiere')
        }),
        ('Statut et validation', {
            'fields': ('statut', 'valide_par', 'date_validation')
        }),
        ('Métadonnées', {
            'fields': ('createur', 'date_creation'),
            'classes': ('collapse',)   # Section repliable
        }),
    )


@admin.register(RoleClub)
class RoleClubAdmin(admin.ModelAdmin):
    list_display  = ('libelle', 'club', 'afficher_permissions')
    list_filter   = ('libelle', 'club')
    search_fields = ('club__nom',)

    def afficher_permissions(self, obj):
        """Affiche les permissions sous forme lisible."""
        if obj.permissions:
            return ", ".join(obj.permissions)
        return "Aucune permission"
    afficher_permissions.short_description = "Permissions"


@admin.register(Adhesion)
class AdhesionAdmin(admin.ModelAdmin):
    list_display  = (
        'utilisateur', 'club', 'afficher_roles',
        'est_actif', 'ajoute_par', 'date_debut'
    )
    list_filter   = ('est_actif', 'club')
    search_fields = ('utilisateur__nom', 'utilisateur__email', 'club__nom')
    readonly_fields = ('date_debut',)
    filter_horizontal = ('roles_club',)   # Widget pratique pour ManyToMany

    def afficher_roles(self, obj):
        """Affiche tous les rôles du membre dans le club."""
        roles = obj.roles_club.all()
        if roles:
            return ", ".join([r.get_libelle_display() for r in roles])
        return "Aucun rôle"
    afficher_roles.short_description = "Rôles"


# clubs/admin.py 

from .models import Club, RoleClub, Adhesion, Publication  # ← ajoute Publication

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display  = (
        'titre', 'club', 'auteur',
        'statut', 'est_evenement', 'date_creation'
    )
    list_filter   = ('statut', 'club')
    search_fields = ('titre', 'description', 'club__nom')
    readonly_fields = ('date_creation', 'date_validation', 'valide_par')

    fieldsets = (
        ('Contenu', {
            'fields': ('titre', 'description', 'image')
        }),
        ('Événement', {
            'fields': ('date_debut', 'date_fin'),
            'classes': ('collapse',)
        }),
        ('Validation', {
            'fields': ('statut', 'motif_rejet', 'valide_par', 'date_validation')
        }),
        ('Métadonnées', {
            'fields': ('club', 'auteur', 'date_creation'),
            'classes': ('collapse',)
        }),
    )