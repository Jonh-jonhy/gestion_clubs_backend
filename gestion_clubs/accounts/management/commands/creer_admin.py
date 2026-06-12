# accounts/management/commands/creer_admin.py

from django.core.management.base import BaseCommand
from accounts.models import Utilisateur

class Command(BaseCommand):
    help = 'Crée un compte administrateur ClubISJ'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str)
        parser.add_argument('password', type=str)
        parser.add_argument('--prenom', type=str, default='Admin')
        parser.add_argument('--nom', type=str, default='Principal')

    def handle(self, *args, **options):
        email = options['email']

        if Utilisateur.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(f'{email} existe déjà — ignoré.')
            )
            return

        admin = Utilisateur.objects.create_superuser(
            email=email,
            password=options['password'],
            nom=options['nom'],
            prenom=options['prenom'],
        )

        self.stdout.write(
            self.style.SUCCESS(f'Administrateur {email} créé !')
        )