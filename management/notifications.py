from datetime import timedelta

from dateutil import tz
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone, formats

from management.models import Appointment, Settings


def send_reminders(appointment: Appointment):
    admins = appointment.admins.all()
    context = {
        'sender': Settings.get(Settings.SETTING_SENDER),
        'admins': admins,
        'appointment': appointment,
        'reminder_note': Settings.get(Settings.SETTING_REMINDER_NOTE)
    }
    for admin in admins:
        context['recipient'] = admin.name
        message = render_to_string('management/mails/reminder.j2', context=context)
        start_time = formats.date_format(
            appointment.start_time + tz.gettz(settings.TIME_ZONE).utcoffset(appointment.start_time),
            "DATETIME_FORMAT", use_l10n=True)
        send_mail(
            f'Erinnerung: Sprechstunde {start_time}',
            message,
            settings.EMAIL_SENDER,
            [admin.email],
            fail_silently=True
        )


def send_understaffed(appointment: Appointment):
    if appointment.admins.all().count() >= settings.APPOINTMENT_UNDERSTAFFED_THRESHOLD:  # enough people, do nothing
        return

    context = {
        'sender': Settings.get(Settings.SETTING_SENDER),
        'appointment': appointment
    }
    message = render_to_string('management/mails/understaffed.j2', context=context)
    start_time = formats.date_format(
        appointment.start_time + tz.gettz(settings.TIME_ZONE).utcoffset(appointment.start_time),
        "DATETIME_FORMAT", use_l10n=True)
    send_mail(
        f'Sprechstunde {start_time}',
        message,
        settings.EMAIL_SENDER,
        [Settings.get(Settings.SETTING_MAILING_LIST)],
        fail_silently=False
    )


def send_enter_new_appointment():
    context = {
        'sender': Settings.get(Settings.SETTING_SENDER)
    }
    message = render_to_string('management/mails/enter_new_appointments.j2', context=context)
    send_mail(
        'Neue Sprechstundentermine eintragen',
        message,
        settings.EMAIL_SENDER,
        [settings.EMAIL_VORSTAND],
        fail_silently=False
    )


def check_for_enough_dates():
    """
    Check for appointments to exist for at least 8 weeks in advance
    """
    deadline = timezone.now() + relativedelta(weeks=8)
    last_appointment = Appointment.objects.filter(start_time__gte=deadline)
    if last_appointment.exists():  # we have enough appointments, do nothing
        return

    send_enter_new_appointment()


def process_reminders():
    today = timezone.now()
    tomorrow = today + timedelta(days=1)
    for appointment in Appointment.objects.all(reminder_sent=False, start_time__gt=today, end_time__lte=tomorrow):
        send_understaffed(appointment)
        send_reminders(appointment)

        appointment.reminder_sent = True
        appointment.save()
