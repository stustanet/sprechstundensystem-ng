from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Create a new admin user'

    def add_arguments(self, parser):
        parser.add_argument('-f', '--full', action='store_true')

    def handle(self, *args, **options):
        if options['full']:
            self.stdout.write(self.style.WARNING('username\tfirst name\tlast name\temail'))
            for user in User.objects.filter(is_staff=True):
                self.stdout.write(f'{user.username}\t{user.first_name}\t{user.last_name}\t{user.email}')
        else:
            self.stdout.write(self.style.WARNING('username\temail'))
            for user in User.objects.filter(is_staff=True):
                self.stdout.write(f'{user.username}\t{user.email}')
