from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Delete admin user'

    def add_arguments(self, parser):
        parser.add_argument('username')

    def handle(self, *args, **options):
        if not User.objects.filter(username=options['username']).exists():
            self.stdout.write(self.style.ERROR('User does not exist'))
            return

        confirm = input('confirm [yN]: ')  # nosec
        if confirm == 'y':
            User.objects.filter(username=options['username']).delete()
            self.stdout.write(self.style.SUCCESS('Successfully deleted admin'))
            return

        self.stdout.write(self.style.WARNING('canceled operation'))
