from django.core.management.base import BaseCommand

from management.notifications import check_for_enough_dates, process_reminders


class Command(BaseCommand):
    help = 'Processes current reminders'

    def handle(self, *args, **options):
        process_reminders()
        check_for_enough_dates()

        self.stdout.write(self.style.SUCCESS('Successfully processed all reminders and notifications'))
