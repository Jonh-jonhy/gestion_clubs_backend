# accounts/admin.py — version complète

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Utilisateur, Notification


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    model = Utilisateur
    list_display  = ('email', 'nom', 'prenom', 'role', 'is_active')
    list_filter   = ('role', 'is_active')
    search_fields = ('email', 'nom', 'prenom')
    ordering      = ('nom',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Informations personnelles', {'fields': ('nom', 'prenom', 'photo_profil')}),
        ('Rôle et permissions', {'fields': ('role', 'is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nom', 'prenom', 'password1', 'password2', 'role'),
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = (
        'titre', 'destinataire',
        'type_notification', 'est_lue', 'date_creation'
    )
    list_filter   = ('type_notification', 'est_lue')
    search_fields = ('titre', 'destinataire__email')
    readonly_fields = ('date_creation',)