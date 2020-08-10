from django.contrib.auth import views as auth_views
from django.urls import path

from management import views

app_name = 'management'

urlpatterns = [
    path('', views.plan, name='index'),
    path('settings', views.app_settings, name='settings'),
    path('statistics', views.statistics, name='statistics'),

    # admins
    path('admins', views.manage_admins, name='manage_admins'),
    path('admins/<int:pk>/edit', views.edit_admin, name='edit_admin'),
    path('admins/<int:pk>/appointments.ical', views.admin_calendar, name='admin_calendar'),
    path('admins/create', views.create_admin, name='create_admin'),

    # appointments
    path('appointments/create', views.create_appointments, name='create_appointments'),
    path('appointments/<int:pk>/edit', views.edit_appointment, name='edit_appointment'),

    # ical calendar stuff
    path('calendar', views.calendar, name='calendar'),
    path('calendar/all.ical', views.full_calendar, name='full_calendar'),
    path('calendar/<int:pk>.ical', views.admin_calendar, name='admin_calendar_old'),

    # api stuff
    path('persons.json', views.api_list_admins, name='api_list_admins'),
    path('appointments.json', views.api_list_appointments, name='api_list_appointments'),

    # authentication stuff
    path('auth/login/', auth_views.LoginView.as_view(), name='login'),
    path('auth/logout/', auth_views.LogoutView.as_view(next_page='management:index'), name='logout'),
    # path('auth/', include('django.contrib.auth.urls')),
]
