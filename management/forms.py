from datetime import datetime, timedelta
import datetime
from typing import Optional

from dateutil import tz
from django import forms
from django.conf import settings

from management.models import Admin, Appointment, HSemester, Settings


class SettingsForm(forms.Form):
    name = forms.CharField(widget=forms.HiddenInput())

    ACTION_ADD = 'add'
    ACTION_SAVE = 'save'
    ACTION_DELETE = 'delete'

    def __init__(self, *args, setting_name: Optional[str] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.setting_name = setting_name
        if self.setting_name:
            self.fields['name'].initial = self.setting_name
            self.update_settings()
        else:
            self.settings = None

    def update_settings(self):
        self.settings = Settings.objects.filter(name=self.setting_name)

    def clean_name(self):
        self.setting_name = self.cleaned_data['name']
        self.update_settings()

    def clean(self):
        action = self.data.get('submit')
        to_delete = self.data.get('delete')
        if (action is None or action not in [self.ACTION_ADD, self.ACTION_SAVE]) and (not to_delete):
            raise forms.ValidationError('invalid submit')
        action = action or self.ACTION_DELETE
        self.cleaned_data['action'] = action

        if action == self.ACTION_SAVE:
            if not self.data.get('active') or not self.data['active'].isnumeric() or not self.settings.filter(
                    pk=int(self.data['active'])).exists():
                raise forms.ValidationError('invalid active setting')

            self.cleaned_data['active'] = int(self.data['active'])

            for setting in self.settings:
                if not str(setting.pk) in self.data:
                    raise forms.ValidationError(f'missing setting with id {setting.pk}')

                setting.value = self.data[str(setting.pk)]
                setting.active = setting.pk == self.cleaned_data['active']

            self.cleaned_data['settings'] = self.settings

        if action == self.ACTION_DELETE:
            if not to_delete.isnumeric() or not self.settings.filter(pk=int(to_delete)).exists():
                raise forms.ValidationError('invalid setting to delete')

            self.cleaned_data['delete'] = self.settings.filter(pk=int(to_delete)).first()

        return self.cleaned_data

    def save(self):
        if self.cleaned_data['action'] == self.ACTION_ADD:
            Settings.objects.create(name=self.setting_name, value='')
            self.update_settings()
            return self.settings

        if self.cleaned_data['action'] == self.ACTION_SAVE:
            for setting in self.settings:
                setting.save()
            return self.settings

        if self.cleaned_data['action'] == self.ACTION_DELETE:
            self.cleaned_data['delete'].delete()
            self.update_settings()
            return self.settings

        return self.settings


class AddAppointmentsForm(forms.Form):
    def clean(self):
        cleaned_data = self.cleaned_data
        if not self.data.getlist('appointments'):
            raise forms.ValidationError('Bitte Sprechstunden auswählen')

        cleaned_data['appointments'] = []

        for appointment_time in self.data.getlist('appointments'):
            try:
                start_time = datetime.fromisoformat(appointment_time)
                start_time.replace(tzinfo=tz.gettz(settings.TIME_ZONE))
            except ValueError as e:
                raise forms.ValidationError(str(e))

            cleaned_data['appointments'].append(
                Appointment(start_time=start_time, end_time=start_time + timedelta(minutes=30))
            )

        self.cleaned_data = cleaned_data

        return self.cleaned_data

    def save(self):
        Appointment.objects.bulk_create(self.cleaned_data['appointments'])


class EditAppointmentForm(forms.ModelForm):
    start_date = forms.DateField()
    start_time = forms.TimeField()
    end_time = forms.TimeField()

    class Meta:
        model = Appointment
        fields = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.start_datetime = self.instance.start_time
            self.end_datetime = self.instance.end_time
            self.fields['start_date'].initial = self.instance.start_time.date()
            self.fields['start_time'].initial = self.instance.start_time.time()
            self.fields['end_time'].initial = self.instance.end_time.time()

    def clean_admins(self):
        admins = []
        for admin_pk in self.data.getlist('admins', []):
            if admin_pk == '':
                continue
            if not admin_pk.isnumeric():
                raise forms.ValidationError('admin id must be an integer')
            admin_pk = int(admin_pk)

            admin = Admin.objects.filter(pk=admin_pk)
            if not admin.exists():
                raise forms.ValidationError(f'Admin with id {admin_pk} does not exist')
            admins.append(admin.first())
        self.cleaned_data['admins'] = admins

    def clean(self):
        self.clean_admins()

        self.start_datetime = datetime.combine(
            self.cleaned_data['start_date'],
            self.cleaned_data['start_time'],
            tzinfo=tz.gettz(settings.TIME_ZONE)
        )
        self.end_datetime = datetime.combine(
            self.cleaned_data['start_date'],
            self.cleaned_data['end_time'],
            tzinfo=tz.gettz(settings.TIME_ZONE)
        )
        self.cleaned_data['start_datetime'] = self.start_datetime
        self.cleaned_data['end_datetime'] = self.end_datetime
        return self.cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.start_time = self.cleaned_data['start_datetime']
        instance.end_time = self.cleaned_data['end_datetime']
        if commit:
            instance.save()
            instance.admins.clear()
            instance.admins.add(*self.cleaned_data['admins'])

        return instance


class AdminForm(forms.ModelForm):
    class Meta:
        model = Admin
        fields = ('first_name', 'last_name', 'email')

    def clean_date(self):
        hdates = self.data.getlist('date', [])
        hsemesters = self.data.getlist('hsems', [])
        if len(hdates) != len(hsemesters):
            raise forms.ValidationError('date and hsems field must have the same length.')
        if hdates[-1] == "":
            # remove last "" entry
            hdates = hdates[:-1]
            hsemesters = hsemesters[:-1]
        
        
        to_remove = {i.pk for i in self.instance.h_semesters.all()}
        to_save = []
        for hdate_str, hsem_pk_str in zip(hdates, hsemesters):
            try:
                # check that date has correct format
                hdate = datetime.date.fromisoformat(hdate_str)
            except ValueError:
                raise forms.ValidationError('Wrong date format.')
            # check that pk actually matches the admin
            if hsem_pk_str != "":
                hsem_pk = int(hsem_pk_str)
                if hsem_pk not in [i.pk for i in self.instance.h_semesters.all()]:
                    raise forms.ValidationError('Honorary semester does not belong to admin.')

                hs = HSemester.objects.filter(pk=hsem_pk).first()
                hs.date = hdate
                to_save.append(hs)
                to_remove -= {hs.pk}
            else:
                to_save.append(HSemester(date=hdate, admin=self.instance))
        self.cleaned_data["dates_to_save"] = to_save
        self.cleaned_data["dates_to_remove"] = to_remove


    def clean(self):
        self.clean_date()
        return self.cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            for i in self.cleaned_data["dates_to_save"]:
                i.save()
            for hsem_pk in self.cleaned_data["dates_to_remove"]:
                HSemester.objects.filter(pk=hsem_pk).delete()
            instance.save()

        return instance
