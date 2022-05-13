import calendar
from datetime import datetime, date
from typing import List, Optional

from dateutil import tz
from django.conf import settings
from django.db import models
from django.db.models import QuerySet
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import formats

from management.utils import is_holiday, is_during_lecture_time


class Admin(models.Model):
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField()

    class Meta:
        unique_together = [('first_name', 'last_name')]

    def __str__(self) -> str:
        return f'{self.first_name} {self.last_name}'

    @property
    def name(self) -> str:
        return f'{self.first_name} {self.last_name}'

    def ical_link(self):
        return reverse('management:admin_calendar', kwargs={'pk': self.pk})

    @property
    def h_semester_count(self):
        return self.h_semesters.count()

    @property
    def ss_since_last_h_semester(self):
        if self.h_semesters.count() == 0:
            return 0
        last_h_semester_date = self.h_semesters.order_by("-date").first().date
        # use maxtime here as the sprechstunde on the same day as the honorary semester
        # is awarded counts to this very honorary semester
        last_h_semester_datetime = datetime.combine(
            last_h_semester_date, datetime.max.time(), tzinfo=tz.gettz(settings.TIME_ZONE))
        return self.appointments.filter(start_time__gte=last_h_semester_datetime).count()


class HSemester(models.Model):
    """Models honorary semesters"""
    date = models.DateField()
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE, related_name="h_semesters")

    def __str__(self):
        return f"Honorarsemester an {self.admin} zugesprochen am {self.date}"


class Appointment(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    admins = models.ManyToManyField(Admin, blank=True, related_name='appointments')
    reminder_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ('start_time',)

    def __str__(self) -> str:
        return f'Sprechstunde {self.start_time} - {self.end_time}'

    @property
    def format_date(self) -> str:
        return formats.date_format(self.start_time, format='DATE_FORMAT', use_l10n=True)

    @property
    def month(self):
        return self.start_time.month

    @property
    def comment(self):
        holiday, comment = is_holiday(self.start_time.date())
        if holiday:
            return comment

        return is_during_lecture_time(self.start_time.date())[1]

    @classmethod
    def get_in_interval(cls, from_date: date, to_date: date):
        return cls.objects.filter(start_time__gte=from_date, start_time__lt=to_date)

    @classmethod
    def create_for_month(cls, year: int, month: int) -> List['Appointment']:
        c = calendar.Calendar()
        appointments = []

        for d in c.itermonthdates(year, month):
            day_start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=tz.gettz(settings.TIME_ZONE))
            day_end = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=tz.gettz(settings.TIME_ZONE))
            if not cls.objects.filter(start_time__gte=day_start, end_time__lte=day_end).exists() and \
                    (d.weekday() == 0 or d.weekday() == 3):
                appointments.append(Appointment(
                    start_time=datetime(d.year, d.month, d.day, 19, 0, 0, tzinfo=tz.gettz(settings.TIME_ZONE)),
                    end_time=datetime(d.year, d.month, d.day, 19, 30, 0, tzinfo=tz.gettz(settings.TIME_ZONE))
                ))

        return appointments

    @staticmethod
    def as_ical(appointments: QuerySet, title: str, with_attendants: bool = False) -> str:
        context = {
            'appointments': appointments,
            'with_attendants': with_attendants,
            'title': title,
            'location': Settings.get(Settings.SETTING_APPOINTMENT_LOCATION)
        }

        return render_to_string('management/ical.j2', context=context)


class Settings(models.Model):
    name = models.CharField(max_length=255)
    value = models.TextField(max_length=2000)
    active = models.BooleanField(default=False)

    SETTING_SENDER = 'sender'
    SETTING_MAILING_LIST = 'mailing_list'
    SETTING_REMINDER_NOTE = 'reminder_note'
    SETTING_APPOINTMENT_LOCATION = 'appointment_location'

    def __str__(self) -> str:
        return f'{self.name}: {self.value}'

    @classmethod
    def get(cls, key: str, default: Optional[str] = None):
        if cls.objects.filter(name=key, active=True).exists():
            return cls.objects.filter(name=key, active=True).first().value

        if default is not None:
            return default

        if key == cls.SETTING_SENDER:
            return settings.DEFAULT_SENDER

        if key == cls.SETTING_MAILING_LIST:
            return settings.DEFAULT_MAILING_LIST

        if key == cls.SETTING_REMINDER_NOTE:
            return settings.DEFAULT_REMINDER_NOTE

        if key == cls.SETTING_APPOINTMENT_LOCATION:
            return settings.DEFAULT_APPOINTMENT_LOCATION

        return None

    @classmethod
    def verbose_name(cls, name):
        if name == cls.SETTING_SENDER:
            return 'Absender'

        if name == cls.SETTING_MAILING_LIST:
            return 'Mailingliste'

        if name == cls.SETTING_REMINDER_NOTE:
            return 'Hinweis zur Sprechstunde'

        if name == cls.SETTING_APPOINTMENT_LOCATION:
            return 'Ort'

        return name
