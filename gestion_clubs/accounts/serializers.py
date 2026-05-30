# accounts/serializers.py

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Utilisateur, Notification


# ──────────────────────────────────────────────────────────────────
# SERIALIZER D'INSCRIPTION
# Gère la création d'un nouveau compte utilisateur.
# Il valide les données envoyées par le client avant
# de créer l'objet en base de données.
# ──────────────────────────────────────────────────────────────────
class InscriptionSerializer(serializers.ModelSerializer):

    # Ces champs sont déclarés manuellement car ils ont une logique spéciale :
    # - write_only=True : ils sont acceptés en entrée mais jamais renvoyés
    # - required=True   : ils sont obligatoires
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],  # Vérifie la robustesse du mot de passe
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        label="Confirmation du mot de passe"
    )

    class Meta:
        model = Utilisateur
        # Champs acceptés lors de l'inscription
        fields = ['id', 'email', 'nom', 'prenom', 'password', 'password2']
        extra_kwargs = {
            'email': {'required': True},
            'nom':   {'required': True},
            'prenom':{'required': True},
        }

    def validate(self, attrs):
        """
        Validation globale : appelée après la validation de chaque champ.
        On vérifie ici que les deux mots de passe correspondent.
        Si non, on lève une ValidationError qui sera renvoyée au client.
        """
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Les deux mots de passe ne correspondent pas."
            })
        return attrs

    def create(self, validated_data):
        """
        Création de l'utilisateur en base de données.
        On retire password2 car il ne correspond à aucun champ du modèle.
        On utilise create_user() (notre Manager) pour hasher le mot de passe.
        """
        # On retire password2 du dictionnaire, on n'en a plus besoin
        validated_data.pop('password2')

        # create_user() de notre Manager hache le mot de passe automatiquement
        utilisateur = Utilisateur.objects.create_user(
            email=validated_data['email'],
            nom=validated_data['nom'],
            prenom=validated_data['prenom'],
            password=validated_data['password'],
            # Par défaut : rôle VISITEUR (défini dans le modèle)
        )
        return utilisateur


# ──────────────────────────────────────────────────────────────────
# SERIALIZER DE PROFIL
# Utilisé pour lire et mettre à jour les infos d'un utilisateur.
# NE gère PAS le mot de passe (sécurité).
# ──────────────────────────────────────────────────────────────────
class UtilisateurProfilSerializer(serializers.ModelSerializer):

    class Meta:
        model = Utilisateur
        # Champs exposés dans la réponse API
        fields = [
            'id',
            'email',
            'nom',
            'prenom',
            'role',
            'photo_profil',
            'date_inscription'
        ]
        # Ces champs ne peuvent pas être modifiés via l'API
        read_only_fields = ['id', 'email', 'role', 'date_inscription']


# ──────────────────────────────────────────────────────────────────
# SERIALIZER DE CHANGEMENT DE MOT DE PASSE
# Séparé du profil pour des raisons de sécurité :
# on ne veut pas mélanger les données de profil et le mot de passe.
# ──────────────────────────────────────────────────────────────────
class ChangerMotDePasseSerializer(serializers.Serializer):
    """
    Ce serializer n'hérite pas de ModelSerializer car
    il ne correspond pas directement à un modèle.
    """
    ancien_password = serializers.CharField(
        required=True,
        write_only=True
    )
    nouveau_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password]
    )
    nouveau_password2 = serializers.CharField(
        required=True,
        write_only=True
    )

    def validate(self, attrs):
        if attrs['nouveau_password'] != attrs['nouveau_password2']:
            raise serializers.ValidationError({
                "nouveau_password": "Les deux mots de passe ne correspondent pas."
            })
        return attrs


# ──────────────────────────────────────────────────────────────────
# SERIALIZER NOTIFICATION
# ──────────────────────────────────────────────────────────────────
class NotificationSerializer(serializers.ModelSerializer):

    type_display = serializers.CharField(
        source='get_type_notification_display',
        read_only=True
    )

    class Meta:
        model  = Notification
        fields = [
            'id',
            'type_notification',
            'type_display',
            'titre',
            'message',
            'est_lue',
            'date_creation',
        ]
        read_only_fields = [
            'id', 'type_notification',
            'titre', 'message', 'date_creation'
        ]