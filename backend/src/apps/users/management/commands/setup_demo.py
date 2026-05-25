"""Create demo organization and user for live demos."""
from django.core.management.base import BaseCommand

from apps.users.models import Organization, User


class Command(BaseCommand):
    help = 'Create demo organization and login user (demo@example.com / demo12345)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--noinput',
            action='store_true',
            help='Skip confirmation prompts',
        )

    def handle(self, *args, **options):
        org, created = Organization.objects.get_or_create(
            name='Demo Organization',
            defaults={'api_secret_hash': 'demo'},
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created Demo Organization'))

        user, created = User.objects.get_or_create(
            email='demo@example.com',
            organization=org,
            defaults={
                'first_name': 'Demo',
                'last_name': 'User',
                'role': 'admin',
                'is_staff': True,
            },
        )
        if created:
            user.set_password('demo12345')
            user.save()
            self.stdout.write(self.style.SUCCESS(
                'Demo user ready: demo@example.com / demo12345'
            ))
        else:
            self.stdout.write('Demo user already exists: demo@example.com')
