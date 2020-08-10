#!/usr/bin/env python3

"""Requires fully set up mgdbv3 and access to old database"""

import os
import sys
from datetime import timedelta

import psycopg2
import psycopg2.extras
from django.contrib.auth.models import User

# setup django
sys.path.append('../')
os.environ['DJANGO_SETTINGS_MODULE'] = 'sprechstundensystem.settings'
import django  # noqa E402, need settings module before setting up django

django.setup()

from management.models import (  # noqa E402
    Admin,
    Appointment,
    Settings
)

# CHANGE SETTINGS HERE
old_server = "dbname='sss' user='sss' host='localhost' password='???'"
DEBUG = True


def load_admins(c):
    c.execute("""select * from persons""")
    admins = c.fetchall()

    adms = []
    for admin in admins:
        adms.append(Admin(
            pk=admin['id'],
            first_name=admin['first_name'],
            last_name=admin['last_name'],
            email=admin['email'],
        ))

    if not DEBUG:
        Admin.objects.bulk_create(adms)


def load_appointments(c):
    c.execute("""select * from appointments""")

    appointments = c.fetchall()
    apps = []
    for appointment in appointments:
        start_time = appointment['time']
        end_time = start_time + timedelta(minutes=appointment['duration'])
        apps.append(Appointment(
            pk=appointment['id'],
            start_time=start_time,
            end_time=end_time,
            reminder_sent=appointment['reminder_sent']
        ))

    if not DEBUG:
        Appointment.objects.bulk_create(apps)


def load_settings(c):
    Settings.objects.create(
        name=Settings.SETTING_SENDER,
        value='Leo',
        active=True
    )
    Settings.objects.create(
        name=Settings.SETTING_MAILING_LIST,
        value='admins@stusta.net',
        active=True
    )
    Settings.objects.create(
        name=Settings.SETTING_APPOINTMENT_LOCATION,
        value='Haus 10, Raum 0002',
        active=True
    )
    Settings.objects.create(
        name=Settings.SETTING_REMINDER_NOTE,
        value='',
        active=True
    )


def load_users(c):
    c.execute("""select * from users""")
    users = c.fetchall()

    usrs = []
    for user in users:
        u = User(
            pk=user['id'],
            username=user['username'],
            email=user['email'],
            is_staff=True,
            password=user['password']
        )
        usrs.append(u)

    if not DEBUG:
        User.objects.bulk_create(usrs)


def load_many_to_many(c):
    c.execute("""select * from users""")
    m2m = c.fetchall()

    for entry in m2m:
        appointment = Appointment.objects.get(pk=entry['appointment'])
        admin = Admin.objects.get(pk=entry['person'])
        if not DEBUG:
            appointment.admins.add(admin)


def main():
    con = psycopg2.connect(old_server)
    cur = con.cursor(cursor_factory=psycopg2.extras.DictCursor)
    load_admins(cur)
    load_appointments(cur)
    # load_users(cur)
    load_settings(cur)
    load_many_to_many(cur)


if __name__ == '__main__':
    main()
