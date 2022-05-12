import itertools
from datetime import date, datetime

from dateutil.relativedelta import relativedelta
from dateutil.tz import tz
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone

from management.forms import AdminForm, AddAppointmentsForm, EditAppointmentForm, SettingsForm
from management.models import Settings, Appointment, Admin
from management.utils import datetime_plus_months


def plan(request):
    today = timezone.now()
    year = request.GET.get('year')
    month = request.GET.get('month')

    if year and year.isnumeric() and month and month.isnumeric():
        year = int(year)
        month = int(month)
        if (not request.user.is_authenticated or not request.user.is_staff) and date(today.year, today.month, 1) > date(
                year, month, 1):
            return HttpResponseForbidden('<h1>Forbidden</h1>')

    else:
        year = today.year
        month = today.month

    from_date = datetime(year=year, month=month, day=1)
    to_date = datetime_plus_months(from_date, 1)

    previous_date = datetime_plus_months(from_date, -2)
    next_date = datetime_plus_months(from_date, 2)

    context = {
        'from_date': from_date,
        'to_date': to_date,
        'link_previous': reverse(
            'management:index') + f'?year={previous_date.year}&month={previous_date.month}',
        'link_next': reverse(
            'management:index') + f'?year={next_date.year}&month={next_date.month}',
        'today': today,
        'plan': [
            {
                'date': from_date,
                'appointments': Appointment.get_in_interval(from_date, datetime_plus_months(from_date, 1))
            },
            {
                'date': datetime_plus_months(from_date, 1),
                'appointments': Appointment.get_in_interval(datetime_plus_months(from_date, 1),
                                                            datetime_plus_months(from_date, 2))
            }
        ]
    }

    return render(request, 'management/plan.html', context)


def calendar(request):
    context = {
        'admins': Admin.objects.all()
    }
    return render(request, 'management/calendar.html', context)


def full_calendar(request):
    appointments = Appointment.objects.all()
    cal = Appointment.as_ical(appointments, title='Sprechstundenplan')
    return HttpResponse(content=cal, content_type='text/plain')


@staff_member_required(login_url=settings.LOGIN_URL)
def create_appointments(request):
    months = request.GET.get('months')
    if not months or not months.isnumeric():
        months = 3
    else:
        months = max(1, int(months))

    if request.POST:
        form = AddAppointmentsForm(data=request.POST)
        if form.is_valid():
            form.save()

    today = date.today()

    def for_month(i):
        return datetime_plus_months(today, i)

    context = {
        'appointments': itertools.chain(*[Appointment.create_for_month(
            year=for_month(i).year,
            month=for_month(i).month,
        ) for i in range(months)])
    }

    return render(request, 'management/create_appointments.html', context)


@staff_member_required(login_url=settings.LOGIN_URL)
def admin_calendar(request, pk):
    admin = get_object_or_404(Admin, pk=pk)
    cal = Appointment.as_ical(admin.appointments.all(), title=f'Sprechstunden von {admin.name}', with_attendants=True)
    return HttpResponse(content=cal, content_type='text/plain; charset=utf-8')


@staff_member_required(login_url=settings.LOGIN_URL)
def manage_admins(request):
    context = {
        'admins': Admin.objects.all()
    }
    return render(request, 'management/manage_admins.html', context)


@staff_member_required(login_url=settings.LOGIN_URL)
def create_admin(request):
    context = {
        'form': AdminForm()
    }

    if request.POST:
        form = AdminForm(data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Admin angelegt!')
            return redirect('management:manage_admins')

        context['form'] = form

    return render(request, 'management/edit_admin.html', context)


@staff_member_required(login_url=settings.LOGIN_URL)
def edit_admin(request, pk):
    admin = get_object_or_404(Admin, pk=pk)
    context = {
        'admin': admin,
        'form': AdminForm(instance=admin)
    }

    if request.POST:
        form = AdminForm(data=request.POST, instance=admin)
        if form.is_valid():
            form.save()
            messages.success(request, 'Änderungen gespeichert!')
            return redirect('management:manage_admins')

        context['form'] = form

    return render(request, 'management/edit_admin.html', context)


@staff_member_required(login_url=settings.LOGIN_URL)
def edit_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    context = {
        'appointment': appointment,
        'form': EditAppointmentForm(instance=appointment)
    }

    if request.POST:
        form = EditAppointmentForm(data=request.POST, instance=appointment)
        if form.is_valid():
            form.save()
            return redirect('management:index')

        context['form'] = form

    return render(request, 'management/edit_appointment.html', context)


@staff_member_required(login_url=settings.LOGIN_URL)
def delete_appointment(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk)
    admins = appointment.admins
    if admins.count() == 0:
        appointment.delete()
        messages.success(request, f"{appointment} wurde gelöscht")
    else:
        messages.error(request, f"{appointment} wurde nicht gelöscht, da schon Admins angemeldet waren")
    return redirect('management:index')


@staff_member_required(login_url=settings.LOGIN_URL)
def statistics(request):
    today = date.today()
    from_date = request.GET.get('from_date')
    if from_date:
        try:
            from_date = date.fromisoformat(from_date)
        except ValueError:
            from_date = None

    if not from_date:
        from_date = today - relativedelta(months=3)
    to_date = request.GET.get('to_date')
    if to_date:
        try:
            to_date = date.fromisoformat(to_date)
        except ValueError:
            to_date = None

    if not to_date:
        to_date = today + relativedelta(months=3)

    from_datetime = datetime.combine(from_date, datetime.min.time(), tzinfo=tz.gettz(settings.TIME_ZONE))
    to_datetime = datetime.combine(to_date, datetime.min.time(), tzinfo=tz.gettz(settings.TIME_ZONE))

    count_query = Count(
        'appointments',
        filter=Q(appointments__start_time__gte=from_datetime, appointments__end_time__lte=to_datetime)
    )

    admins = Admin.objects.annotate(num_appointments=count_query).filter(num_appointments__gte=1).order_by(
        '-num_appointments')

    context = {
        'from_date': from_date,
        'to_date': to_date,
        'admins': admins
    }
    return render(request, 'management/statistics.html', context)


@staff_member_required(login_url=settings.LOGIN_URL)
def app_settings(request):
    context = {
        'settings': [{
            'fields': Settings.objects.filter(name=name),
            'name': name,
            'verbose_name': Settings.verbose_name(name)
        } for name in Settings.objects.all().values_list('name', flat=True).distinct()],
        'forms': [{
            'name': name,
            'verbose_name': Settings.verbose_name(name),
            'form': SettingsForm(setting_name=name)
        } for name in Settings.objects.all().values_list('name', flat=True).distinct()],
    }

    if request.POST:
        form = SettingsForm(data=request.POST)
        if form.is_valid():
            form.save()

    return render(request, 'management/settings.html', context)


@staff_member_required(login_url=settings.LOGIN_URL)
def api_list_admins(request):
    admins = Admin.objects.all()

    json_payload = [
        {
            'id': admin.pk,
            'name': admin.name,
            'email': admin.email
        } for admin in admins
    ]

    return JsonResponse(json_payload, safe=False)


def api_list_appointments(request):
    elements = request.GET.get('elements')
    if not elements or not elements.isnumeric():
        elements = 2
    else:
        elements = int(elements)
    now = timezone.now()
    appointments = Appointment.objects.filter(start_time__gte=now)[:elements]

    json_payload = [
        {
            'start': appointment.start_time.timestamp(),
            'end': appointment.end_time.timestamp(),
            'count': appointment.admins.all().count()
        } for appointment in appointments
    ]

    return JsonResponse(json_payload, safe=False)
