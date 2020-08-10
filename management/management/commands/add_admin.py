from getpass import getpass

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create a new admin user'

    def handle(self, *args, **options):
        username = input('Username: ')  # nosec
        email = input('E-Mail: ')  # nosec
        password = getpass('Password: ')
        password_confirmation = getpass('Password (confirm):')

        if not password == password_confirmation:
            self.stdout.write(self.style.ERROR('Passwords did not match'))

        user = User(username=username, email=email, is_staff=True)
        user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS(f'Successfully create user {username}'))
